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


# ---------- ohschonhell.de (aggregator): JSON behind the calendar page ----------

OHSCHONHELL = "https://ohschonhell.de"


def parse_ohschonhell(page):
    data = json.loads(page)
    found = {}
    days = [day for month in data.get("months", []) for day in month.get("month_days", [])]
    for day in days + data.get("days", []):
        for e in day.get("events") or []:
            if not (e.get("name") and e.get("date") and e.get("event_post") and e.get("location_name")):
                continue
            found[e["event_id"]] = {
                "url": OHSCHONHELL + e["event_post"],
                "title": clean(e["name"]),
                "text": clean((e.get("lineup") or "").replace("<br />", " "))[:1500],
                "starts_at": at(e["date"], e.get("event_time") or None),
                "venue": clean(e["location_name"]),
            }
    return list(found.values())


# ---------- concert-news.de (aggregator): "05.11.2026 – Title – Venue" lines ----------

CONCERT_NEWS = "https://www.concert-news.de/konzertkalender/"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", clean(text).lower()).strip("-")[:80]


def parse_concertnews(page):
    """No time and no event page on this site: the link is the calendar with a unique anchor."""
    start = page.find('id="myFuture"')
    events, seen = [], set()
    for line in re.findall(r"<div>(\d{2}\.\d{2}\.\d{4}) – (.*?)</div>", page[start:] if start >= 0 else page, re.S):
        day, rest = line
        parts = [clean(x) for x in re.sub(r"<b>.*?</b>", "", rest, flags=re.S).split(" – ")]
        if len(parts) < 2:
            continue
        venue, title = parts[-1], " – ".join(parts[:-1])
        url = f"{CONCERT_NEWS}#{de_date(day)}-{slug(title)}-{slug(venue)}"
        if not title or not venue or url in seen:
            continue
        seen.add(url)
        events.append({"url": url, "title": title, "text": "", "starts_at": at(de_date(day)), "venue": venue})
    return events


# ---------- sperrstunde.org (aggregator, DIY / punk): event blocks, date in the event URL ----------

SPERRSTUNDE = "https://www.sperrstunde.org"
SPERRSTUNDE_MUSIC = {"Konzert", "Party"}  # the rest is talks, Küfa, workshops, demos


def parse_sperrstunde(page):
    events = []
    for block in re.split(r'<div class="event event-published">', page)[1:]:
        link = re.search(r'<h2>\s*<a title="[^"]*" href="(/events/(\d{4}-\d{2}-\d{2})[^"]*)">(.*?)</a>', block, re.S)
        venue = re.search(r'class="event-venue">\s*<a[^>]*>(.*?)</a>', block, re.S)
        categories = set(re.findall(r'category-label[^>]*>\s*([^<]+?)\s*<', block))
        if not (link and venue) or not categories & SPERRSTUNDE_MUSIC:
            continue
        time = re.search(r'event-time">\s*([0-9]{1,2}:[0-9]{2})', block)
        text = re.search(r'<div class="event-text">(.*?)<div class="event-links">', block, re.S)
        events.append(
            {
                "url": SPERRSTUNDE + link.group(1),
                "title": clean(link.group(3)),
                "text": "; ".join(x for x in (", ".join(sorted(categories)), clean(text.group(1)) if text else "") if x)[:1500],
                "starts_at": at(link.group(2), time.group(1) if time else None),
                "venue": clean(venue.group(1)),
            }
        )
    return events


# ---------- Golden Pudel: pudel.com/programm, no event pages (link = programme + anchor) ----------

PUDEL = "https://pudel.com/programm/"
MONTHS_DE = {m: i for i, m in enumerate(
    ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"], 1
)}


def de_long_date(text):
    """'5. November 2026' -> '2026-11-05'."""
    dom, month, year = re.match(r"(\d{1,2})\.\s*([A-Za-zä]+)\s+(\d{4})", text.strip()).groups()
    return f"{year}-{MONTHS_DE[month]:02d}-{int(dom):02d}"


