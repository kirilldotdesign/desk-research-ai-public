"""T6: one event from two sources (venue site + aggregator) -> one row, the venue link wins.

Same event = same venue + same day + similar title (SPEC decision 10).
"""

import os
import re
import unicodedata
from difflib import SequenceMatcher

AGGREGATORS = {"ohschonhell", "clubkombinat", "concertnews", "sperrstunde", "rausgegangen", "krach", "vamh"}  # source kinds that list other venues' events


UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def norm(text):
    text = (text or "").translate(UMLAUTS)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


# SPEC 3 T9: one venue, one name — sources spell venues differently (norm(variant) -> canonical name)
VENUE_ALIASES = {
    "gruenspan": "Grünspan",
    "uebel und gefaehrlich": "Uebel & Gefährlich",
    "uebel gefaehrlich": "Uebel & Gefährlich",
    "uebel gefaehrlich turmzimmer": "Uebel & Gefährlich",
    "hafenklang goldener salon": "Hafenklang",
    "goldener salon": "Hafenklang",
    "golden pudel": "Golden Pudel Club",
    "pudel": "Golden Pudel Club",
    "haus73": "Haus 73",
    "jazz cafe mojo club": "Mojo Club",
    "mojo jazz cafe": "Mojo Club",
    "stellwerk hamburg": "Stellwerk",
    "fabrik im gaengeviertel": "Gängeviertel",
    "fabrique im gaengeviertel": "Gängeviertel",
    "suedpol hamburg": "Südpol",
    "grosse freiheit": "Grosse Freiheit 36",
    "ms stubnitz hamburg": "MS Stubnitz",
    "kent club hamburg": "KENT Club",
    "frau hedis tanzkaffee": "Frau Hedi",
    "markthalle hamburg": "Markthalle",
    "fabrik hamburg": "Fabrik",
}


def canonical_venue(name):
    name = " ".join((name or "").replace("[ ]", "").split())
    return VENUE_ALIASES.get(norm(name), name)


def same_venue(a, b):
    a, b = norm(canonical_venue(a)), norm(canonical_venue(b))
    return bool(a and b) and a == b


def same_title(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    short, long = sorted((a, b), key=len)
    # "FAT DOG" vs "FAT DOG Support: SILVERWINGKILLER" is the same night
    if long.startswith(short) or SequenceMatcher(None, a, b).ratio() >= 0.8:
        return True
    # "Radwan Ghazi Moumneh (Jerusalem In My Heart) …" vs "Radwan Ghazi Moumneh & …": same long beginning
    common = len(os.path.commonprefix([a, b]))
    if common >= 15:
        return True
    # "Holy Mother - The Holy Storm Tour" vs "Holy Mother + Wicked Maraya – …": same first two words
    # (only ever compared within one venue and one day, across different sources)
    wa, wb = a.split(), b.split()
    return len(wa) >= 2 and len(wb) >= 2 and wa[:2] == wb[:2] and len(" ".join(wa[:2])) >= 8


def find_duplicates(event, candidates):
    """candidates: [(id, venue, title, from_aggregator)] already saved for the same day.
    Returns every matching candidate (one event can come from several aggregators)."""
    return [
        c for c in candidates if same_venue(event["venue"], c[1]) and same_title(event["title"], c[2])
    ]


def find_duplicate(event, candidates):
    matches = find_duplicates(event, candidates)
    return matches[0] if matches else None
