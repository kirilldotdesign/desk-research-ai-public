"""Collector: visits every active venue once, saves upcoming events, exits."""

import urllib.request
from datetime import datetime, timedelta

import db
from collector.dedup import AGGREGATORS, canonical_venue, find_duplicates
from collector.venues import BERLIN, HIDDEN, PARSERS

SERVICE = "collector"
WINDOW_DAYS = 14  # SPEC decision 2
USER_AGENT = "Mozilla/5.0 (compatible; hamburg-clubnacht/0.1)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def upcoming(events, now=None):
    """Only events from today to WINDOW_DAYS ahead, without cancelled / sold out / postponed."""
    now = now or datetime.now(BERLIN)
    first = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last = first + timedelta(days=WINDOW_DAYS + 1)
    return [
        e
        for e in events
        if first <= e["starts_at"] < last and not HIDDEN.search(e["title"])
    ]


def save(conn, source_id, run_id, event, from_aggregator=False):
    event = dict(event, venue=canonical_venue(event["venue"]))
    candidates = conn.execute(
        """SELECT m.id, m.venue, m.title, s.kind = ANY(%s)
           FROM materials m JOIN sources s ON s.id = m.source_id
           WHERE m.source_id <> %s AND m.url <> %s
             AND (m.starts_at AT TIME ZONE 'Europe/Berlin')::date = %s""",
        (list(AGGREGATORS), source_id, event["url"], event["starts_at"].date()),
    ).fetchall()
    duplicates = find_duplicates(event, candidates)
    if duplicates:
        if from_aggregator or any(not from_agg for *_, from_agg in duplicates):
            return False  # the event is already there (a venue's own row, or another aggregator first)
        # the venue site wins over aggregators: replace every aggregator row of this event
        for duplicate_id, *_ in duplicates:
            conn.execute("DELETE FROM findings WHERE material_id = %s", (duplicate_id,))
            conn.execute("DELETE FROM materials WHERE id = %s", (duplicate_id,))
    row = conn.execute(
        """INSERT INTO materials (source_id, run_id, url, title, text, published_at, starts_at, venue)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (url) DO NOTHING RETURNING id""",
        (
            source_id,
            run_id,
            event["url"],
            event["title"],
            event["text"],
            event["starts_at"],
            event["starts_at"],
            event["venue"],
        ),
    ).fetchone()
    return row is not None


def main():
    conn = db.connect()
    db.init_schema(conn)
    run_id = db.start_run(conn, SERVICE)
    total_new = 0
    broken = []  # "Concert News: HTTP Error 403" — shown in the run note, /status and the feed
    try:
        sources = conn.execute(
            "SELECT id, name, kind, url FROM sources WHERE active"
        ).fetchall()
        for source_id, name, kind, url in sources:
            try:
                events = upcoming(PARSERS[kind](fetch(url)))
            except Exception as error:
                # one broken source does not stop the run
                db.log(SERVICE, f"источник «{name}» недоступен: {error}")
                broken.append(f"{name}: {str(error)[:80]}")
                continue
            if not events:  # the page came, but nothing was found: layout change or a block page
                broken.append(f"{name}: 0 событий")
            new = sum(save(conn, source_id, run_id, e, kind in AGGREGATORS) for e in events)
            total_new += new
            db.progress_run(
                conn,
                SERVICE,
                run_id,
                total_new,
                f"{name}: событий в окне {len(events)}, новых {new}",
            )
        note = f"новых событий в базе: {total_new}"
        if broken:
            note += "; недоступны: " + "; ".join(broken)
        db.finish_run(conn, SERVICE, run_id, total_new, note)
    except Exception as error:
        db.fail_run(conn, SERVICE, run_id, error)
        raise


if __name__ == "__main__":
    main()
