"""T5: Knust parser on the saved programme page."""

import unittest

from collector.venues import parse_knust
from tests.helpers import VenueChecks, page


class KnustTest(VenueChecks, unittest.TestCase):
    venue = "Knust"

    @classmethod
    def setUpClass(cls):
        cls.events = parse_knust(page("knust.html"))

    def test_known_event(self):
        e = [e for e in self.events if e["url"].endswith("/event/nichtseattle_111637923/")][0]
        self.assertEqual(e["title"], "NICHTSEATTLE - SUPPORT: BLUMES")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-04 20:30")
        self.assertEqual(e["text"], "SINGER/SONGWRITER")


if __name__ == "__main__":
    unittest.main()
