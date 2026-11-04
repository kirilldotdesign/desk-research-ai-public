"""SPEC 3 T8: MS Stubnitz events list (genres in "theme", no start time)."""

import unittest

from collector.venues import parse_stubnitz
from tests.helpers import page


class StubnitzTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = parse_stubnitz(page("stubnitz.html"))

    def test_has_events(self):
        self.assertGreaterEqual(len(self.events), 10)
        for e in self.events:
            self.assertEqual(e["venue"], "MS Stubnitz")
            self.assertTrue(e["url"].startswith("https://www.stubnitz.com/events/"))

    def test_known_event_with_genres(self):
        e = [e for e in self.events if e["title"].startswith("Horse Lords")][0]
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d"), "2026-11-07")
        self.assertIn("microtonal", e["text"])
        self.assertTrue(e["text"].startswith("Concert"))

    def test_urls_unique(self):
        urls = [e["url"] for e in self.events]
        self.assertEqual(len(urls), len(set(urls)))


if __name__ == "__main__":
    unittest.main()
