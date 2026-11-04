"""SPEC 3 T9: one venue name across sources; aggregator vs venue site duplicates on real pages."""

import os
import unittest
from pathlib import Path

from collector.dedup import canonical_venue, same_venue
from collector.main import upcoming
from collector.venues import parse_ohschonhell, parse_pudel
from tests.helpers import SAVED_ON, page


class AliasTest(unittest.TestCase):
    def test_spellings(self):
        self.assertEqual(canonical_venue("Gruenspan"), "Grünspan")
        self.assertEqual(canonical_venue("Uebel und Gefährlich"), "Uebel & Gefährlich")
        self.assertEqual(canonical_venue("Uebel & Gefährlich [ ]"), "Uebel & Gefährlich")
        self.assertEqual(canonical_venue("Jazz Café (Mojo Club)"), "Mojo Club")
        self.assertEqual(canonical_venue("Hafenklang Goldener Salon"), "Hafenklang")
        self.assertEqual(canonical_venue("Knust"), "Knust")

    def test_fabrik_is_not_gaengeviertel(self):
        self.assertFalse(same_venue("Fabrik", "Fabrik Im Gängeviertel"))
        self.assertTrue(same_venue("Fabrik Im Gängeviertel", "Gängeviertel"))


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL not set")
class PudelTwoSourcesTest(unittest.TestCase):
    """The same 20 Pudel nights come from ohschonhell (22:00 everywhere) and pudel.com (exact times)."""

    def setUp(self):
        import psycopg

        self.conn = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        self.conn.execute((Path(__file__).resolve().parents[1] / "db" / "schema.sql").read_text())

    def tearDown(self):
        self.conn.close()

    def source(self, kind):
        return self.conn.execute("SELECT id FROM sources WHERE kind = %s", (kind,)).fetchone()[0]

    def test_venue_site_time_wins(self):
        from collector.main import save

        osh = [e for e in upcoming(parse_ohschonhell(page("ohschonhell.json")), now=SAVED_ON) if e["venue"] == "Golden Pudel Club"]
        pudel = upcoming(parse_pudel(page("pudel.html")), now=SAVED_ON)
        for e in osh:
            save(self.conn, self.source("ohschonhell"), None, e, True)
        for e in pudel:
            save(self.conn, self.source("pudel"), None, e, False)
        for e in osh:  # next morning the aggregator comes again
            save(self.conn, self.source("ohschonhell"), None, e, True)
        rows = self.conn.execute(
            "SELECT m.title, to_char(m.starts_at AT TIME ZONE 'Europe/Berlin', 'DD.MM HH24:MI'), s.kind"
            " FROM materials m JOIN sources s ON s.id = m.source_id WHERE m.venue = 'Golden Pudel Club'"
        ).fetchall()
        self.assertEqual(len(rows), len(pudel))
        self.assertTrue(all(kind == "pudel" for _, _, kind in rows))
        tripno = [when for title, when, _ in rows if title.startswith("Ab 19 Uhr: TRIPNO")]
        self.assertEqual(tripno, ["08.11 19:00"])


if __name__ == "__main__":
    unittest.main()
