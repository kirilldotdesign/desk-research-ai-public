"""SPEC 3 T6: Südpol programme (multi-day events, link = page anchor)."""

import unittest

from collector.venues import parse_suedpol
from tests.helpers import VenueChecks, page


class SuedpolTest(VenueChecks, unittest.TestCase):
    venue = "Südpol"

    @classmethod
    def setUpClass(cls):
        cls.events = parse_suedpol(page("suedpol.html"))

    def test_multi_day_event_starts_on_first_day(self):
        e = [e for e in self.events if e["title"] == "Expedition Südpol"][0]
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-13 23:59")
        self.assertEqual(e["url"], "https://www.suedpol.org/#event_4290")
        self.assertIn("Paluli", e["text"])

    def test_lineup_kept(self):
        e = [e for e in self.events if "Alle Lampen an" in e["title"]][0]
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d"), "2026-11-07")
        self.assertIn("Tipping Point", e["text"])


if __name__ == "__main__":
    unittest.main()
