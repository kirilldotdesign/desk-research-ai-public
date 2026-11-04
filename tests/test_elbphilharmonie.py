"""Elbphilharmonie programme page (first page, saved 04.11)."""

import unittest

from collector.venues import parse_elbphilharmonie
from tests.helpers import page


class ElbphilharmonieTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = parse_elbphilharmonie(page("elbphilharmonie.html"))

    def test_events(self):
        self.assertGreaterEqual(len(self.events), 5)
        for e in self.events:
            self.assertTrue(e["url"].startswith("https://www.elbphilharmonie.de/de/programm/"))
            self.assertTrue(e["venue"])  # Elbphilharmonie, Laeiszhalle and outreach venues

    def test_traditional_music(self):
        e = [e for e in self.events if e["title"] == "Shavnabada Chor"][0]
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-04 20:00")
        self.assertIn("Traditionelle Vokalmusik aus Georgien", e["text"])
        self.assertEqual(e["url"], "https://www.elbphilharmonie.de/de/programm/shavnabada-chor/28900")


if __name__ == "__main__":
    unittest.main()
