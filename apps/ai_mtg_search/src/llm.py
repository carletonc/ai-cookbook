import asyncio
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from langchain.prompts import PromptTemplate

from src.db.cards import (
    drop_equivalent_to_seed,
    legal_cards_first,
    lookup_card_by_oracle_id,
)
from src.llm_client import (
    PLANNER_MAX_TOKENS,
    RANKER_MAX_TOKENS,
    QuotaExceeded,
    consume_llm_request,
    get_chat_llm,
    is_quota_error,
)
from src.search import (
    FUZZY_AUTO_ACCEPT,
    card_abilities,
    find_seed_matches,
    format_candidates,
    merge_search_hits,
    record_search_event,
    search_card_text,
)

SCRIPT_DIR = Path(__file__).parent.resolve()
PROMPTS_DIR = SCRIPT_DIR / "prompts"
PLANNER_PATH = PROMPTS_DIR / "planner.md"
RANKER_PATH = PROMPTS_DIR / "ranker.md"

# The seed-card path runs one search per ability, so a per-ability limit as
# large as the text path's would blow up the ranker's context on a card with
# four abilities. Cap the union instead.
TEXT_CANDIDATES = 50
ABILITY_CANDIDATES = 20
MAX_CANDIDATES = 60

UNSUPPORTED_MESSAGE = (
    "`{query}` is outside what this tool covers, so any answer would be guesswork.\n\n"
    "Try describing a card's effect (\"draw when opponents cast spells\") or naming "
    "a card to find alternatives to (\"cards like Rhystic Study\")."
)

UNRESOLVED_MESSAGE = (
    "We didn't find a card matching `{name}`.\n\n"
    "Check the spelling, or describe the effect you're looking for instead."
)

GENERIC_API_ERROR = (
    "Something went wrong talking to the model. Please try again in a moment."
)

QUOTA_MESSAGE = (
    "Demo LLM quota is exhausted for now — try again later.\n\n"
    "You can still try a known card name once the quota resets; "
    "retrieval does not need the model for exact matches after a pick."
)

EMPTY_RANKER_MESSAGE = (
    "The ranker finished without a write-up. Try the same query again — "
    "the current model sometimes spends its token budget on hidden reasoning."
)


def _ranker_text_or_fallback(text: str | None) -> str:
    cleaned = (text or "").strip()
    return cleaned or EMPTY_RANKER_MESSAGE


@dataclass
class PipelineResult:
    """Outcome of one pipeline step. `need_pick` pauses for the Streamlit picker."""

    status: Literal[
        "done", "need_pick", "unresolved", "unsupported", "error", "quota"
    ]
    text: str | None = None
    choices: list[dict] | None = None
    name: str | None = None
    # How the choices were found — selects picker copy ("contains" vs "fuzzy").
    pick_kind: Literal["contains", "fuzzy"] | None = None
    timings_ms: dict[str, int] = field(default_factory=dict)
    # Resolved seed card when this was a "cards like X" search.
    seed: dict | None = None


def load_prompt(filepath: Path) -> str:
    """Load a Markdown prompt template as plain text."""
    return Path(filepath).read_text(encoding="utf-8")


