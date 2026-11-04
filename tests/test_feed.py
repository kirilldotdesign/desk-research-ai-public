"""T8: feed line format, 14-day window and order."""

import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot.events import BERLIN, event_line, when


class LineTest(unittest.TestCase):
    def test_line(self):
        starts = datetime(2026, 11, 6, 20, 0, tzinfo=BERLIN)
        self.assertEqual(
            event_line(starts, "Molotow", "Fahnenflucht", "Deutschpunk"),
            "Fr 06.11 20:00 · Molotow · Fahnenflucht — Deutschpunk",
        )

    def test_no_time_no_zero(self):
        self.assertEqual(when(datetime(2026, 11, 8, 0, 0, tzinfo=BERLIN)), "So 08.11")

    def test_utc_is_shown_in_hamburg_time(self):
        utc = datetime(2026, 11, 6, 18, 0, tzinfo=timezone.utc)
        self.assertEqual(when(utc), "Fr 06.11 19:00")

    def test_summary_equal_to_title_is_not_repeated(self):
        starts = datetime(2026, 11, 6, 20, 0, tzinfo=BERLIN)
        self.assertEqual(event_line(starts, "Knust", "Flohmarkt", "flohmarkt"), "Fr 06.11 20:00 · Knust · Flohmarkt")


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL not set")
class FeedDatabaseTest(unittest.TestCase):
    def setUp(self):
        import psycopg

        self.conn = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        self.conn.execute((Path(__file__).resolve().parents[1] / "db" / "schema.sql").read_text())
        source = self.conn.execute("SELECT id FROM sources WHERE name = 'Molotow'").fetchone()[0]
        now = datetime.now(BERLIN).replace(minute=0, second=0, microsecond=0)
        for title, starts in (
            ("yesterday", now - timedelta(days=1, hours=2)),
            ("later", now + timedelta(days=3)),
            ("soon", now + timedelta(days=1)),
            ("too far", now + timedelta(days=20)),
        ):
            material = self.conn.execute(
                "INSERT INTO materials (source_id, url, title, starts_at, venue, status) VALUES (%s, %s, %s, %s, 'Molotow', 'done') RETURNING id",
                (source, f"https://m/{title}", title, starts),
            ).fetchone()[0]
            self.conn.execute(
                "INSERT INTO findings (material_id, entity, summary, event_type, model, prompt_version) VALUES (%s, 'Molotow', 'Indie', 'Konzert', 'm', 'v2')",
                (material,),
            )

    def tearDown(self):
        self.conn.close()

    def test_window_and_order(self):
        from bot.main import page_data

        findings = page_data(self.conn)["findings"]
        self.assertEqual([f["title"] for f in findings], ["soon", "later"])
        self.assertRegex(findings[0]["line"], r"^(Mo|Di|Mi|Do|Fr|Sa|So) \d\d\.\d\d \d\d:\d\d · Molotow · soon — Indie$")
        self.assertEqual(findings[0]["event_type"], "Konzert")


if __name__ == "__main__":
    unittest.main()
