"""Bot: Telegram bot and a Mini App with the findings.

- remembers everyone who pressed Start (table subscribers);
- after each collection is sorted by the worker, sends one summary to subscribers and marks findings.sent_at;
- answers /start and /status;
- serves the Mini App page on PORT, the bot opens it inside Telegram.
"""

import html
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import db
from bot.events import BERLIN, digest_days, digest_title, event_line, today_in_hamburg, window

SERVICE = "bot"
HERE = Path(__file__).resolve().parent
SEND_EVERY_SECONDS = 60
LATEST = 5  # events listed after /start, the rest are in the feed
MAX_MESSAGE = 3800  # Telegram allows 4096 characters
# a collection counts for the digest only if it finished after this bot started:
# right after a deploy the morning run of the old code must not trigger an empty digest
STARTED_AT = datetime.now(timezone.utc)

COMMANDS = [
    {"command": "start", "description": "подписаться на находки"},
    {"command": "status", "description": "что было в последних прогонах"},
]


def setting(name):
    return os.environ.get(name, "").strip()


def page_url():
    """Address of the Mini App: set by hand or taken from the platform (Railway, Coolify)."""
    url = (
        setting("MINI_APP_URL")
        or setting("RAILWAY_PUBLIC_DOMAIN")
        or setting("COOLIFY_URL")
    )
    if not url:
        return ""
    url = url.split(",")[0].strip()  # Coolify lists several domains separated by commas
    if not url.startswith("http"):
        url = f"https://{url}"
    return url.rstrip("/") + "/"


# ---------- Telegram ----------


def api(method, payload=None, timeout=20):
    base = setting("TELEGRAM_API") or "https://api.telegram.org"
    request = urllib.request.Request(
        f"{base}/bot{setting('TELEGRAM_TOKEN')}/{method}",
        data=json.dumps(payload or {}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())["result"]


def say(chat_id, text, button=True):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if button and page_url():
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "Открыть ленту", "web_app": {"url": page_url()}}]
            ]
        }
    api("sendMessage", payload)


EVENT_ROWS = (
    "SELECT m.starts_at, coalesce(m.venue, f.entity), m.title, f.summary, m.url FROM findings f"
    " JOIN materials m ON m.id = f.material_id"
)


def finding_lines(rows):
    return [
        f'• <a href="{html.escape(url)}">{html.escape(event_line(starts_at, venue, title, summary))}</a>'
        for starts_at, venue, title, summary, url in rows
    ]


def digest_text(days, rows):
    """SPEC decision 9: one message with the events of the given days, cut to fit Telegram."""
    title = f"<b>{html.escape(digest_title(days))}</b>"
    if not rows:
        return title + "\n\nНичего не нашёл. Вся афиша на 14 дней — в ленте."
    lines, text = finding_lines(rows), title + "\n"
    for shown, line in enumerate(lines):
        rest = len(lines) - shown
        if len(text) + len(line) + 60 > MAX_MESSAGE:
            return text + f"\n… и ещё {rest} в ленте."
        text += "\n" + line
    return text


def setup(conn):
    """Menu commands, the permanent page button, and a starting point for sending."""
    api("setMyCommands", {"commands": COMMANDS})
    if page_url():
        api(
            "setChatMenuButton",
            {
                "menu_button": {
                    "type": "web_app",
                    "text": "Лента",
                    "web_app": {"url": page_url()},
                }
            },
        )
    # before the first subscriber, old findings count as sent: the bot pushes only what comes later
    if not conn.execute("SELECT 1 FROM subscribers LIMIT 1").fetchone():
        marked = conn.execute(
            "UPDATE findings SET sent_at = now() WHERE sent_at IS NULL"
        ).rowcount
        if marked:
            db.log(
                SERVICE,
                f"подписчиков нет, {marked} старых находок лежат в ленте, рассылать их не буду",
            )
    me = api("getMe")
    db.log(SERVICE, f"@{me['username']} на связи, лента {page_url() or 'без адреса'}")


