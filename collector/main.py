"""Collector: visits every active venue once, saves upcoming events, exits."""

import urllib.request
from datetime import datetime, timedelta

import db
from collector.dedup import AGGREGATORS, find_duplicate
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
    candidates = conn.execute(
        """SELECT m.id, m.venue, m.title, s.kind = ANY(%s)
           FROM materials m JOIN sources s ON s.id = m.source_id
           WHERE m.source_id <> %s AND m.url <> %s
             AND (m.starts_at AT TIME ZONE 'Europe/Berlin')::date = %s""",
        (list(AGGREGATORS), source_id, event["url"], event["starts_at"].date()),
    ).fetchall()
    duplicate = find_duplicate(event, candidates)
    if duplicate:
        duplicate_id, _, _, duplicate_from_aggregator = duplicate
        if from_aggregator or not duplicate_from_aggregator:
            return False  # the venue's own row is already there
        # the venue site wins over an aggregator: replace the aggregator's row
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
                continue
            new = sum(save(conn, source_id, run_id, e, kind in AGGREGATORS) for e in events)
            total_new += new
            db.progress_run(
                conn,
                SERVICE,
                run_id,
                total_new,
                f"{name}: событий в окне {len(events)}, новых {new}",
            )
        db.finish_run(
            conn, SERVICE, run_id, total_new, f"новых событий в базе: {total_new}"
        )
    except Exception as error:
        db.fail_run(conn, SERVICE, run_id, error)
        raise


if __name__ == "__main__":
    main()
