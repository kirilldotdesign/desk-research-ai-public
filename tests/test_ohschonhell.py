"""SPEC 3 T1: ohschonhell aggregator (JSON) on the saved response."""

import unittest

from collector.venues import parse_ohschonhell
from tests.helpers import page


class OhschonhellTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = parse_ohschonhell(page("ohschonhell.json"))

    def test_many_events_many_venues(self):
        self.assertGreaterEqual(len(self.events), 50)
        self.assertGreaterEqual(len({e["venue"] for e in self.events}), 20)

    def test_every_event_is_complete(self):
        for e in self.events:
            self.assertTrue(e["title"])
            self.assertTrue(e["url"].startswith("https://ohschonhell.de/date/"), e["url"])
            self.assertIsNotNone(e["starts_at"].tzinfo)

    def test_html_entities_are_decoded(self):
        titles = " ".join(e["title"] for e in self.events)
        self.assertNotIn("&#82", titles)
        self.assertIn("“Wuff”", titles)

    def test_known_pudel_event(self):
        e = [e for e in self.events if e["title"].startswith("Speckman & Friends")][0]
        self.assertEqual(e["venue"], "Golden Pudel Club")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-05 22:00")

    def test_lineup_text_keeps_genres(self):
        e = [e for e in self.events if e["title"] == "OPEN DECKS by ODC"][0]
        self.assertIn("Baile Funk", e["text"])


if __name__ == "__main__":
    unittest.main()
