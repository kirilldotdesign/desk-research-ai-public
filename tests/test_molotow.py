"""T4: Molotow parser on the saved page."""

import unittest

from collector.venues import parse_molotow
from tests.helpers import VenueChecks, page


class MolotowTest(VenueChecks, unittest.TestCase):
    venue = "Molotow"

    @classmethod
    def setUpClass(cls):
        cls.events = parse_molotow(page("molotow.html"))

    def test_known_event(self):
        fat_dog = [e for e in self.events if e["title"].startswith("FAT DOG")][0]
        self.assertEqual(fat_dog["url"], "https://molotowclub.com/programm/programm.php?nr=66340")
        self.assertEqual(fat_dog["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-05 19:00")
        self.assertIn("Support: SILVERWINGKILLER", fat_dog["title"])
        self.assertTrue(fat_dog["text"].startswith("Konzert, Club"))
        death_valley = [e for e in self.events if e["title"] == "DEATH VALLEY GIRLS"][0]
        self.assertTrue(death_valley["text"].startswith("Konzert, Top Ten Bar"))


if __name__ == "__main__":
    unittest.main()
