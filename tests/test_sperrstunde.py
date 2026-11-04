"""SPEC 3 T3: sperrstunde (DIY calendar) on the saved page."""

import unittest

from collector.venues import parse_sperrstunde
from tests.helpers import page


class SperrstundeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = parse_sperrstunde(page("sperrstunde.html"))

    def test_only_concerts_and_parties(self):
        self.assertGreaterEqual(len(self.events), 30)
        for e in self.events:
            categories = e["text"].split(";")[0]
            self.assertTrue("Konzert" in categories or "Party" in categories, categories)

    def test_known_event_with_genres(self):
        e = [e for e in self.events if e["title"].startswith("Sunset Images")][0]
        self.assertEqual(e["venue"], "MS Stubnitz")
        self.assertEqual(e["url"], "https://www.sperrstunde.org/events/2026-11-04-sunset-images-mx-ok-wait")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d"), "2026-11-04")
        self.assertIn("noise rock", e["text"])

    def test_talks_are_skipped(self):
        self.assertFalse(any("Anlaufpunkt" in e["title"] for e in self.events))

    def test_urls_unique(self):
        urls = [e["url"] for e in self.events]
        self.assertEqual(len(urls), len(set(urls)))


if __name__ == "__main__":
    unittest.main()
