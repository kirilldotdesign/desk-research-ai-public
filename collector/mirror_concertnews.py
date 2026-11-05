"""SPEC-3 T18: Concert News mirror, runs in GitHub Actions (.github/workflows/concertnews.yml).

concert-news.de times out from the course server. GitHub fetches the calendar, our own parse_concertnews
turns it into events, and only the facts (date, title, venue, link) go to a JSON file.
The collector reads that file back with venues.parse_concertnews_json.

    python -m collector.mirror_concertnews concertnews.json
"""

import json
import sys
from pathlib import Path

from collector.main import fetch
from collector.venues import CONCERT_NEWS, parse_concertnews


def to_json(events):
    rows = [
        {"url": e["url"], "title": e["title"], "venue": e["venue"], "starts_at": e["starts_at"].isoformat()}
        for e in events
    ]
    # stable output: an unchanged calendar gives an identical file, so the Action makes no commit
    return json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(path="concertnews.json"):
    events = parse_concertnews(fetch(CONCERT_NEWS))
    if not events:
        # the page changed or came back empty: keep yesterday's file instead of an empty one
        sys.exit("Concert News: 0 events parsed")
    Path(path).write_text(to_json(events), encoding="utf-8")
    print(f"Concert News: {len(events)} events, {len({e['venue'] for e in events})} venues -> {path}")


if __name__ == "__main__":
    main(*sys.argv[1:])
