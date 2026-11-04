"""T3: Uebel & Gefährlich parser on the saved page."""

import unittest

from collector.main import upcoming
from collector.venues import parse_uebel
from tests.helpers import SAVED_ON, VenueChecks, page


class UebelTest(VenueChecks, unittest.TestCase):
    venue = "Uebel & Gefährlich"

    @classmethod
    def setUpClass(cls):
        cls.events = parse_uebel(page("uebel.html"))

    def test_known_event_uses_beginn(self):
        slam = [e for e in self.events if e["title"] == "SCIENCE SLAM"][0]
        self.assertEqual(slam["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-04 20:00")
        self.assertIn("/veranstaltungen/", slam["url"])
        self.assertIn("Lesung", slam["text"])

    def test_cancelled_are_hidden(self):
        titles = " ".join(e["title"] for e in upcoming(self.events, now=SAVED_ON)).upper()
        for word in ("ABGESAGT", "AUSVERKAUFT", "VERSCHOBEN"):
            self.assertNotIn(word, titles)


if __name__ == "__main__":
    unittest.main()
