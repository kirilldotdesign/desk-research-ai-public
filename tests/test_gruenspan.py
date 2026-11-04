"""T2: Grünspan parser on the saved page."""

import unittest

from collector.venues import parse_gruenspan
from tests.helpers import VenueChecks, page


class GruenspanTest(VenueChecks, unittest.TestCase):
    venue = "Grünspan"

    @classmethod
    def setUpClass(cls):
        cls.events = parse_gruenspan(page("gruenspan.html"))

    def test_known_event(self):
        mammoth = [e for e in self.events if e["title"] == "Mammoth"]
        self.assertEqual(len(mammoth), 1)
        e = mammoth[0]
        self.assertEqual(e["url"], "https://www.gruenspan.de/konzerte/mammoth/")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-05 19:00")


if __name__ == "__main__":
    unittest.main()
