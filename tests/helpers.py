"""Shared helpers for venue parser tests. Fixtures were saved on 04.11.2026."""

from datetime import datetime
from pathlib import Path

from collector.venues import BERLIN

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAVED_ON = datetime(2026, 11, 4, 12, 0, tzinfo=BERLIN)


def page(name):
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


class VenueChecks:
    """Mixin: every parser must give events with title, url, date and a real start time."""

    venue = None
    events = []

    def test_has_events(self):
        self.assertGreaterEqual(len(self.events), 1)

    def test_every_event_is_complete(self):
        for e in self.events:
            self.assertTrue(e["title"], e)
            self.assertTrue(e["url"].startswith("https://"), e)
            self.assertEqual(e["venue"], self.venue)
            self.assertEqual(e["starts_at"].tzinfo, BERLIN)

    def test_most_events_have_a_time(self):
        with_time = [e for e in self.events if (e["starts_at"].hour, e["starts_at"].minute) != (0, 0)]
        self.assertGreaterEqual(len(with_time) / len(self.events), 0.9)

    def test_urls_are_unique(self):
        urls = [e["url"] for e in self.events]
        self.assertEqual(len(urls), len(set(urls)))