def parse_pudel(page):
    events, seen = [], set()
    series = ""
    for chunk in re.split(r'(<h3 class="event-cat">.*?</h3>)', page, flags=re.S):
        head = re.match(r'<h3 class="event-cat">(.*?)</h3>', chunk, re.S)
        if head:
            series = clean(head.group(1))
            continue
        for block in re.split(r'<div class="vsel-content">', chunk)[1:]:
            meta = re.search(r'vsel-meta-date">(.*?)</p>\s*<b class="vsel-meta-title">(.*?)</b>', block, re.S)
            if not meta:
                continue
            when = clean(meta.group(1))
            title = clean(meta.group(2))
            time = re.search(r"(\d{1,2}:\d{2})", when)
            day = de_long_date(when)
            url = f"{PUDEL}#{day}-{slug(title)}"
            if url in seen:
                continue
            seen.add(url)
            links = re.findall(r'<a href="https?://(?:www\.)?([^"]+?)/?"', block)
            events.append(
                {
                    "url": url,
                    "title": title,
                    "text": "; ".join(x for x in (series, ", ".join(links)) if x)[:1500],
                    "starts_at": at(day, time.group(1) if time else None),
                    "venue": "Golden Pudel Club",
                }
            )
    return events


# ---------- Hafenklang: <article class='cp-event'>, event link /programm?cpnr=… ----------

HAFENKLANG = "https://www.hafenklang.com"


def parse_hafenklang(page):
    events, seen = [], set()
    for article in re.findall(r"<article class='cp-event.*?</article>", page, re.S):
        link = re.search(r"<h2 class='cp-title cp-title-desktop[^']*'><a href='([^']+)'>(.*?)</a></h2>", article, re.S)
        day = re.search(r"<p class='cp-date'>\w+ (\d{2}\.\d{2}\.)(\d{2})</p>", article)
        if not (link and day):
            continue
        url = HAFENKLANG + link.group(1)
        if url in seen:
            continue
        seen.add(url)
        sub = re.search(r"<span class='cp-sub-title'>(.*?)</span>", link.group(2), re.S)
        title = clean(re.sub(r"<span class='cp-sub-title'>.*?</span>", "", link.group(2), flags=re.S))
        room = re.search(r"<span class='cp-room[^']*'>(.*?)</span>", article)
        kind = re.search(r"<p class='cp-type'><span>(.*?)</span>", article)
        time = re.search(r"Beginn:\s*([0-9]{1,2}:[0-9]{2})", article) or re.search(r"Einlass:\s*([0-9]{1,2}:[0-9]{2})", article)
        events.append(
            {
                "url": url,
                "title": title,
                "text": "; ".join(clean(x.group(1)) for x in (kind, room, sub) if x)[:1500],
                "starts_at": at(de_date(day.group(1) + "20" + day.group(2)), time.group(1) if time else None),
                "venue": "Hafenklang",
            }
        )
    return events


# ---------- Südpol: suedpolevent_item blocks, link = page anchor #event_<id> ----------

SUEDPOL = "https://www.suedpol.org/"


def parse_suedpol(page):
    events = []
    for item_id, body in re.findall(
        r'<div id="event_(\d+)" name="event_\d+" class="suedpolevent_item(.*?)(?=<div id="event_\d+" name=|$)', page, re.S
    ):
        rows = [clean(x) for x in re.findall(r'<li class="list_item">(.*?)</li>', body, re.S)]
        name = re.search(r'<div class="event_name">(.*?)</div>', body, re.S)
        dates = re.match(r"(\d{2})\.(\d{2})\.(?:\s*-\s*\d{2}\.(\d{2})\.)?\s*(\d{4})?", rows[0]) if rows else None
        if not (name and dates):
            continue
        dom, month, end_month, year = dates.groups()
        year = int(year or 0)
        if end_month and int(month) > int(end_month):
            year -= 1  # 30.12. - 01.01.2027
        time = re.match(r"(\d{1,2}:\d{2})", rows[2]) if len(rows) > 2 else None
        text = re.search(r'<div class="event_description">(.*?)</div>', body, re.S)
        events.append(
            {
                "url": f"{SUEDPOL}#event_{item_id}",
                "title": clean(name.group(1)),
                "text": clean(text.group(1)).replace("RUNNING ORDER", "").strip(" _")[:1500] if text else "",
                "starts_at": at(f"{year}-{month}-{dom}", time.group(1) if time else None),
                "venue": "Südpol",
            }
        )
    return events


# ---------- Rote Flora: MEC list, date in ?occurrence=; only music nights (also: cinema, talks, bike workshop) ----------

