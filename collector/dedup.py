"""T6: one event from two sources (venue site + aggregator) -> one row, the venue link wins.

Same event = same venue + same day + similar title (SPEC decision 10).
"""

import re
import unicodedata
from difflib import SequenceMatcher

AGGREGATORS = {"ohschonhell", "clubkombinat", "concertnews", "sperrstunde", "rausgegangen"}  # source kinds that list other venues' events


def norm(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def same_venue(a, b):
    a, b = norm(a), norm(b)
    return bool(a and b) and (a == b or a in b or b in a)


def same_title(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    short, long = sorted((a, b), key=len)
    # "FAT DOG" vs "FAT DOG Support: SILVERWINGKILLER" is the same night
    return long.startswith(short) or SequenceMatcher(None, a, b).ratio() >= 0.8


def find_duplicate(event, candidates):
    """candidates: [(id, venue, title, from_aggregator)] already saved for the same day.
    Returns the matching candidate or None."""
    for candidate in candidates:
        _, venue, title, _ = candidate
        if same_venue(event["venue"], venue) and same_title(event["title"], title):
            return candidate
    return None
