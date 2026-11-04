"""Parsers of Hamburg venue programmes (SPEC 1).

Every parser takes the page as text and returns a list of events:
    {"url", "title", "text", "starts_at" (aware datetime, Europe/Berlin), "venue"}
Fetching, the 14-day window and cancelled events are handled in collector/main.py.
"""

import html as htmllib
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")

# words in a title or status that mean "do not show this event" (SPEC decision 7)
HIDDEN = re.compile(
    r"abgesagt|ausverkauft|verschoben|entf[äa]llt|f[äa]llt\s+(leider\s+)?aus|cancel+ed|sold\s*out|postponed",
    re.IGNORECASE,
)


def clean(fragment):
    """HTML fragment -> one line of plain text."""
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    return " ".join(htmllib.unescape(text).split())


def at(day, time=None):
    """'2026-11-05' + '19:00' (or '19.00') -> aware datetime in Hamburg; no time -> 00:00."""
    hour, minute = (0, 0)
    if time:
        hour, minute = (int(x) for x in re.split(r"[:.]", time.strip())[:2])
    year, month, dom = (int(x) for x in day.split("-"))
    return datetime(year, month, dom, hour, minute, tzinfo=BERLIN)


def de_date(text):
    """'05.11.2026' -> '2026-11-05'."""
    dom, month, year = text.strip().split(".")
    return f"{year}-{month}-{dom}"


# ---------- Grünspan: schema.org Event blocks + "Einlass" from the list ----------


def parse_gruenspan(page):
    doors = {}
    for article in re.findall(r'<article class="mec-event-article.*?</article>', page, re.S):
        link = re.search(r'class="mec-event-title"><a[^>]*href="([^"]+)"', article)
        time = re.search(r"Einlass:\s*([0-9]{1,2}[.:][0-9]{2})", article)
        if link:
            doors[link.group(1)] = time.group(1) if time else None
    events = []
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if not isinstance(data, dict) or data.get("@type") != "Event":
            continue
        url = data.get("url") or (data.get("offers") or {}).get("url")
        title = clean(data.get("name"))
        status = data.get("eventStatus") or ""
        if not url or not title:
            continue
        if any(s in status for s in ("Cancelled", "Postponed", "Rescheduled")):
            title += " – abgesagt"  # collector hides it
        events.append(
            {
                "url": url,
                "title": title,
                "text": clean(htmllib.unescape(data.get("description") or ""))[:1500],
                "starts_at": at(data["startDate"][:10], doors.get(url)),
                "venue": "Grünspan",
            }
        )
    return events


PARSERS = {"gruenspan": parse_gruenspan}