def _message_text(output: Any) -> str:
    """Prefer chat `content`; fall back to reasoning if the host left content empty."""
    content = getattr(output, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
        joined = "".join(parts).strip()
        if joined:
            return joined
    additional = getattr(output, "additional_kwargs", None) or {}
    reasoning = additional.get("reasoning_content") or additional.get("reasoning")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning
    return (content or "") if isinstance(content, str) else ""


def _extract_json_object(text: str) -> dict:
    """Parse a JSON object from model output, tolerating fences or prose wrappers."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Planner JSON was not an object")
    return data


async def _run_prompt(
    template_path: Path,
    *,
    max_tokens: int,
    model_kwargs: dict | None = None,
    on_token: Callable[[str], None] | None = None,
    **variables,
) -> str:
    consume_llm_request()
    llm = get_chat_llm(max_tokens=max_tokens, model_kwargs=model_kwargs or {})
    prompt = PromptTemplate(
        input_variables=list(variables),
        template=load_prompt(template_path),
    )
    chain = prompt | llm
    if on_token is None:
        output = await chain.ainvoke(variables)
        return _message_text(output)

    parts: list[str] = []
    async for chunk in chain.astream(variables):
        piece = _message_text(chunk)
        if not piece:
            # Streaming chunks often only populate .content incrementally.
            raw = getattr(chunk, "content", "") or ""
            if isinstance(raw, list):
                piece = "".join(
                    b if isinstance(b, str) else str(b.get("text", ""))
                    for b in raw
                )
            else:
                piece = raw
        if piece:
            parts.append(piece)
            on_token(piece)
    return "".join(parts)


async def query_planner(user_input: str) -> dict:
    """Classify the query into seed_card, text_search, or unsupported."""
    # JSON mode is planner-only; the ranker must stay free-form markdown.
    # Some OpenAI-compatible hosts ignore or reject response_format — fall back.
    json_mode = {"response_format": {"type": "json_object"}}

    async def _once(query: str, *, use_json_mode: bool) -> str:
        try:
            return await _run_prompt(
                PLANNER_PATH,
                max_tokens=PLANNER_MAX_TOKENS,
                model_kwargs=json_mode if use_json_mode else None,
                query=query,
            )
        except Exception as exc:
            if use_json_mode and "response_format" in str(exc).lower():
                return await _run_prompt(
                    PLANNER_PATH,
                    max_tokens=PLANNER_MAX_TOKENS,
                    model_kwargs=None,
                    query=query,
                )
            raise

    raw = await _once(user_input, use_json_mode=True)
    try:
        return _extract_json_object(raw)
    except (json.JSONDecodeError, ValueError):
        repair = await _once(
            user_input
            + "\n\n(Previous reply was not valid JSON. "
            "Respond with ONLY the schema object.)",
            use_json_mode=True,
        )
        return _extract_json_object(repair)


async def rank_and_explainer(
    user_input: str,
    context: str,
    *,
    on_token: Callable[[str], None] | None = None,
) -> str:
    return await _run_prompt(
        RANKER_PATH,
        max_tokens=RANKER_MAX_TOKENS,
        on_token=on_token,
        query=user_input,
        context=context,
    )


async def _candidates_for_seed(seed: dict) -> list[dict]:
    """Search once per ability (in parallel) and exclude the seed itself."""
    abilities = card_abilities(seed)
    if not abilities:
        return []

    batches = await asyncio.gather(
        *(
            asyncio.to_thread(search_card_text, ability, ABILITY_CANDIDATES)
            for ability in abilities
        )
    )
    candidates: list[dict] = []
    for batch in batches:
        candidates.extend(batch)

    merged = legal_cards_first(
        drop_equivalent_to_seed(seed, merge_search_hits(candidates))
    )[:MAX_CANDIDATES]
    record_search_event(
        {
            "event": "seed_union_dedupe",
            "seed": seed["name"],
            "n_ability_searches": len(abilities),
            "concat_rows": len(candidates),
            "after_dedupe_exclude_seed": len(merged),
            "names": [card["name"] for card in merged],
        }
    )
    return merged


async def _rank_seed_path(
    input_query: str,
    seed: dict,
    *,
    timings: dict[str, int],
    on_token: Callable[[str], None] | None = None,
) -> PipelineResult:
    t0 = time.perf_counter()
    candidates = await _candidates_for_seed(seed)
    timings["retrieve"] = int((time.perf_counter() - t0) * 1000)

    if not candidates:
        return PipelineResult(
            status="done",
            text=(
                f"Nothing in the card pool matched alternatives to `{seed['name']}`.\n\n"
                "Try describing the effect in different words."
            ),
            timings_ms=timings,
            seed=seed,
        )

    ranker_query = (
        input_query + "\n\nTarget Card Context:\n" + format_candidates([seed])
    )
    t1 = time.perf_counter()
    text = await rank_and_explainer(
        user_input=ranker_query,
        context=format_candidates(candidates),
        on_token=on_token,
    )
    timings["rank"] = int((time.perf_counter() - t1) * 1000)
    return PipelineResult(
        status="done",
        text=_ranker_text_or_fallback(text),
        timings_ms=timings,
        seed=seed,
    )


async def pipeline(
    input_query: str,
    *,
    seed_oracle_id: str | None = None,
    on_token: Callable[[str], None] | None = None,
) -> PipelineResult:
    """
    Route the query, retrieve candidates, then rank and explain them.

    When `seed_oracle_id` is set, skip the planner and name resolution — the
    user already picked a card from the disambiguation list.
    """
    timings: dict[str, int] = {}
    try:
        if seed_oracle_id:
            seed = lookup_card_by_oracle_id(seed_oracle_id)
            if seed is None:
                return PipelineResult(
                    status="unresolved",
                    text=UNRESOLVED_MESSAGE.format(name=seed_oracle_id),
                    name=seed_oracle_id,
                    timings_ms=timings,
                )
            return await _rank_seed_path(
                input_query, seed, timings=timings, on_token=on_token
            )

        t0 = time.perf_counter()
        plan = await query_planner(input_query)
        timings["planner"] = int((time.perf_counter() - t0) * 1000)
        query_type = plan.get("query_type")

        if query_type == "seed_card":
            card_name = plan.get("card_name") or ""
            t1 = time.perf_counter()
            match = find_seed_matches(card_name)
            timings["resolve"] = int((time.perf_counter() - t1) * 1000)
            if not match.cards:
                return PipelineResult(
                    status="unresolved",
                    text=UNRESOLVED_MESSAGE.format(name=card_name),
                    name=card_name,
                    timings_ms=timings,
                )

            # Exact / contains: one hit continues; many open the family picker.
            # Fuzzy: many (or one weak hit) open the "did you mean" picker; only a
            # high-confidence unique typo auto-continues.
            if match.source == "fuzzy":
                strong_unique = (
                    len(match.cards) == 1
                    and match.best_score is not None
                    and match.best_score >= FUZZY_AUTO_ACCEPT
                )
                if not strong_unique:
                    return PipelineResult(
                        status="need_pick",
                        choices=match.cards,
                        name=card_name,
                        pick_kind="fuzzy",
                        timings_ms=timings,
                    )
                return await _rank_seed_path(
                    input_query,
                    match.cards[0],
                    timings=timings,
                    on_token=on_token,
                )

            if len(match.cards) > 1:
                return PipelineResult(
                    status="need_pick",
                    choices=match.cards,
                    name=card_name,
                    pick_kind="contains",
                    timings_ms=timings,
                )
            return await _rank_seed_path(
                input_query,
                match.cards[0],
                timings=timings,
                on_token=on_token,
            )

        if query_type == "text_search":
            t1 = time.perf_counter()
            candidates = await asyncio.to_thread(
                search_card_text,
                plan.get("search_text") or input_query,
                TEXT_CANDIDATES,
            )
            timings["retrieve"] = int((time.perf_counter() - t1) * 1000)
            candidates = legal_cards_first(candidates)
            if not candidates:
                return PipelineResult(
                    status="done",
                    text=(
                        f"Nothing in the card pool matched `{input_query}`.\n\n"
                        "Try describing the effect in different words, or loosening any filters."
                    ),
                    timings_ms=timings,
                )
            t2 = time.perf_counter()
            text = await rank_and_explainer(
                user_input=input_query,
                context=format_candidates(candidates),
                on_token=on_token,
            )
            timings["rank"] = int((time.perf_counter() - t2) * 1000)
            return PipelineResult(
                status="done",
                text=_ranker_text_or_fallback(text),
                timings_ms=timings,
            )

        return PipelineResult(
            status="unsupported",
            text=UNSUPPORTED_MESSAGE.format(query=input_query),
            timings_ms=timings,
        )
    except QuotaExceeded:
        return PipelineResult(status="quota", text=QUOTA_MESSAGE, timings_ms=timings)
    except Exception as exc:
        if is_quota_error(exc):
            return PipelineResult(status="quota", text=QUOTA_MESSAGE, timings_ms=timings)
        return PipelineResult(
            status="error",
            text=GENERIC_API_ERROR,
            timings_ms=timings,
        )


if __name__ == "__main__":
    queries = [
        "Control opponents turns",
        "Return cards to hand",
        "Cards similar to Chatterfang",
    ]

    async def main():
        for q in queries:
            result = await pipeline(q)
            print(f"Input Query: {q}\nStatus: {result.status}\nOutput:\n{result.text}\n---\n")

    asyncio.run(main())
