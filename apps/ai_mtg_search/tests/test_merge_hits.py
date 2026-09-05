import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.cards import drop_equivalent_to_seed, legal_cards_first, merge_search_hits


class MergeSearchHitsTests(unittest.TestCase):
    def test_same_oracle_id_keeps_higher_similarity(self):
        rows = [
            {"scryfall_oracle_id": "a", "name": "Oak", "similarity": 0.4},
            {"scryfall_oracle_id": "b", "name": "Pine", "similarity": 0.9},
            {"scryfall_oracle_id": "a", "name": "Oak", "similarity": 0.8},
        ]
        merged = merge_search_hits(rows)
        self.assertEqual([c["scryfall_oracle_id"] for c in merged], ["a", "b"])
        self.assertEqual(merged[0]["similarity"], 0.8)

    def test_limit_slices_after_dedupe(self):
        rows = [
            {"scryfall_oracle_id": "a", "similarity": 0.5},
            {"scryfall_oracle_id": "b", "similarity": 0.4},
            {"scryfall_oracle_id": "a", "similarity": 0.9},
        ]
        self.assertEqual(len(merge_search_hits(rows, limit=1)), 1)
        self.assertEqual(merge_search_hits(rows, limit=1)[0]["scryfall_oracle_id"], "a")

    def test_drops_same_oracle_text_under_another_name(self):
        seed = {
            "scryfall_oracle_id": "blue",
            "name": "Rhystic Study",
            "oracle_text": "Whenever an opponent casts a spell, you may draw a card unless that player pays {1}.",
        }
        white = {
            "scryfall_oracle_id": "white",
            "name": "White Rhystic Study",
            "oracle_text": "Whenever an opponent casts a spell, you may draw a card unless that player pays {1}.",
        }
        other = {
            "scryfall_oracle_id": "other",
            "name": "Mystic Remora",
            "oracle_text": "Cumulative upkeep {1}",
        }
        kept = drop_equivalent_to_seed(seed, [seed, white, other])
        self.assertEqual([c["name"] for c in kept], ["Mystic Remora"])

    def test_illegal_cards_sort_after_legal(self):
        rows = [
            {"name": "Joke", "commander_legal": False},
            {"name": "Bolt", "commander_legal": True},
            {"name": "Also legal", "commander_legal": True},
        ]
        self.assertEqual(
            [c["name"] for c in legal_cards_first(rows)],
            ["Bolt", "Also legal", "Joke"],
        )
