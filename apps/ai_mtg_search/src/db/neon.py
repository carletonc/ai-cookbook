"""
Read-only access to the Neon Postgres + pgvector card database.

The `cards` and `embeddings` tables are written weekly by the external
`mtg-db` ETL repo. This app never mutates them, so every statement runs
inside a read-only transaction — that holds even while the connection
string still carries the ETL role's credentials.

Connections are opened lazily. Neon scales to zero, so an idle pool
accumulates dead sockets and the first query after a cold start is slow;
`query` transparently rebuilds the pool and retries once.
"""

import threading
from contextlib import contextmanager

import psycopg2
from psycopg2 import extras, pool as pg_pool

from src.config import get_database_url

_MIN_CONNECTIONS = 1
_MAX_CONNECTIONS = 4
_CONNECT_TIMEOUT_SECONDS = 15

_pool: pg_pool.SimpleConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> pg_pool.SimpleConnectionPool:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = pg_pool.SimpleConnectionPool(
                _MIN_CONNECTIONS,
                _MAX_CONNECTIONS,
                dsn=get_database_url(),
                connect_timeout=_CONNECT_TIMEOUT_SECONDS,
            )
    return _pool


def _discard_pool() -> None:
    """Drop the pool so the next call reconnects. Used after a dropped socket."""
    global _pool
    with _pool_lock:
        if _pool is not None:
            try:
                _pool.closeall()
            except Exception:
                pass
            _pool = None


# SET LOCAL cannot take a parameterized target, so the knobs a caller may
# touch are whitelisted rather than interpolated.
_ALLOWED_SETTINGS = frozenset(
    {
        "ivfflat.probes",
        "ivfflat.iterative_scan",
        "ivfflat.max_probes",
        "enable_indexscan",
        "enable_bitmapscan",
    }
)


@contextmanager
def _read_only_cursor(settings: dict | None):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        conn.rollback()
        conn.set_session(readonly=True, autocommit=False)
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            for name, value in (settings or {}).items():
                if name not in _ALLOWED_SETTINGS:
                    raise ValueError(f"Setting {name!r} is not allowed.")
                cur.execute(f"SET LOCAL {name} = %s", (value,))
            yield cur
        conn.rollback()
    finally:
        pool.putconn(conn)


# Forcing an exact scan costs ~100-150ms server-side on 36k vectors, against
# ~3-6ms for the approximate index. That trade is worth it: the shared IVFFlat
# index is global across all three embedding sources, so a source-filtered
# search at the default probes=1 measured as low as 0% recall@5. Worse, the
# planner only chooses the index below roughly LIMIT 10, so retrieval quality
# would silently depend on k. Reproduce with eda.ipynb.
_EXACT_SCAN_SETTINGS = {"enable_indexscan": "off", "enable_bitmapscan": "off"}


def query(
    sql: str,
    params: dict | tuple | None = None,
    *,
    exact: bool = False,
    probes: int | None = None,
    settings: dict | None = None,
) -> list[dict]:
    """
    Run a SELECT and return rows as dicts.

    `exact` disables index scans so vector ordering is brute-force and exactly
    correct. Use it for any `ORDER BY embedding <=> ...` query.

    `probes` raises ivfflat.probes for this transaction only, for measuring the
    approximate index rather than using it in anger.

    `settings` applies additional whitelisted SET LOCAL knobs.
    """
    merged = dict(_EXACT_SCAN_SETTINGS) if exact else {}
    merged.update(settings or {})
    if probes is not None:
        merged["ivfflat.probes"] = probes

    for attempt in (0, 1):
        try:
            with _read_only_cursor(merged) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            _discard_pool()
            if attempt:
                raise
    return []


def healthcheck() -> dict:
    """Confirm connectivity, pgvector availability, and table freshness."""
    rows = query(
        """
        SELECT
            (SELECT count(*) FROM cards)                          AS cards,
            (SELECT count(*) FROM embeddings)                     AS embeddings,
            (SELECT max(updated_at) FROM embeddings)              AS embeddings_updated_at,
            (SELECT extversion FROM pg_extension
              WHERE extname = 'vector')                           AS pgvector_version,
            pg_size_pretty(pg_database_size(current_database()))   AS db_size
        """
    )
    return rows[0] if rows else {}
