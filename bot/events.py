"""SPEC 1, T8–T9: how one event looks and which days the morning digest covers."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
WINDOW_DAYS = 14
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def when(starts_at):
    """'Fr 06.11 20:00'; no time known (00:00) -> 'Fr 06.11'."""
    local = starts_at.astimezone(BERLIN)
    text = f"{WEEKDAYS[local.weekday()]} {local:%d.%m}"
    if (local.hour, local.minute) != (0, 0):
        text += f" {local:%H:%M}"
    return text


def event_line(starts_at, venue, title, summary):
    """SPEC decision 3: date, time, club, title as on the site, one phrase."""
    line = f"{when(starts_at)} · {venue} · {title}"
    if summary and summary.strip().lower() != title.strip().lower():
        line += f" — {summary}"
    return line


def digest_days(today):
    """SPEC decision 9: Mon–Thu today; Fri Fri+Sat+Sun; Sat Saturday; Sun Sunday."""
    if today.weekday() == 4:
        return [today + timedelta(days=i) for i in range(3)]
    return [today]


def digest_title(days):
    if len(days) > 1:
        return f"Выходные: {WEEKDAYS[days[0].weekday()]} {days[0]:%d.%m} – {WEEKDAYS[days[-1].weekday()]} {days[-1]:%d.%m}"
    return f"Сегодня, {WEEKDAYS[days[0].weekday()]} {days[0]:%d.%m}"


def window(now=None):
    """Feed window: from the start of today (Hamburg) to WINDOW_DAYS ahead."""
    now = (now or datetime.now(BERLIN)).astimezone(BERLIN)
    first = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return first, first + timedelta(days=WINDOW_DAYS + 1)


def today_in_hamburg(now=None) -> date:
    return (now or datetime.now(BERLIN)).astimezone(BERLIN).date()
