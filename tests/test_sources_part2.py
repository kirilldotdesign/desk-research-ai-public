"""SPEC 4 (sources part 2): one test class per new source, on pages saved 04.11.2026."""

import unittest

from collector.main import upcoming
from collector.venues import (
    parse_cascadas, parse_fabrik, parse_frauhedi, parse_kampnagel, parse_kentclub,
    parse_krach, parse_markthalle, parse_ponybar, parse_vamh,
)
from tests.helpers import SAVED_ON, page


def find(events, start):
    return [e for e in events if e["title"].startswith(start)][0]


class Base:
    parser = file = None
    minimum = 3

    @classmethod
    def setUpClass(cls):
        cls.events = cls.parser(page(cls.file))

    def test_events_complete_and_unique(self):
        self.assertGreaterEqual(len(upcoming(self.events, now=SAVED_ON)), self.minimum)
        for e in self.events:
            self.assertTrue(e["title"] and e["venue"] and e["url"].startswith("https://"), e)
        self.assertEqual(len({e["url"] for e in self.events}), len(self.events))


class KrachTest(Base, unittest.TestCase):
    parser, file, minimum = staticmethod(parse_krach), "krach.html", 20

    def test_genres_and_venue(self):
        e = find(self.events, "Teratoma")
        self.assertEqual((e["venue"], e["starts_at"].strftime("%d.%m %H:%M")), ("Hafenklang", "04.11 19:00"))
        self.assertTrue(e["text"].startswith("Death Metal"))
        self.assertIn("Bambi Galore", {e["venue"] for e in self.events})


class MarkthalleTest(Base, unittest.TestCase):
    parser, file = staticmethod(parse_markthalle), "markthalle.html"

    def test_known(self):
        e = find(self.events, "Hatebreed")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d"), "2026-11-16")
        self.assertIn("/konzerte/", e["url"])


class KampnagelTest(Base, unittest.TestCase):
    parser, file, minimum = staticmethod(parse_kampnagel), "kampnagel.html", 1  # theatre house: few music nights

    def test_music_only(self):
        titles = " ".join(e["title"] for e in self.events)
        self.assertIn("ÜBERJAZZ", titles.upper())
        self.assertNotIn("Nele Neuhaus", titles)  # Krimifestival reading


class VamhTest(Base, unittest.TestCase):
    parser, file = staticmethod(parse_vamh), "vamh.html"

    def test_venue_from_ort(self):
        e = find(self.events, "Hörbar: González")
        self.assertEqual((e["venue"], e["starts_at"].strftime("%d.%m %H:%M")), ("Hörbar", "04.11 20:00"))


class FabrikTest(Base, unittest.TestCase):
    parser, file, minimum = staticmethod(parse_fabrik), "fabrik.html", 5

    def test_time(self):
        self.assertEqual(find(self.events, "LEAP")["starts_at"].strftime("%H:%M"), "20:00")


class FrauHediTest(Base, unittest.TestCase):
    parser, file = staticmethod(parse_frauhedi), "frauhedi.html"

    def test_balearic(self):
        e = find(self.events, "BALEARIC DISCO YACHTRIDE")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d"), "2026-11-07")


class PonyBarTest(Base, unittest.TestCase):
    parser, file = staticmethod(parse_ponybar), "ponybar.html"

    def test_time(self):
        self.assertEqual(find(self.events, "Live-Jazz")["starts_at"].strftime("%d.%m %H:%M"), "04.11 20:30")


class KentClubTest(Base, unittest.TestCase):
    parser, file = staticmethod(parse_kentclub), "kentclub.html"

    def test_date_from_link(self):
        e = find(self.events, "BACK TO HOUSE")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d"), "2026-11-07")


class CascadasTest(Base, unittest.TestCase):
    parser, file = staticmethod(lambda p: parse_cascadas(p, today=SAVED_ON.date())), "cascadas.html"

    def test_genre_and_time(self):
        e = find(self.events, "FUNKY DANCE NIGHT")
        self.assertEqual(e["starts_at"].strftime("%Y-%m-%d %H:%M"), "2026-11-06 21:00")
        self.assertIn("Boogie Funk", e["text"])


if __name__ == "__main__":
    unittest.main()
