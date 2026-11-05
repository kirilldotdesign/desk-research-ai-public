# SPEC 3 — вся клубная сцена Гамбурга

Статус: **v1, утверждена** (04.11.2026). Исполнение: ночь 04.→05.11 через `/goal`.
Порядок спек изменён (Kirill, 04.11): сначала SPEC 3 (источники), потом SPEC 2 (фильтр по вкусу).

## Для кого и зачем
Для Kirill. Ручная разметка 04.11 показала: в афише четырёх клубов SPEC 1 интересно **1 событие из 56 (2%)**.
Его музыка (disco-диггинг, Afro / Arabic / Latin, традиционная, нойз и грайнд, DJ-вечеринки) идёт на других
площадках. Цель: собрать афишу всего города, чтобы фильтру вкуса (SPEC 2) было из чего выбирать.

## Решения (Kirill, 04.11)
1. Агрегаторы **и** площадки без страниц событий напрямую (Hafenklang, Südpol). У таких ссылка ведёт на
   билет, если он есть, иначе на программу площадки.
2. Instagram — **в бэклог** (способ готов: Apify, ~$3–4 в месяц). Только для площадок, которых нет ни в одном
   источнике ниже.
3. **Golden Pudel напрямую:** в ohschonhell все 20 событий Pudel есть, но у 4 из 20 неверное время
   (агрегатор ставит 22:00 по умолчанию; TRIPNO на самом деле в 19:00).
4. rausgegangen.de — по правилу 45 минут (простой запрос даёт 403). Resident Advisor — нет (условия сайта).

## Источники
Агрегаторы (`kind` в `collector/dedup.AGGREGATORS` — проигрывают сайту клуба при дубле):

| Источник | Что покрывает | Как читать | Зона |
|---|---|---|---|
| ohschonhell.de | электроника и DJ: 38 площадок, 120 событий на 2 месяца (Pudel, Locke, Fundbureau, Südpol, Gängeviertel, Edelfettwerk, Frau Holle …) | JSON `ajax/data_cache_db.php?load=initial&osh_page=hamburg`; ссылка `/date/…`; жанры в тексте лайнапа | 🟢 |
| concert-news.de/konzertkalender | почти все концерты: Hafenklang, MS Stubnitz, Mojo Jazz Café, Logo, Bahnhof Pauli, Astra Stube, Bambi Galore … | HTML-список | 🟢 |
| sperrstunde.org | DIY / панк / политика: Buttclub, Rote Flora, Gängeviertel … | HTML, страницы `/events/…` | 🟢 |

Площадки напрямую:

| Площадка | Почему | Зона |
|---|---|---|
| Golden Pudel | точное время (решение 3); `pudel.com/programm` — HTML | 🟢 |
| Hafenklang | экстрим (trapped in purgatory), DJ; ссылка на билет / программу | 🟢 |
| Südpol | техно, рейвы; ссылка на программу | 🟢 |
| Rote Flora | панк, DIY-рейвы; `rote-flora.de/programm` | 🟢 |
| MS Stubnitz | экспериментальное, с жанрами в анонсе | 🟢 |

Кандидаты по **правилу 45 минут** (≥ 1 событие с датой, временем и ссылкой — иначе бэклог с причиной):
Clubplan Clubkombinat (app.clubkombinat.de), Mojo Club (вкл. Jazz Café — world / desert blues),
Elbphilharmonie (world / традиционная), rausgegangen.de.

## KPI
| KPI | Тип | Порог | До (04.11) | После |
|---|---|---|---|---|
| Площадок в афише за 14 дней | полезно ли | ≥ 40 | 4 | **36** ✗ (с Concert News локально 69 — с сервера недоступен) |
| Интересных Kirill событий за 14 дней (ручная разметка новой афиши) | полезно ли | ≥ 10 | 1 | ждёт разметки `eval/label-after.html` |
| Время совпадает с сайтом клуба (выборка Pudel + 2 площадки) | полезно ли | ≥ 95% | — (ohschonhell сам по себе: 80% у Pudel) | **100%** (Pudel 11/11, Hafenklang 21/21, Südpol 2/2 — строки с сайта клуба) ✅ |
| Дубли между источниками | полезно ли | 0 | — | **0** ✅ (1 повтор внутри ohschonhell: «Auf Socken», Gängeviertel 08.11) |
| Ссылка ведёт на страницу события (кроме Hafenklang / Südpol) | полезно ли | ≥ 95% | 100% (4 клуба) | **92%** (148/161) ✗ — Pudel (11) без страниц событий, ссылка = программа + якорь |
| Каждый подключённый источник дал ≥ 1 событие за прогон | работает ли | все | 4 из 4 | **10 из 11** ✗ — Concert News: timeout с сервера |
| Разбор моделью новой афиши (первый прогон) | работает ли | без сбоев, ≤ $0.20 | — | **105/105, 0 сбоев, ключ всего $0.043** ✅ |