def send_new(conn, now=None, started_at=None):
    """Morning digest (SPEC decision 9): once a day, after today's collection is sorted by the worker."""
    today = today_in_hamburg(now)
    already = conn.execute(
        "SELECT 1 FROM runs WHERE service = 'bot' AND status = 'finished' AND note LIKE %s",
        (f"сводка за {today:%Y-%m-%d}%",),
    ).fetchone()
    if already:
        return
    collected_today = conn.execute(
        "SELECT 1 FROM runs WHERE service = 'collector' AND status = 'finished'"
        " AND (finished_at AT TIME ZONE 'Europe/Berlin')::date = %s AND finished_at > %s",
        (today, started_at or STARTED_AT),
    ).fetchone()
    busy = conn.execute(
        "SELECT EXISTS (SELECT 1 FROM materials WHERE status = 'new')"
        " OR EXISTS (SELECT 1 FROM runs WHERE service = 'collector' AND status IN ('started', 'running')"
        "            AND started_at > now() - interval '30 minutes')"
    ).fetchone()[0]
    subscribers = [row[0] for row in conn.execute("SELECT chat_id FROM subscribers")]
    if not collected_today or busy or not subscribers:
        return
    days = digest_days(today)
    rows = conn.execute(
        EVENT_ROWS + " WHERE (m.starts_at AT TIME ZONE 'Europe/Berlin')::date = ANY(%s)"
        " AND m.starts_at >= now() - interval '6 hours' ORDER BY m.starts_at, m.venue",
        (days,),
    ).fetchall()
    text = digest_text(days, rows)
    run_id = db.start_run(conn, SERVICE)
    delivered = 0
    for chat_id in subscribers:
        try:
            say(chat_id, text)
            delivered += 1
        except urllib.error.HTTPError as error:
            if error.code == 403:  # the person blocked the bot
                conn.execute("DELETE FROM subscribers WHERE chat_id = %s", (chat_id,))
            db.log(SERVICE, f"чат {chat_id}: не доставлено, ответ {error.code}")
    conn.execute("UPDATE findings SET sent_at = now() WHERE sent_at IS NULL")
    db.finish_run(
        conn, SERVICE, run_id, len(rows),
        f"сводка за {today:%Y-%m-%d}: {len(rows)} событий, получили {delivered} из {len(subscribers)}",
    )


def status_text(conn):
    lines = []
    for service, name in (
        ("collector", "Сбор"),
        ("worker", "Разбор"),
        ("bot", "Рассылка"),
    ):
        run = conn.execute(
            "SELECT started_at, status, note FROM runs WHERE service = %s ORDER BY id DESC LIMIT 1",
            (service,),
        ).fetchone()
        if run:
            state = {"finished": "завершен", "failed": "упал"}.get(run[1], "идет")
            lines.append(
                f"{name}: {run[0].astimezone(timezone.utc):%d.%m %H:%M} UTC, {state}. {html.escape(run[2] or '')}"
            )
        else:
            lines.append(f"{name}: еще не было")
    findings, subscribers = conn.execute(
        "SELECT (SELECT count(*) FROM findings), (SELECT count(*) FROM subscribers)"
    ).fetchone()
    lines.append(f"\nВсего находок {findings}, подписчиков {subscribers}.")
    return "\n".join(lines)


def handle(conn, message):
    chat = message["chat"]
    if chat.get("type") != "private":
        return
    words = (message.get("text") or "").split()
    command = words[0].split("@")[0] if words else ""
    if command == "/start":
        name = chat.get("username") or chat.get("first_name") or ""
        conn.execute(
            "INSERT INTO subscribers (chat_id, name) VALUES (%s, %s) ON CONFLICT (chat_id) DO NOTHING",
            (chat["id"], name),
        )
        latest = conn.execute(
            EVENT_ROWS + " WHERE m.starts_at >= now() ORDER BY m.starts_at LIMIT %s", (LATEST,)
        ).fetchall()
        text = (
            "Готово, вы подписаны. Каждое утро пришлю афишу клубов Гамбурга: в будни — что сегодня,"
            " в пятницу — все выходные, в субботу и воскресенье — этот день."
        )
        if latest:
            text += "\n\nБлижайшее:\n" + "\n".join(finding_lines(latest))
        text += "\n\nВся афиша на 14 дней в ленте: кнопка ниже или «Лента» рядом с полем ввода. /status покажет, как работают блоки."
        say(chat["id"], text)
        db.log(SERVICE, f"новый подписчик {name or chat['id']}")
    elif command == "/status":
        say(chat["id"], status_text(conn))
    else:
        say(chat["id"], "Я понимаю /start и /status. Афиша в ленте:")


def poll_forever():
    """Long polling: asks Telegram for new messages and answers them."""
    offset = None
    while True:
        try:
            updates = api(
                "getUpdates",
                {"timeout": 30, "offset": offset, "allowed_updates": ["message"]},
                timeout=40,
            )
            if updates:
                with db.connect() as conn:
                    for update in updates:
                        offset = update["update_id"] + 1
                        if "message" in update:
                            handle(conn, update["message"])
        except urllib.error.HTTPError as error:
            if error.code == 409:
                # Telegram gives updates to one program at a time
                db.log(SERVICE, "409: этот токен уже слушает другая программа, бот ждет, пока она остановится")
            else:
                db.log(SERVICE, f"ошибка связи с Telegram: ответ {error.code}")
            time.sleep(5)
        except Exception as error:
            db.log(SERVICE, f"ошибка связи с Telegram: {error}")
            time.sleep(5)


def send_forever():
    while True:
        try:
            with db.connect() as conn:
                send_new(conn)
        except Exception as error:
            db.log(SERVICE, f"рассылка не прошла: {error}")
        time.sleep(SEND_EVERY_SECONDS)


# ---------- Mini App page ----------


def iso(moment):
    return (
        moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if moment
        else None
    )


