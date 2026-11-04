-- Desk Research: five tables.
-- sources     -> where we collect from
-- materials   -> what the collector brought (one row per link)
-- findings    -> what the worker extracted with the model
-- runs        -> every run of every block, with status
-- subscribers -> who pressed Start in the Telegram bot

CREATE TABLE IF NOT EXISTS sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    kind        TEXT NOT NULL,            -- parser name in collector/
    url         TEXT NOT NULL,
    active      BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS runs (
    id           SERIAL PRIMARY KEY,
    service      TEXT NOT NULL,           -- collector | worker | bot
    status       TEXT NOT NULL,           -- started | running | finished | failed
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    items        INTEGER NOT NULL DEFAULT 0,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS materials (
    id            SERIAL PRIMARY KEY,
    source_id     INTEGER NOT NULL REFERENCES sources(id),
    run_id        INTEGER REFERENCES runs(id),
    url           TEXT NOT NULL UNIQUE,
    title         TEXT NOT NULL,
    text          TEXT,
    published_at  TIMESTAMPTZ,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    status        TEXT NOT NULL DEFAULT 'new'   -- new | done | skipped | failed
);

CREATE TABLE IF NOT EXISTS findings (
    id              SERIAL PRIMARY KEY,
    material_id     INTEGER NOT NULL UNIQUE REFERENCES materials(id),
    entity          TEXT,                 -- company the material is about
    summary         TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- the bot marks a finding when it has been sent to subscribers
ALTER TABLE findings ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS subscribers (
    chat_id     BIGINT PRIMARY KEY,
    name        TEXT,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- SPEC 1 (T1): events instead of AI news
ALTER TABLE materials ADD COLUMN IF NOT EXISTS starts_at TIMESTAMPTZ;  -- event start, Europe/Berlin
ALTER TABLE materials ADD COLUMN IF NOT EXISTS venue TEXT;            -- club / location name
ALTER TABLE findings  ADD COLUMN IF NOT EXISTS event_type TEXT;       -- Konzert | Party | Sonstiges

-- remove the AI template: findings -> materials -> sources (idempotent, by source name)
DELETE FROM findings WHERE material_id IN (
    SELECT m.id FROM materials m JOIN sources s ON s.id = m.source_id
    WHERE s.name IN ('Hacker News', 'Hacker News: Anthropic', 'Hacker News: OpenAI', 'arXiv cs.AI', 'Хабр: ИИ'));
DELETE FROM materials WHERE source_id IN (
    SELECT id FROM sources
    WHERE name IN ('Hacker News', 'Hacker News: Anthropic', 'Hacker News: OpenAI', 'arXiv cs.AI', 'Хабр: ИИ'));
DELETE FROM sources
    WHERE name IN ('Hacker News', 'Hacker News: Anthropic', 'Hacker News: OpenAI', 'arXiv cs.AI', 'Хабр: ИИ');

-- kind = name of the parser in collector/
INSERT INTO sources (name, kind, url) VALUES
    ('Grünspan',           'gruenspan', 'https://www.gruenspan.de/'),
    ('Uebel & Gefährlich', 'uebel',     'https://www.uebelundgefaehrlich.com/'),
    ('Molotow',            'molotow',   'https://molotowclub.com/programm/programm.php'),
    ('Knust',              'knust',     'https://knusthamburg.de/programm/')
ON CONFLICT (name) DO NOTHING;
-- T5: Knust dates are on the programme page, not in the API
UPDATE sources SET url = 'https://knusthamburg.de/programm/' WHERE name = 'Knust';

-- SPEC 3: the whole Hamburg club scene (aggregators lose to a venue's own site on duplicates)
INSERT INTO sources (name, kind, url) VALUES
    ('oh schon hell', 'ohschonhell', 'https://ohschonhell.de/ajax/data_cache_db.php?load=initial&osh_page=hamburg'),
    ('Concert News',  'concertnews', 'https://www.concert-news.de/konzertkalender/'),
    ('sperrstunde',   'sperrstunde', 'https://www.sperrstunde.org/')
ON CONFLICT (name) DO NOTHING;
