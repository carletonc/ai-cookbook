import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src.config import LLM_MODEL
from src.db.cards import lookup_card_by_oracle_id
from src.search import (
    FUZZY_AUTO_ACCEPT,
    card_abilities,
    dedupe_cards,
    find_seed_matches,
    format_candidates,
    search_card_text,
)

SCRIPT_DIR = Path(__file__).parent.resolve()
PROMPTS_DIR = SCRIPT_DIR / "prompts"
PLANNER_PATH = PROMPTS_DIR / "planner.md"
RANKER_PATH = PROMPTS_DIR / "ranker.md"

TEMPERATURE = 0.1

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


@dataclass
class PipelineResult:
    """Outcome of one pipeline step. `need_pick` pauses for the Streamlit picker."""

    status: Literal["done", "need_pick", "unresolved", "unsupported"]
    text: str | None = None
    choices: list[dict] | None = None
    name: str | None = None
    # How the choices were found — selects picker copy ("contains" vs "fuzzy").
    pick_kind: Literal["contains", "fuzzy"] | None = None


def load_prompt(filepath: Path) -> str:
    """Load a Markdown prompt template as plain text."""
    return Path(filepath).read_text(encoding="utf-8")


async def _run_prompt(template_path: Path, **variables) -> str:
    llm = ChatOpenAI(model=LLM_MODEL, temperature=TEMPERATURE)
    prompt = PromptTemplate(
        input_variables=list(variables),
        template=load_prompt(template_path),
    )
    output = await (prompt | llm).ainvoke(variables)
    return output.content


async def query_planner(user_input: str) -> dict:
    """Classify the query into seed_card, text_search, or unsupported."""
    return json.loads(await _run_prompt(PLANNER_PATH, query=user_input))


async def rank_and_explainer(user_input: str, context: str) -> str:
    return await _run_prompt(RANKER_PATH, query=user_input, context=context)


def _candidates_for_seed(seed: dict) -> list[dict]:
    """Search once per ability and exclude the seed from its own alternatives."""
    candidates: list[dict] = []
    for ability in card_abilities(seed):
        candidates.extend(search_card_text(ability, k=ABILITY_CANDIDATES))

    return [
        card
        for card in dedupe_cards(candidates)
        if card["scryfall_oracle_id"] != seed["scryfall_oracle_id"]
    ][:MAX_CANDIDATES]


async def _rank_seed_path(input_query: str, seed: dict) -> PipelineResult:
    candidates = _candidates_for_seed(seed)
    if not candidates:
        return PipelineResult(
            status="done",
            text=(
                f"Nothing in the card pool matched alternatives to `{seed['name']}`.\n\n"
                "Try describing the effect in different words."
            ),
        )

    ranker_query = (
        input_query + "\n\nTarget Card Context:\n" + format_candidates([seed])
    )
    text = await rank_and_explainer(
        user_input=ranker_query,
        context=format_candidates(candidates),
    )
    return PipelineResult(status="done", text=text)


async def pipeline(
    input_query: str,
    *,
    seed_oracle_id: str | None = None,
) -> PipelineResult:
    """
    Route the query, retrieve candidates, then rank and explain them.

    When `seed_oracle_id` is set, skip the planner and name resolution — the
    user already picked a card from the disambiguation list.
    """
    if seed_oracle_id:
        seed = lookup_card_by_oracle_id(seed_oracle_id)
        if seed is None:
            return PipelineResult(
                status="unresolved",
                text=UNRESOLVED_MESSAGE.format(name=seed_oracle_id),
                name=seed_oracle_id,
            )
        return await _rank_seed_path(input_query, seed)

    plan = await query_planner(input_query)
    query_type = plan.get("query_type")

    if query_type == "seed_card":
        card_name = plan.get("card_name") or ""
        match = find_seed_matches(card_name)
        if not match.cards:
            return PipelineResult(
                status="unresolved",
                text=UNRESOLVED_MESSAGE.format(name=card_name),
                name=card_name,
            )

        # Exact / contains: one hit continues; many open the family picker.
        # Fuzzy: many (or one weak hit) open the "did you mean" picker; only a
        # high-confidence unique typo auto-continues (Lightnin Bolt → Lightning Bolt).
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
                )
            return await _rank_seed_path(input_query, match.cards[0])

        if len(match.cards) > 1:
            return PipelineResult(
                status="need_pick",
                choices=match.cards,
                name=card_name,
                pick_kind="contains",
            )
        return await _rank_seed_path(input_query, match.cards[0])

    if query_type == "text_search":
        candidates = search_card_text(
            plan.get("search_text") or input_query,
            k=TEXT_CANDIDATES,
        )
        if not candidates:
            return PipelineResult(
                status="done",
                text=(
                    f"Nothing in the card pool matched `{input_query}`.\n\n"
                    "Try describing the effect in different words, or loosening any filters."
                ),
            )
        text = await rank_and_explainer(
            user_input=input_query,
            context=format_candidates(candidates),
        )
        return PipelineResult(status="done", text=text)

    return PipelineResult(
        status="unsupported",
        text=UNSUPPORTED_MESSAGE.format(query=input_query),
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
