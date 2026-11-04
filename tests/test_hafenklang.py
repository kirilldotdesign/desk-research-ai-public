"""SPEC 3 T5: Hafenklang programme page."""

import unittest

from collector.venues import parse_hafenklang
from tests.helpers import VenueChecks, page


class HafenklangTest(VenueChecks, unittest.TestCase):
    venue = "Hafenklang"

    @classmethod
    def setUpClass(cls):
        cls.events = parse_hafenklang(page("hafenklang.html"))

    def test_known_event_with_genre_and_beginn(self):
        e = [e for e in self.events if e["title"].startswith("Keele")][0]
        self.assertEqual(e["url"], "https://www.hafenklang.com/programm?cpnr=70065")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-05 20:00")
        self.assertIn("Post Punk - Indie", e["text"])
        self.assertNotIn("Post Punk", e["title"])

    def test_extreme_show_is_there(self):
        e = [e for e in self.events if e["title"].startswith("Teratoma")][0]
        self.assertIn("trapped in purgatory", e["text"])


if __name__ == "__main__":
    unittest.main()
