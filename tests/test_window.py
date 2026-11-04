"""T2: the 14-day window and hidden (cancelled / sold out / postponed) events."""

import unittest
from datetime import timedelta

from collector.main import upcoming
from collector.venues import at
from tests.helpers import SAVED_ON


def event(title, day):
    return {"title": title, "url": "https://x", "text": "", "venue": "V", "starts_at": at(day, "20:00")}


class WindowTest(unittest.TestCase):
    def test_window_and_hidden(self):
        events = [
            event("gestern", "2026-11-03"),
            event("heute", "2026-11-04"),
            event("in 14 Tagen", "2026-11-18"),
            event("in 15 Tagen", "2026-11-19"),
            event("BAND – ABGESAGT", "2026-11-05"),
            event("Band – Ausverkauft", "2026-11-05"),
            event("CLAWFINGER – VERSCHOBEN", "2026-11-05"),
            event("Fällt leider aus : EDGING", "2026-11-05"),
        ]
        kept = [e["title"] for e in upcoming(events, now=SAVED_ON)]
        self.assertEqual(kept, ["heute", "in 14 Tagen"])

    def test_today_late_event_is_kept_in_the_morning(self):
        morning = SAVED_ON.replace(hour=7) - timedelta(minutes=1)
        self.assertEqual(len(upcoming([event("heute", "2026-11-04")], now=morning)), 1)


if __name__ == "__main__":
    unittest.main()
