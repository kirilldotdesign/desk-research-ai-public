"""Worker: takes new materials from the database, asks the model, writes findings.

This is the only place in the system where a model is called.
"""

import json
import os
import time
import urllib.request

import db

SERVICE = "worker"
MODEL = os.environ.get("MODEL", "anthropic/claude-haiku-5.5")
PROMPT_VERSION = "v2-events"
POLL_SECONDS = 10
RETRY_SECONDS = 3600

EVENT_TYPES = ["Konzert", "Party", "Sonstiges"]
MAX_SUMMARY = 80


PROMPT = """Du hilfst bei einem Veranstaltungs-Digest für Clubs in Hamburg.
Veranstaltung:
Club: {venue}
Titel: {title}
Infos: {text}

Antworte nur mit JSON, ohne Erklärungen:
{{"event_type": eines von {types} — Konzert = Live-Band oder Künstler:in auf der Bühne,
                Party = DJs / Clubnacht / Rave, Sonstiges = Lesung, Slam, Markt, Talk usw.,
  "summary": "was das ist, eine kurze Phrase auf Deutsch, Genre oder Format, höchstens 60 Zeichen,
              ohne Titel, Datum und Club zu wiederholen (z. B. 'Deutschpunk', 'Techno-Rave bis morgens')"}}"""


def to_finding(answer):
    """Model answer -> (event_type, summary). Unknown type -> Sonstiges; empty summary -> error."""
    event_type = answer.get("event_type")
    if event_type not in EVENT_TYPES:
        event_type = "Sonstiges"
    summary = " ".join(str(answer.get("summary") or "").split())
    if not summary:
        raise ValueError(f"модель не дала summary: {answer}")
    if len(summary) > MAX_SUMMARY:
        summary = summary[: MAX_SUMMARY - 1].rstrip() + "…"
    return event_type, summary


def ask_model(venue, title, text):
    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT.format(
                    venue=venue or "",
                    title=title,
                    text=(text or "")[:2000],
                    types=", ".join(EVENT_TYPES),
                ),
            }
        ],
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        content = json.loads(resp.read())["choices"][0]["message"]["content"]
    content = (
        content.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    )
    return json.loads(content)


def process_new(conn):
    pending = conn.execute(
        "SELECT id, venue, title, text FROM materials WHERE status = 'new' ORDER BY id"
    ).fetchall()
    if not pending:
        return
    run_id = db.start_run(conn, SERVICE)
    found = 0
    for done, (material_id, venue, title, text) in enumerate(pending, 1):
        try:
            event_type, summary = to_finding(ask_model(venue, title, text))
        except Exception as error:
            conn.execute(
                "UPDATE materials SET status = 'failed' WHERE id = %s", (material_id,)
            )
            db.log(SERVICE, f"материал {material_id}: модель не ответила: {error}")
            continue
        # SPEC decision 1: every event becomes a finding, the type is only a label
        conn.execute(
            """INSERT INTO findings (material_id, entity, summary, event_type, model, prompt_version)
               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (material_id) DO NOTHING""",
            (material_id, venue, summary, event_type, MODEL, PROMPT_VERSION),
        )
        conn.execute("UPDATE materials SET status = 'done' WHERE id = %s", (material_id,))
        found += 1
        db.log(SERVICE, f"событие {material_id} ({venue}) -> {event_type}: {summary}")
        if done % 10 == 0:
            db.progress_run(
                conn, SERVICE, run_id, found, f"разобрано {done} из {len(pending)}"
            )
    db.finish_run(
        conn, SERVICE, run_id, found, f"разобрано {len(pending)}, находок {found}"
    )


def retry_failed(conn):
    retried = conn.execute(
        "UPDATE materials SET status = 'new' WHERE status = 'failed'"
    ).rowcount
    if retried:
        db.log(
            SERVICE,
            f"вернул в разбор {retried} материалов, на которых модель не ответила",
        )


def main():
    conn = db.connect()
    db.init_schema(conn)
    db.log(SERVICE, f"жду новые материалы в базе, модель {MODEL}")
    last_retry = float("-inf")
    while True:
        try:
            # materials the model failed on go back into the queue once an hour
            if time.monotonic() - last_retry >= RETRY_SECONDS:
                retry_failed(conn)
                last_retry = time.monotonic()
            process_new(conn)
        except Exception as error:
            db.log(SERVICE, f"упал: {error}")
            conn = db.connect()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