Замер «после»: 04.11.2026, ~21:30, живая лента после деплоя `08abf12`.

## Что меняем и где
- `collector/venues.py`: парсеры новых источников; агрегаторы отдают своё название площадки (`venue`).
- `collector/dedup.py`: **словарь названий площадок** («Uebel und Gefährlich» = «Uebel & Gefährlich»,
  «Gruenspan» = «Grünspan» …), агрегаторы в `AGGREGATORS`; дубль агрегатор ↔ агрегатор — остаётся первый.
- `collector/venues.clean`: HTML-коды в названиях (`&#8220;` → «“»).
- `db/schema.sql`: новые источники.
- `tests/`: fixture + тест на каждый источник; тесты словаря площадок и дублей между тремя агрегаторами.
- `eval/`: страница разметки пересобирается на новой афише (замер «после» по интересу).

## Задачи (одна задача = один коммит с тестом)
- **T1** ohschonhell (JSON). **T2** concert-news. **T3** sperrstunde. **T4** Golden Pudel.
  **T5** Hafenklang. **T6** Südpol. **T7** Rote Flora. **T8** MS Stubnitz.
  Тест каждого: ≥ 1 событие, у каждого название, дата, url; отменённые отфильтрованы.
- **T9** Словарь площадок + дубли между агрегаторами и сайтами клубов. Тест: Pudel из ohschonhell и с сайта →
  одна строка со временем сайта.
- **T10–T13** Кандидаты по правилу 45 минут: Clubplan, Mojo, Elbphilharmonie, rausgegangen.
- **T14** Деплой → Execute Now → проверка логов и стоимости разбора → замер KPI → новая страница разметки для
  Kirill → `REPORT-3.md`. Бот упал → откат на предыдущий коммит, Redeploy, запись в отчёт.

Зависимости: T1 → T9 (нужен первый агрегатор для проверки дублей); T2–T8 в любом порядке; T10–T13 после T9;
T14 последней.

## Дополнение 04.11, вечер (решения Kirill после REPORT-3)
- **T15** sperrstunde **включить** — сбор только с сервера (как и все источники). `active = TRUE` в схеме.
- **T16** Elbphilharmonie **подключить** (первая страница программы ≈ ближайшие 1–2 дня; традиционная / world).

## Concert News через GitHub Actions (05.11)

**Для кого и зачем.** Concert News с сервера курса (TimeWeb) даёт `urlopen error timed out`, с Mac работает —
похоже на блок IP. Без него в ленте нет Mojo, Mojo Jazz Café, Bahnhof Pauli, Astra Stube и мелких концертных
площадок. GitHub Actions раз в день забирает страницу со своих IP, бесплатно, в форке
`kirilldotdesign/desk-research-ai-public`. `robots.txt` concert-news.de закрывает только `/wp-admin/`.

**Как.** Action скачивает `/konzertkalender/`, разбирает нашим `parse_concertnews` и пишет в ветку `data`
только факты: дата, название, площадка, ссылка → `concertnews.json`. Сырой HTML в публичный репо не кладём.
Collector на сервере читает JSON с `raw.githubusercontent.com` (GitHub с сервера доступен — Coolify тянет код оттуда).
Дедупликация, окно 14 дней, разбор моделью — без изменений.

### KPI
| KPI | Тип | Порог | До (05.11) | После |
|---|---|---|---|---|
| concert-news.de отвечает с GitHub (разовый `curl` в `workflow_dispatch`) | работает ли | HTTP 200, страница со списком | — | **HTTP 200, 185 КБ, `myFuture` есть** ✅ (05.11, run 41976498775) |
| Событий в `concertnews.json` после прогона Action | работает ли | > 0 | — | **1570 событий, 70 площадок** ✅ (05.11, run 41976773851; Bahnhof Pauli, Mojo есть) |
| Concert News в прогоне collector на сервере | работает ли | ≥ 1 событие, нет «timed out» в `/status` | timeout | **208 в окне, 117 новых, без ошибок** ✅ (прогон 50, 05.11 05:58 UTC) |
| Площадок в афише за 14 дней | полезно ли | > 73 | 73 (REPORT-4) | **97** ✅ (433 события; 117 от Concert News, все разобраны моделью) |
| Mojo / Bahnhof Pauli в живой ленте | полезно ли | есть | нет | **есть** ✅ (Mojo Club, Bahnhof Pauli; Jazz Café в ближайшие 14 дней нет) |

### Что меняем и где
- новые: `.github/workflows/concertnews.yml`, `collector/mirror_concertnews.py`, `tests/test_concertnews_json.py`
- правки: `collector/venues.py` (парсер `parse_concertnews_json` + `PARSERS`), `collector/dedup.py` (`AGGREGATORS`),
  `db/schema.sql` (UPDATE источника Concert News)