MUSIC_WORDS = re.compile(r"konzert|party|rave|punk|festival|\bdj|live|disco|techno|noise|hardcore|metal|soli-?show|tanz", re.I)


def parse_roteflora(page):
    events = []
    for article in re.findall(r'<article class="mec-event-article.*?</article>', page, re.S):
        link = re.search(r'class="mec-event-title"><a[^>]*href="([^"]+\?occurrence=(\d{4}-\d{2}-\d{2}))"[^>]*>(.*?)</a>', article, re.S)
        if not link:
            continue
        description = re.search(r'mec-event-description">(.*?)</div>', article, re.S)
        title, text = clean(link.group(3)), clean(description.group(1)) if description else ""
        if not MUSIC_WORDS.search(f"{title} {text}"):
            continue
        time = re.search(r'mec-start-time">\s*([0-9]{1,2}:[0-9]{2})', article)
        events.append(
            {
                "url": link.group(1),
                "title": title,
                "text": text[:1500],
                "starts_at": at(link.group(2), time.group(1) if time else None),
                "venue": "Rote Flora",
            }
        )
    return events


# ---------- MS Stubnitz: /events/ list with genre "theme"; no start time in the list ----------

STUBNITZ = "https://www.stubnitz.com"


def parse_stubnitz(page):
    events, seen = [], set()
    for item in re.findall(r'<li class="(?:confirmed|[^"]*)">\s*<a href="(/events/[^"]+\.html)">(.*?)</li>', page, re.S):
        path, body = item
        day = re.search(r"(\d{2}\.\d{2}\.\d{4})", body)
        name = re.search(r'<h3 class="event-name[^"]*">(.*?)</h3>', body, re.S)
        if not (day and name) or path in seen:
            continue
        seen.add(path)
        kind = re.search(r'<p class="event-type[^"]*">(.*?)</p>', body, re.S)
        sub = re.search(r"<h4>(.*?)</h4>", body, re.S)
        theme = re.search(r'<p class="theme">(.*?)</p>', body, re.S)
        events.append(
            {
                "url": STUBNITZ + path,
                "title": clean(name.group(1)),
                "text": "; ".join(x for x in (clean(m.group(1)) for m in (kind, sub, theme) if m) if x)[:1500],
                "starts_at": at(de_date(day.group(1))),
                "venue": "MS Stubnitz",
            }
        )
    return events


# ---------- Elbphilharmonie / Laeiszhalle: /de/programm/ first page (≈ next 1–2 days) ----------

ELBPHILHARMONIE = "https://www.elbphilharmonie.de"


def parse_elbphilharmonie(page):
    events = []
    for item in re.findall(r'<li id="event_id_[^"]*"[^>]*class="event-item".*?(?=<li id="event_id_|</ul>)', page, re.S):
        start = re.search(r'<time datetime="(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})', item)
        link = re.search(r'<p class="event-title[^"]*"><a href="([^"]+)">(.*?)</a>', item, re.S)
        if not (start and link):
            continue
        place = re.search(r'place-cell"><span class="caption uppercase"><strong>(.*?)</strong>(.*?)</span>', item, re.S)
        subtitle = re.search(r'<p class="event-subtitle">(.*?)</p>', item, re.S)
        events.append(
            {
                "url": ELBPHILHARMONIE + link.group(1),
                "title": clean(link.group(2)),
                "text": "; ".join(x for x in (clean(subtitle.group(1)) if subtitle else "", clean(place.group(2)) if place else "") if x),
                "starts_at": at(start.group(1), start.group(2)),
                "venue": clean(place.group(1)) if place else "Elbphilharmonie",
            }
        )
    return events


PARSERS = {
    "elbphilharmonie": parse_elbphilharmonie,
    "stubnitz": parse_stubnitz,
    "roteflora": parse_roteflora,
    "suedpol": parse_suedpol,
    "hafenklang": parse_hafenklang,
    "pudel": parse_pudel,
    "sperrstunde": parse_sperrstunde,
    "concertnews": parse_concertnews,
    "ohschonhell": parse_ohschonhell,
    "gruenspan": parse_gruenspan,
    "uebel": parse_uebel,
    "molotow": parse_molotow,
    "knust": parse_knust,
}
