"""T9: morning digest by weekday."""

import os
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

from bot.events import BERLIN, digest_days, digest_title


class DigestDaysTest(unittest.TestCase):
    def test_every_weekday(self):
        monday = date(2026, 11, 2)
        expected = {
            0: [0], 1: [0], 2: [0], 3: [0],  # Mon–Thu: today
            4: [0, 1, 2],                    # Fri: Fri + Sat + Sun
            5: [0], 6: [0],                  # Sat, Sun: that day
        }
        for offset, days in expected.items():
            today = monday + timedelta(days=offset)
            self.assertEqual(digest_days(today), [today + timedelta(days=d) for d in days], today)

    def test_titles(self):
        self.assertEqual(digest_title([date(2026, 11, 4)]), "Сегодня, Mi 04.11")
        self.assertEqual(digest_title(digest_days(date(2026, 11, 6))), "Выходные: Fr 06.11 – So 08.11")


class DigestTextTest(unittest.TestCase):
    def test_long_list_is_cut_for_telegram(self):
        from bot.main import MAX_MESSAGE, digest_text

        starts = datetime(2026, 11, 6, 20, 0, tzinfo=BERLIN)
        rows = [(starts, "Molotow", f"Band {i}", "Indie-Rock", f"https://m/{i}") for i in range(200)]
        text = digest_text([starts.date()], rows)
        self.assertLessEqual(len(text), MAX_MESSAGE)
        self.assertIn("в ленте", text)

    def test_empty_day(self):
        from bot.main import digest_text

        self.assertIn("Ничего не нашёл", digest_text([date(2026, 11, 4)], []))


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "TEST_DATABASE_URL not set")
class SendDigestTest(unittest.TestCase):
    def setUp(self):
        import psycopg

        self.conn = psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True)
        self.conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        self.conn.execute((Path(__file__).resolve().parents[1] / "db" / "schema.sql").read_text())
        self.conn.execute("INSERT INTO subscribers (chat_id, name) VALUES (1, 'k')")
        self.conn.execute("INSERT INTO runs (service, status, finished_at) VALUES ('collector', 'finished', now())")
        source = self.conn.execute("SELECT id FROM sources WHERE name = 'Knust'").fetchone()[0]
        self.now = datetime.now(BERLIN)
        today_late = self.now.replace(hour=23, minute=30, second=0, microsecond=0)
        for title, starts in (("tonight", today_late), ("in a week", today_late + timedelta(days=7))):
            m = self.conn.execute(
                "INSERT INTO materials (source_id, url, title, starts_at, venue, status) VALUES (%s, %s, %s, %s, 'Knust', 'done') RETURNING id",
                (source, f"https://k/{title}", title, starts),
            ).fetchone()[0]
            self.conn.execute(
                "INSERT INTO findings (material_id, entity, summary, event_type, model, prompt_version) VALUES (%s, 'Knust', 'Indie', 'Konzert', 'm', 'v2')",
                (m,),
            )

    def tearDown(self):
        self.conn.close()

    def test_once_a_day_with_todays_events(self):
        from bot import main as bot

        with mock.patch.object(bot, "say") as say:
            bot.send_new(self.conn, now=self.now)
            bot.send_new(self.conn, now=self.now)  # second call the same day: nothing
        self.assertEqual(say.call_count, 1)
        text = say.call_args[0][1]
        self.assertIn("tonight", text)
        if digest_days(self.now.date()) == [self.now.date()]:
            self.assertNotIn("in a week", text)


if __name__ == "__main__":
    unittest.main()
