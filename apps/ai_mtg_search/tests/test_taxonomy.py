import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.mtg_taxonomy import (
    COLOR_GROUPS,
    expand_search_texts,
    get_node,
    match_color_identity,
    match_nodes,
)


class TaxonomyTests(unittest.TestCase):
    def test_board_wipe_is_mass_removal(self):
        keys = [node["key"] for node in match_nodes("cheap board wipe")]
        self.assertIn("interaction.mass_removal", keys)
        texts = expand_search_texts("cheap board wipe")
        self.assertEqual(texts[0], "cheap board wipe")
        self.assertTrue(any("destroy all creatures" in t for t in texts))

    def test_ramp_walks_children(self):
        texts = expand_search_texts("ramp")
        joined = " ".join(texts).lower()
        self.assertIn("search your library for a land", joined)
        self.assertTrue(any("treasure" in t.lower() for t in texts) or "add {" in joined)

    def test_tax_and_stax_are_siblings(self):
        self.assertIsNotNone(get_node("interaction.stax"))
        self.assertIsNotNone(get_node("interaction.tax"))
        tax_keys = [node["key"] for node in match_nodes("rhystic tax piece")]
        stax_keys = [node["key"] for node in match_nodes("winter orb stax")]
        self.assertIn("interaction.tax", tax_keys)
        self.assertIn("interaction.stax", stax_keys)

    def test_theft_and_ability_denial(self):
        theft = [node["key"] for node in match_nodes("steal a creature")]
        denial = [node["key"] for node in match_nodes("loses all abilities")]
        self.assertTrue(any(k.startswith("theft") for k in theft))
        self.assertIn("interaction.ability_denial", denial)

    def test_bare_control_does_not_match_theft(self):
        keys = [node["key"] for node in match_nodes("gain control of target")]
        self.assertTrue(any(k.startswith("theft") for k in keys))
        self.assertNotIn("control", keys)

    def test_search_is_not_expanded_as_tutor(self):
        keys = [node["key"] for node in match_nodes("search for flying creatures")]
        self.assertNotIn("card_advantage.tutor", keys)

    def test_guild_name_maps_to_color_identity(self):
        self.assertEqual(match_color_identity("best ramp in rakdos"), ["B", "R"])
        self.assertEqual(COLOR_GROUPS["dimir"], ["U", "B"])
        self.assertIsNone(match_color_identity("make squirrel tokens"))

    def test_bare_mill_expands_self_and_opponent(self):
        keys = [node["key"] for node in match_nodes("mill")]
        self.assertEqual(keys, ["graveyard.mill"])
        joined = " ".join(expand_search_texts("mill")).lower()
        self.assertIn("your library into your graveyard", joined)
        self.assertIn("target player mills", joined)

    def test_dredge_is_self_mill_not_hate(self):
        keys = [node["key"] for node in match_nodes("dredge")]
        self.assertEqual(keys, ["graveyard.mill.self"])
        self.assertNotIn("graveyard.hate", keys)

    def test_graveyard_hate_is_not_synergy(self):
        keys = [node["key"] for node in match_nodes("graveyard hate")]
        self.assertEqual(keys, ["graveyard.hate"])
        joined = " ".join(expand_search_texts("rest in peace")).lower()
        self.assertIn("exile", joined)

    def test_sacrifice_synergy_vs_edict(self):
        sac = [node["key"] for node in match_nodes("aristocrats sac outlet")]
        edict = [node["key"] for node in match_nodes("forced sacrifice")]
        self.assertTrue(any(k.startswith("sacrifice") for k in sac))
        self.assertIn("interaction.targeted_removal.edict", edict)

    def test_burn_is_interaction_methodology(self):
        keys = [node["key"] for node in match_nodes("burn")]
        self.assertEqual(keys, ["interaction.burn"])
        joined = " ".join(expand_search_texts("direct damage")).lower()
        self.assertIn("deals damage", joined)

    def test_cascade_and_discover_are_cheat_methods(self):
        self.assertEqual(
            [node["key"] for node in match_nodes("cascade")],
            ["card_advantage.cheat.cascade"],
        )
        self.assertEqual(
            [node["key"] for node in match_nodes("discover")],
            ["card_advantage.cheat.discover"],
        )
        joined = " ".join(expand_search_texts("cheat into play")).lower()
        self.assertIn("without paying", joined)
        self.assertIn("cascade", joined)

    def test_json_labels_are_on_the_tree(self):
        wipe = get_node("interaction.mass_removal")
        self.assertIn("Wrath of God", wipe["examples"])
        self.assertTrue(any("destroy all" in p for p in wipe["card_text_regex"]))
        self.assertIsNotNone(get_node("ramp.fast_mana"))
        self.assertIsNotNone(get_node("ramp.ritual"))


if __name__ == "__main__":
    unittest.main()