### Задачи
- **T0 (проверка, без кода в `collector/`)** Разовый workflow `workflow_dispatch` с одним `curl` на
  `https://www.concert-news.de/konzertkalender/`: код ответа и есть ли `id="myFuture"`. Тайм-аут / 403 →
  стоп, задачи T17–T19 не делаем, возвращаемся к вариантам Hetzner / Apify. Этот workflow потом заменяется T17.
- **T17** `.github/workflows/concertnews.yml`: cron `30 4 * * *` UTC (до collector в 06:00) + `workflow_dispatch`.
  Checkout `master` → Python 3 → `pip install -r requirements.txt` (`collector.main` импортирует `psycopg`) →
  `python -m collector.mirror_concertnews` → commit `concertnews.json` в ветку `data` через `GITHUB_TOKEN`
  (`permissions: contents: write`), только если файл изменился.
- **T18** `collector/mirror_concertnews.py`: `fetch` из `collector/main.py` → `parse_concertnews` → JSON
  (`starts_at` в ISO) → файл. В `collector/venues.py` — `parse_concertnews_json(page)`: `json.loads`, ISO обратно
  в datetime с `BERLIN`; в `PARSERS` как `concertnews_json`; в `dedup.AGGREGATORS` добавить `concertnews_json`.
  Тест `tests/test_concertnews_json.py`: fixture HTML → mirror → JSON → `parse_concertnews_json` дают те же
  события (название, площадка, дата, url). Старый `test_concertnews` не меняется.
- **T19** `db/schema.sql`: `UPDATE sources SET kind = 'concertnews_json', url =
  'https://raw.githubusercontent.com/kirilldotdesign/desk-research-ai-public/data/concertnews.json'
  WHERE name = 'Concert News'` (как для sperrstunde). Затем push → Redeploy → Action вручную → collector Execute Now →
  замер KPI «после» сюда.

Зависимости: T0 → T17 → T18 → T19. T18 можно писать параллельно с T17, но коммит после зелёного T0.

### Риски
- Коммит Action'а в `data` не должен запускать деплой Coolify (он следит за `master`). Проверено 05.11: пуши в `master` и `data` деплой не запустили, все деплои ручные.
- Action упал → JSON вчерашний, `upcoming` отрежет прошедшие дни. Свежесть видна по коммитам ветки `data`.
- GitHub отключает cron через 60 дней без активности в репо — пока репо живой, не проблема.
- `upstream` (курс) этой ветки и workflow не получает — правка только в форке.

### Открытые вопросы
- Нет.

Утверждено: Kirill, 05.11.2026 («утверждаю»)

Замер «после»: 05.11.2026, деплой `6390e35`, Action run 41976773851, прогон collector 50. Тестов 121, все зелёные.
Вне спеки: поправлены `test_collector_note` и `test_venues_dedup` (искали источник по старому `kind`; первый ещё зависел от порядка строк); `mirror_concertnews` при 0 событий падает и оставляет вчерашний JSON.

## Бэклог
- **Concert News с сервера** — `urlopen error timed out` (с Mac работает). Похоже на блок IP дата-центров; не обходим. Источник оставлен включённым, в `/status` видно «недоступны».
- **T10 Clubplan / календарь Clubkombinat** — не подключён: данные идут через GraphQL Hamburg Tourismus
  (`content-delivery.imxplatform.de/hht/imxplatform`), запрос требует API-токен. Токен, встроенный в чужой
  виджет, не используем. Вариант: попросить доступ у Clubkombinat / Hamburg Tourismus.
- **T11 Mojo Club** — не подключён: на сайте нет списка событий ни в HTML, ни в WordPress API. Mojo и
  Jazz Café приходят через concert-news (без времени).
- **T12 Elbphilharmonie** — не подключена: `robots.txt` прямо запрещает ClaudeBot. Решает Kirill.
  Традиционная / world-музыка там есть (Shavnabada, грузинский хор), страницы событий `/de/programm/<slug>/<id>`.
- **T13 rausgegangen.de** — не подключён: отдаёт 403 нашему боту; обходить защиту не будем. Вариант: спросить API.
- **sperrstunde.org** — парсер готов (T3), но источник выключен (`active = FALSE`): `robots.txt` блокирует
  ИИ-ботов (GPTBot, ClaudeBot). Без него пропадают Buttclub, Gängeviertel-DIY и часть Rote Flora. Решает Kirill.
- Instagram через Apify (решение 2): кандидат Moloch, если он вообще работает.
- Параллельный разбор моделью (первый прогон станет ~300+ событий).
- Сторож (из SPEC 2).

---
Утверждено: Kirill, 04.11.2026 («утверждаю»)
