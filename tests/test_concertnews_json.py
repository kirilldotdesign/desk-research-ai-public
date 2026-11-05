"""SPEC-3 T18: Concert News via the GitHub mirror gives the same events as the page itself."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from collector import mirror_concertnews
from collector.dedup import AGGREGATORS
from collector.venues import BERLIN, PARSERS, parse_concertnews, parse_concertnews_json
from tests.helpers import page


class ConcertNewsJsonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = page("concertnews.html")
        cls.direct = parse_concertnews(cls.html)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "concertnews.json"
            with mock.patch.object(mirror_concertnews, "fetch", lambda url: cls.html):
                mirror_concertnews.main(str(path))
            cls.file = path.read_text(encoding="utf-8")
        cls.mirrored = parse_concertnews_json(cls.file)

    def test_same_events_after_round_trip(self):
        self.assertGreaterEqual(len(self.mirrored), 100)
        key = lambda e: (e["url"], e["title"], e["venue"], e["starts_at"])
        self.assertEqual([key(e) for e in self.mirrored], [key(e) for e in self.direct])

    def test_dates_back_in_berlin_time(self):
        self.assertTrue(all(e["starts_at"].tzinfo == BERLIN for e in self.mirrored))

    def test_only_facts_in_file(self):
        rows = json.loads(self.file)
        self.assertEqual(set(rows[0]), {"url", "title", "venue", "starts_at"})
        self.assertNotIn("<", self.file)  # no raw HTML in the public repo

    def test_empty_page_keeps_old_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "concertnews.json"
            path.write_text("old", encoding="utf-8")
            with mock.patch.object(mirror_concertnews, "fetch", lambda url: "<html></html>"):
                with self.assertRaises(SystemExit):
                    mirror_concertnews.main(str(path))
            self.assertEqual(path.read_text(encoding="utf-8"), "old")

    def test_registered_as_aggregator(self):
        self.assertIs(PARSERS["concertnews_json"], parse_concertnews_json)
        self.assertIn("concertnews_json", AGGREGATORS)


if __name__ == "__main__":
    unittest.main()
