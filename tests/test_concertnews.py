"""SPEC 3 T2: concert-news calendar on the saved page."""

import unittest

from collector.main import upcoming
from collector.venues import parse_concertnews
from tests.helpers import SAVED_ON, page


class ConcertNewsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = parse_concertnews(page("concertnews.html"))

    def test_many_events_many_venues(self):
        window = upcoming(self.events, now=SAVED_ON)
        self.assertGreaterEqual(len(window), 100)
        self.assertGreaterEqual(len({e["venue"] for e in window}), 30)

    def test_known_events(self):
        by = {(e["title"], e["venue"]) for e in self.events if e["starts_at"].strftime("%d.%m") == "05.11"}
        self.assertIn(("Death Valley Girls", "Molotow"), by)
        self.assertIn(("Etran de L'Aïr", "Jazz Café (Mojo Club)"), by)
        self.assertIn(("Keele - Release Show + Joe Astray", "Hafenklang"), by)

    def test_presented_prefix_is_removed(self):
        self.assertTrue(any(e["title"] == "Pascow" and e["venue"] == "Markthalle" for e in self.events))

    def test_urls_unique_and_cancelled_hidden(self):
        urls = [e["url"] for e in self.events]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertFalse(any("ABGESAGT" in e["title"].upper() for e in upcoming(self.events, now=SAVED_ON)))


if __name__ == "__main__":
    unittest.main()
