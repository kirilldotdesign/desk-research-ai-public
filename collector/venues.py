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


# ---------- Uebel & Gefährlich: <li itemtype="schema.org/Event"> list ----------

UEBEL_KIND = {"konzert": "Konzert", "klub": "Klub", "lesung": "Lesung"}


def parse_uebel(page):
    events = []
    for item in re.findall(r'<li data-href="[^"]*" class="([^"]*)"[^>]*itemtype="http://schema.org/Event">(.*?)</li>', page, re.S):
        classes, body = item
        url = re.search(r'href="([^"]+)"\s+itemprop="url"', body)
        start = re.search(r'itemprop="startDate"\s+datetime="(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})"', body)
        title = re.search(r'itemprop="name">(.*?)</h1>', body, re.S)
        if not (url and start and title):
            continue
        begin = re.search(r"Beginn\s*([0-9]{1,2}:[0-9]{2})", body)
        room = re.search(r'itemprop="location">(.*?)</div>', body, re.S)
        kind = next((UEBEL_KIND[c] for c in classes.split() if c in UEBEL_KIND), "")
        events.append(
            {
                "url": url.group(1),
                "title": clean(title.group(1)),
                "text": ", ".join(x for x in (kind, clean(room.group(1)) if room else "") if x),
                "starts_at": at(start.group(1), begin.group(1) if begin else start.group(2)),
                "venue": "Uebel & Gefährlich",
            }
        )
    return events


# ---------- Molotow: <div id='i<nr>' class='<room> <type>'> blocks ----------

MOLOTOW_EVENT = "https://molotowclub.com/programm/programm.php?nr={}"


def parse_molotow(page):
    events = []
    parts = re.split(r"<div id='i(\d+)' class = '([^']*)'", page)
    # parts = [before, nr, classes, body, nr, classes, body, ...]
    for nr, classes, body in zip(parts[1::3], parts[2::3], parts[3::3]):
        day = re.search(r"(\d{2}\.\d{2}\.\d{4}):", body)
        title = re.search(r"<div class='div_title'>(.*?)<span class='typ'", body, re.S) or re.search(
            r"<div class='div_title'>(.*?)</div>", body, re.S
        )
        if not (day and title):
            continue
        time = re.search(r"(?:Beginn|Start):\s*([0-9]{1,2}[:.][0-9]{2})", body) or re.search(
            r"Einlass:\s*([0-9]{1,2}[:.][0-9]{2})", body
        )
        info = re.search(r"<div class='div_info'>(.*?)<a ", body, re.S)
        room, _, kind = classes.strip().rpartition(" ")
        kind = f"{kind}, {room}" if room else kind  # "Top Ten Bar Konzert" -> "Konzert, Top Ten Bar"
        events.append(
            {
                "url": MOLOTOW_EVENT.format(nr),
                "title": clean(title.group(1).replace("<br />", " · ")),
                "text": "; ".join(x for x in (kind, clean(info.group(1)) if info else "") if x)[:1500],
                "starts_at": at(de_date(day.group(1)), time.group(1) if time else None),
                "venue": "Molotow",
            }
        )
    return events


# ---------- Knust: <div class="kn-event-thumb" data-genre data-date> cards on /programm/ ----------


def parse_knust(page):
    events, seen = [], set()
    for card in re.split(r'(?=<div class="kn-event-thumb)', page)[1:]:
        day = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', card)
        url = re.search(r'href="(https://knusthamburg\.de/event/[^"]+)"', card)
        name = re.search(r'kn-ethumb-name[^>]*aria-label="([^"]*)"', card) or re.search(
            r'kn-ethumb-name[^>]*>(.*?)</a>', card, re.S
        )
        if not (day and url and name) or url.group(1) in seen:
            continue
        seen.add(url.group(1))
        time = re.search(r'kn-ethumb-time[^>]*>\s*([0-9]{1,2}:[0-9]{2})', card)
        genre = re.search(r'data-genre="([^"]*)"', card)
        events.append(
            {
                "url": url.group(1),
                "title": clean(name.group(1)),
                "text": clean(genre.group(1)) if genre else "",
                "starts_at": at(day.group(1), time.group(1) if time else None),
                "venue": "Knust",
            }
        )
    return events


PARSERS = {
    "gruenspan": parse_gruenspan,
    "uebel": parse_uebel,
    "molotow": parse_molotow,
    "knust": parse_knust,
}
