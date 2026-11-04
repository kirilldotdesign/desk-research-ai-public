"""T1: schema switches the template from AI news to Hamburg club events.

The database test runs only when TEST_DATABASE_URL points to a throwaway Postgres
(never the production database); otherwise it is skipped.
"""

import os
import re
import unittest
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
AI_SOURCES = ["Hacker News", "Hacker News: Anthropic", "Hacker News: OpenAI", "arXiv cs.AI", "Хабр: ИИ"]
CLUBS = {
    "Grünspan": "gruenspan",
    "Uebel & Gefährlich": "uebel",
    "Molotow": "molotow",
    "Knust": "knust",
    "oh schon hell": "ohschonhell",
    "Concert News": "concertnews",
    "sperrstunde": "sperrstunde",
    "Golden Pudel Club": "pudel",
    "Hafenklang": "hafenklang",
    "Südpol": "suedpol",
    "Rote Flora": "roteflora",
    "MS Stubnitz": "stubnitz",
}


class SchemaTextTest(unittest.TestCase):
    def setUp(self):
        self.sql = SCHEMA.read_text()

    def test_no_ai_sources_are_seeded(self):
        seed = self.sql[self.sql.index("INSERT INTO sources"):]
        for name in AI_SOURCES:
            self.assertNotIn(f"('{name}'", seed)

    def test_club_sources_are_seeded(self):
        for name, kind in CLUBS.items():
            self.assertRegex(self.sql, rf"\('{re.escape(name)}',\s*'{kind}'")

    def test_new_columns(self):
        for column in ("starts_at", "venue", "event_type"):
            self.assertIn(f"ADD COLUMN IF NOT EXISTS {column}", self.sql)


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL not set")
class SchemaDatabaseTest(unittest.TestCase):
    def setUp(self):
        import psycopg

        self.conn = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")

    def tearDown(self):
        self.conn.close()

    def apply(self):
        self.conn.execute(SCHEMA.read_text())

    def test_applies_twice_and_removes_ai_data(self):
        self.apply()
        # simulate the old template state: an AI source with a material and a finding
        source_id = self.conn.execute(
            "INSERT INTO sources (name, kind, url) VALUES ('Hacker News', 'hn', 'x') RETURNING id"
        ).fetchone()[0]
        material_id = self.conn.execute(
            "INSERT INTO materials (source_id, url, title) VALUES (%s, 'https://a', 'AI') RETURNING id",
            (source_id,),
        ).fetchone()[0]
        self.conn.execute(
            "INSERT INTO findings (material_id, summary, model, prompt_version) VALUES (%s, 's', 'm', 'v1')",
            (material_id,),
        )
        self.apply()  # second run must not fail and must clean up
        names = {r[0] for r in self.conn.execute("SELECT name FROM sources")}
        self.assertEqual(names, set(CLUBS))
        off = {r[0] for r in self.conn.execute("SELECT name FROM sources WHERE NOT active")}
        self.assertEqual(off, {"sperrstunde"})  # robots.txt blocks AI crawlers, Kirill decides
        self.assertEqual(self.conn.execute("SELECT count(*) FROM materials").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM findings").fetchone()[0], 0)
        self.apply()  # third run: still idempotent


if __name__ == "__main__":
    unittest.main()
