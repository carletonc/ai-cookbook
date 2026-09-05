"""
Load the MTG taxonomy from `data/taxonomy.json`.

That file is the single source of truth: slang aliases and oracle_hints
for query expansion, plus keywords / regexes / example cards for labeling.
This module is the matching API. Nothing here is on the live search path yet.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "taxonomy.json"


def _load_doc() -> dict:
    return json.loads(_DATA_PATH.read_text(encoding="utf-8"))


_DOC = _load_doc()
TAXONOMY: list[dict] = _DOC["taxonomy"]
COLOR_GROUPS: dict[str, list[str]] = _DOC["color_groups"]
ABBREVIATIONS: dict[str, str] = _DOC["abbreviations"]


def _walk(nodes: list[dict]):
    for node in nodes:
        yield node
        yield from _walk(node.get("children") or [])


def get_node(key: str) -> dict | None:
    """Look up a taxonomy node by its dotted key."""
    for node in _walk(TAXONOMY):
        if node["key"] == key:
            return node
    return None


def get_all_aliases() -> dict[str, str]:
    """Alias (lowercased) → node key, e.g. {"board wipe": "interaction.mass_removal"}."""
    result = {}
    for node in _walk(TAXONOMY):
        for alias in node.get("aliases") or []:
            result[alias.lower()] = node["key"]
    return result


def get_oracle_hints(key: str) -> list[str]:
    """Oracle-text hints for a node and all descendants."""
    node = get_node(key)
    if not node:
        return []
    hints = list(node.get("oracle_hints") or [])
    for child in _walk(node.get("children") or []):
        hints.extend(child.get("oracle_hints") or [])
    return hints


def get_descriptions(key: str) -> list[str]:
    """Descriptions for a node and all descendants."""
    node = get_node(key)
    if not node:
        return []
    descs = [node["description"]]
    for child in _walk(node.get("children") or []):
        descs.append(child["description"])
    return descs


# Real slang that is also ordinary English — matching floods expansion.
_SKIP_ALIASES = frozenset(
    {
        "search",
        "response",
        "cancel",
        "lock",
        "grow",
        "boost",
        "kill",
    }
)

# One- and two-letter aliases that are safe as whole tokens.
_SHORT_ALIASES = frozenset({"ca", "etb", "ltb", "cmc", "mv", "gy"})


def match_nodes(query: str) -> list[dict]:
    """
    Nodes whose aliases appear in `query`, longest phrase first.

    Overlapping spans keep the longer alias so "spot removal" wins over
    "removal". Bare "control" is not an alias; use "control deck" / "draw-go".
    """
    text = query.lower()
    used: list[tuple[int, int]] = []
    keys: list[str] = []
    aliases = sorted(get_all_aliases().items(), key=lambda item: -len(item[0]))
    for alias, key in aliases:
        if alias in _SKIP_ALIASES:
            continue
        if len(alias) < 3 and alias not in _SHORT_ALIASES:
            continue
        pattern = r"(?<![a-z0-9+])" + re.escape(alias) + r"(?![a-z0-9+])"
        for match in re.finditer(pattern, text):
            start, end = match.span()
            if any(start < used_end and end > used_start for used_start, used_end in used):
                continue
            used.append((start, end))
            if key not in keys:
                keys.append(key)
    return [node for key in keys if (node := get_node(key))]


def expand_search_texts(query: str, *, max_hints: int = 6) -> list[str]:
    """
    Original query plus oracle-text hints from matching taxonomy nodes.

    Always returns at least `[query]`. Hints include descendant nodes so
    "ramp" expands to land tutors, rocks, dorks, etc.
    """
    texts = [query]
    seen = {query.lower()}
    for node in match_nodes(query):
        for hint in get_oracle_hints(node["key"]):
            cleaned = hint.strip()
            if not cleaned or cleaned.lower() in seen:
                continue
            seen.add(cleaned.lower())
            texts.append(cleaned)
            if len(texts) >= max_hints + 1:
                return texts
    return texts


def match_color_identity(query: str) -> list[str] | None:
    """Guild/shard/wedge name → color_identity list, or None."""
    text = query.lower()
    hits: list[tuple[int, list[str]]] = []
    for name, colors in COLOR_GROUPS.items():
        pattern = r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            hits.append((len(name), colors))
    if not hits:
        return None
    hits.sort(key=lambda item: -item[0])
    return list(hits[0][1])
