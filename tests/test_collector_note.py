"""SPEC 3 T14: a broken source is named in the run note (found: Concert News gave 0 on the server)."""

import os
import unittest
from pathlib import Path
from unittest import mock


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL not set")
class BrokenSourceNoteTest(unittest.TestCase):
    def test_note_names_broken_source(self):
        import psycopg

        from collector import main as collector

        conn = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.execute((Path(__file__).resolve().parents[1] / "db" / "schema.sql").read_text())
        conn.execute("UPDATE sources SET active = (kind = 'concertnews_json')")

        def boom(url):
            raise RuntimeError("HTTP Error 403: Forbidden")

        with mock.patch.object(collector, "fetch", boom), mock.patch.object(collector.db, "connect", lambda: conn):
            collector.main()
        note = conn.execute("SELECT note FROM runs WHERE service = 'collector' ORDER BY id DESC LIMIT 1").fetchone()[0]
        # schema re-run in main() also re-activates sperrstunde; the order of sources in the note is not fixed
        self.assertIn("недоступны: ", note)
        self.assertIn("Concert News: HTTP Error 403", note)
        conn.close()


if __name__ == "__main__":
    unittest.main()
