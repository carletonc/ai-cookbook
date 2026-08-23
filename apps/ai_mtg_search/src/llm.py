import asyncio
import json
from pathlib import Path

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from src.config import LLM_MODEL
from src.search import (
    card_abilities,
    dedupe_cards,
    format_candidates,
    resolve_card,
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
    "No card matching `{name}` was found, so there's no seed card to compare against.\n\n"
    "Check the spelling, or describe the effect you're looking for instead."
)


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


def _seed_card_candidates(card_name: str) -> tuple[dict | None, list[dict]]:
    """
    Resolve a seed card, then search once per ability.

    Splitting by ability is the fix for one-card-many-functions: a card that is
    simultaneously ramp, lifegain and card draw averages into a single vector,
    so each ability is searched on its own and the results unioned.
    """
    seed = resolve_card(card_name)
    if seed is None:
        return None, []

    candidates: list[dict] = []
    for ability in card_abilities(seed):
        candidates.extend(search_card_text(ability, k=ABILITY_CANDIDATES))

    # The seed card itself is not an alternative to itself.
    candidates = [
        card
        for card in dedupe_cards(candidates)
        if card["scryfall_oracle_id"] != seed["scryfall_oracle_id"]
    ]
    return seed, candidates[:MAX_CANDIDATES]


async def pipeline(input_query: str) -> str:
    """Route the query, retrieve candidates, then rank and explain them."""
    plan = await query_planner(input_query)
    query_type = plan.get("query_type")

    seed = None
    if query_type == "seed_card":
        seed, candidates = _seed_card_candidates(plan.get("card_name"))
        if seed is None:
            return UNRESOLVED_MESSAGE.format(name=plan.get("card_name"))

    elif query_type == "text_search":
        candidates = search_card_text(plan.get("search_text") or input_query, k=TEXT_CANDIDATES)

    else:
        return UNSUPPORTED_MESSAGE.format(query=input_query)

    if not candidates:
        return (
            f"Nothing in the card pool matched `{input_query}`.\n\n"
            "Try describing the effect in different words, or loosening any filters."
        )

    ranker_query = input_query
    if seed is not None:
        ranker_query += "\n\nTarget Card Context:\n" + format_candidates([seed])

    return await rank_and_explainer(
        user_input=ranker_query,
        context=format_candidates(candidates),
    )


if __name__ == "__main__":
    queries = [
        "Control opponents turns",
        "Return cards to hand",
        "Cards similar to Chatterfang",
    ]

    async def main():
        results = await asyncio.gather(*(pipeline(q) for q in queries))
        for query, output in zip(queries, results):
            print(f"Input Query: {query}\nOutput:\n{output}\n---\n")

    asyncio.run(main())
