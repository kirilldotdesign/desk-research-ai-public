"""SPEC 3 T7: Rote Flora programme — music nights only."""

import unittest

from collector.venues import parse_roteflora
from tests.helpers import VenueChecks, page


class RoteFloraTest(VenueChecks, unittest.TestCase):
    venue = "Rote Flora"

    @classmethod
    def setUpClass(cls):
        cls.events = parse_roteflora(page("roteflora.html"))

    def test_music_only(self):
        titles = [e["title"] for e in self.events]
        self.assertIn("37 Jahre Rote Flora – Punkrock Festival", titles)
        self.assertIn("Konzert", titles)
        self.assertFalse(any("Kino" in t or "Vortrag" in t for t in titles), titles)

    def test_festival_date_and_link(self):
        e = [e for e in self.events if "Punkrock" in e["title"]][0]
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-13 18:00")
        self.assertIn("/veranstaltung/37-jahre-rote-flora/", e["url"])


if __name__ == "__main__":
    unittest.main()