def page_data(conn):
    fields = (
        "id",
        "material_id",
        "summary",
        "reason",
        "title",
        "url",
        "date",
        "run_id",
        "source_id",
        "source",
        "source_url",
        "text",
        "sent_at",
        "model",
        "event_type",
    )
    first, last = window()
    findings = []
    # SPEC 1: only upcoming events in the 14-day window, the soonest first
    for row in conn.execute(
        "SELECT f.id, m.id, f.summary, coalesce(m.venue, f.entity), m.title, m.url, m.starts_at, m.run_id,"
        " s.id, s.name, s.url, left(m.text, 600), f.sent_at, f.model, f.event_type"
        " FROM findings f JOIN materials m ON m.id = f.material_id JOIN sources s ON s.id = m.source_id"
        " WHERE m.starts_at >= %s AND m.starts_at < %s"
        " ORDER BY m.starts_at, m.venue LIMIT 500",
        (first, last),
    ):
        finding = dict(zip(fields, row))
        finding["line"] = event_line(finding["date"], finding["reason"], finding["title"], finding["summary"])
        finding["date"], finding["sent_at"] = (
            iso(finding["date"]),
            iso(finding["sent_at"]),
        )
        findings.append(finding)

    run = conn.execute(
        "SELECT id, finished_at, status, items FROM runs WHERE service = 'collector' AND status <> 'started'"
        " ORDER BY id DESC LIMIT 1"
    ).fetchone()
    run_info, sources = None, []
    if run:
        statuses = dict(
            conn.execute(
                "SELECT status, count(*) FROM materials WHERE run_id = %s GROUP BY status",
                (run[0],),
            ).fetchall()
        )
        added = sum(statuses.values())
        kept = conn.execute(
            "SELECT count(*) FROM findings f JOIN materials m ON m.id = f.material_id WHERE m.run_id = %s",
            (run[0],),
        ).fetchone()[0]
        sent = conn.execute(
            "SELECT count(*) FROM findings f JOIN materials m ON m.id = f.material_id"
            " WHERE m.run_id = %s AND f.sent_at IS NOT NULL",
            (run[0],),
        ).fetchone()[0]
        run_info = {
            "id": run[0],
            "finished_at": iso(run[1]),
            "status": run[2],
            "added": added,
            "processed": statuses.get("done", 0)
            + statuses.get("skipped", 0)
            + statuses.get("failed", 0),
            "kept": kept,
            "skipped": statuses.get("skipped", 0),
            "failed": statuses.get("failed", 0),
            "waiting": statuses.get("new", 0),
            "sent": sent,
        }
        sources = [
            {"name": name, "new": new}
            for name, new in conn.execute(
                "SELECT s.name, count(m.id) FROM sources s"
                " LEFT JOIN materials m ON m.source_id = s.id AND m.run_id = %s WHERE s.active GROUP BY s.id ORDER BY s.id",
                (run[0],),
            )
        ]
    totals = dict(
        zip(
            ("sources", "materials", "findings", "runs", "subscribers"),
            conn.execute(
                "SELECT (SELECT count(*) FROM sources WHERE active), (SELECT count(*) FROM materials),"
                " (SELECT count(*) FROM findings), (SELECT count(*) FROM runs), (SELECT count(*) FROM subscribers)"
            ).fetchone(),
        )
    )
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "totals": totals,
        "run": run_info,
        "sources": sources,
        "findings": findings,
    }


def render_page(conn):
    page = (
        (HERE / "template.html")
        .read_text(encoding="utf-8")
        .replace("/*BRAND*/", (HERE / "brand.css").read_text(encoding="utf-8"))
    )
    payload = json.dumps(page_data(conn), ensure_ascii=False).replace("</", "<\\/")
    return page.replace("/*DATA*/null/*END*/", payload)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            with db.connect() as conn:
                if path == "/health":
                    conn.execute("SELECT 1")
                    body, status, kind = b"ok", 200, "text/plain"
                elif path == "/":
                    body, status, kind = (
                        render_page(conn).encode("utf-8"),
                        200,
                        "text/html; charset=utf-8",
                    )
                else:
                    body, status, kind = b"not found", 404, "text/plain"
        except Exception as error:
            db.log(SERVICE, f"страница не собралась: {error}")
            body, status, kind = b"database unavailable", 503, "text/plain"
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    with db.connect() as conn:
        db.init_schema(conn)
        if setting("TELEGRAM_TOKEN"):
            try:
                setup(conn)
            except Exception as error:
                db.log(SERVICE, f"не настроил бота: {error}")
    if setting("TELEGRAM_TOKEN"):
        threading.Thread(target=poll_forever, daemon=True).start()
        threading.Thread(target=send_forever, daemon=True).start()
    else:
        db.log(
            SERVICE,
            "переменная TELEGRAM_TOKEN пустая: бот молчит, работает только лента",
        )
    port = int(os.environ.get("PORT", "8080"))
    db.log(SERVICE, f"лента открыта на порту {port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
