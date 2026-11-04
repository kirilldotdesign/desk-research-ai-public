"""SPEC 3 T4: Golden Pudel programme page (exact start times, unlike the aggregator)."""

import unittest

from collector.venues import parse_pudel
from tests.helpers import VenueChecks, page


class PudelTest(VenueChecks, unittest.TestCase):
    venue = "Golden Pudel Club"

    @classmethod
    def setUpClass(cls):
        cls.events = parse_pudel(page("pudel.html"))

    def test_exact_times(self):
        times = {e["title"][:20]: e["starts_at"].strftime("%d.%m %H:%M") for e in self.events}
        self.assertEqual(times["Ab 19 Uhr: TRIPNO w/"], "08.11 19:00")
        self.assertEqual(times["Das Ohr zum Sonntag:"], "29.11 20:00")

    def test_weekly_series_listed_once_per_date(self):
        afro = sorted(e["starts_at"].strftime("%d.%m") for e in self.events if e["title"] == "Afrotronic")
        self.assertEqual(afro, ["04.11", "11.11", "18.11", "25.11"])

    def test_series_and_artist_links_in_text(self):
        e = [e for e in self.events if e["title"].startswith("Speckman")][0]
        self.assertIn("Donnerstags", e["text"])
        self.assertIn("soundcloud.com/speckman1", e["text"])
        self.assertIn("&", e["title"])


if __name__ == "__main__":
    unittest.main()
