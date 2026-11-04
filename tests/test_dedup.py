"""T6: duplicates between sources."""

import os
import unittest

from collector.dedup import find_duplicate, same_title, same_venue
from collector.venues import at


def event(venue, title, day="2026-11-05"):
    return {"venue": venue, "title": title, "url": f"https://{venue}/{title}", "text": "", "starts_at": at(day, "20:00")}


class DedupRulesTest(unittest.TestCase):
    def test_same_venue_with_room_suffix(self):
        self.assertTrue(same_venue("Uebel & Gefährlich", "Uebel & Gefährlich - Turmzimmer"))
        self.assertFalse(same_venue("Knust", "Molotow"))

    def test_title_with_support_is_same(self):
        self.assertTrue(same_title("FAT DOG", "FAT DOG · Support: SILVERWINGKILLER"))
        self.assertTrue(same_title("Science Slam", "SCIENCE SLAM"))
        self.assertFalse(same_title("Mammoth", "Boy Harsher"))

    def test_find_duplicate(self):
        candidates = [(1, "Molotow", "FAT DOG · Support: SILVERWINGKILLER", False), (2, "Knust", "JONNY5", False)]
        self.assertEqual(find_duplicate(event("Molotow", "Fat Dog"), candidates)[0], 1)
        # same artist, other venue -> different event
        self.assertIsNone(find_duplicate(event("Uebel & Gefährlich", "JONNY5"), candidates))


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL not set")
class DedupDatabaseTest(unittest.TestCase):
    def setUp(self):
        import psycopg
        from pathlib import Path

        self.conn = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        self.conn.execute((Path(__file__).resolve().parents[1] / "db" / "schema.sql").read_text())
        self.conn.execute("INSERT INTO sources (name, kind, url) VALUES ('oh schon hell', 'ohschonhell', 'x')")

    def tearDown(self):
        self.conn.close()

    def source(self, name):
        return self.conn.execute("SELECT id FROM sources WHERE name = %s", (name,)).fetchone()[0]

    def rows(self):
        return self.conn.execute("SELECT url FROM materials ORDER BY id").fetchall()

    def test_venue_link_wins_both_ways(self):
        from collector.main import save

        aggregator, molotow = self.source("oh schon hell"), self.source("Molotow")
        from_aggregator = dict(event("Molotow", "Fat Dog"), url="https://ohschonhell.de/date/fat-dog")
        from_venue = dict(event("Molotow", "FAT DOG · Support: X"), url="https://molotowclub.com/programm/programm.php?nr=1")

        # aggregator first, then the venue: the aggregator row is replaced
        self.assertTrue(save(self.conn, aggregator, None, from_aggregator, True))
        self.assertTrue(save(self.conn, molotow, None, from_venue, False))
        self.assertEqual(self.rows(), [(from_venue["url"],)])

        # aggregator again: skipped, the venue row stays
        self.assertFalse(save(self.conn, aggregator, None, from_aggregator, True))
        self.assertEqual(self.rows(), [(from_venue["url"],)])

    def test_two_shows_of_one_venue_on_one_day_both_stay(self):
        from collector.main import save

        molotow = self.source("Molotow")
        early = dict(event("Molotow", "Top Ten Bar"), url="https://molotowclub.com/programm/programm.php?nr=2")
        late = dict(event("Molotow", "Top Ten Bar"), url="https://molotowclub.com/programm/programm.php?nr=3")
        self.assertTrue(save(self.conn, molotow, None, early))
        self.assertTrue(save(self.conn, molotow, None, late))
        self.assertEqual(len(self.rows()), 2)


if __name__ == "__main__":
    unittest.main()
