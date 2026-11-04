"""Build a labeling page (interesting / not) from the live feed.

Usage: python eval/make_label_page.py <name>   ->  eval/<name>.html, answers download as <name>.json
"""

import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

FEED = "https://bot-iiozytiy2xwk0rd37aoj2p0c.201-34-144-213.sslip.io/"
HERE = Path(__file__).resolve().parent


def live_events():
    page = urllib.request.urlopen(FEED, timeout=30).read().decode()
    at = page.find('"generated_at"')
    data, _ = json.JSONDecoder().raw_decode(page[page.rfind("{", 0, at):].replace("<\\/", "</"))
    return [
        {"url": f["url"], "venue": f["reason"], "title": f["title"], "summary": f["summary"],
         "type": f.get("event_type"), "line": f["line"], "text": (f.get("text") or "")[:300]}
        for f in data["findings"]
    ]


def main(name):
    events = live_events()
    html = (HERE / "label-template.html").read_text()
    html = html.replace("/*EVENTS*/", json.dumps(events, ensure_ascii=False)).replace("/*KEY*/", name)
    html = html.replace("/*DATE*/", date.today().strftime("%d.%m.%Y"))
    out = HERE / f"{name}.html"
    out.write_text(html)
    print(out, len(events), "events")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "label-after")
