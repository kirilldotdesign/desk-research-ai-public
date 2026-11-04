# Отчёт «источники, часть 2» — 04.11.2026, ночь

Спеки нет — по решению Kirill («делай, спеку потом»). SPEC-4.md написать задним числом.

Деплой `4cb49c3`, прогон 48: 103 новых события, 103/103 разобрано, 0 сбоев.
**Лента: 303 события на 73 площадках** (было 202 / 53).

| Источник | Событий | Что даёт |
|---|---|---|
| KRACH Metal (агрегатор) | 22 новых (30 в окне) | вся тяжёлая сцена с жанрами: Bambi Galore, Logo, Grosse Freiheit 36, BETTY, Monkeys … |
| Markthalle | 11 | Hatebreed + Life of Agony, Eluveitie … |
| Fabrik | 13 | world, джаз, фолк (schema.org Event) |
| Cascadas | 15 | Funky Dance Night (Boogie Funk), Caribbean Night |
| KENT Club | 12 | Afrobeats-вечера, концерты (без времени) |
| Pony Bar | 11 | Italo, dark wave, джаз, бесплатно |
| VAMH (агрегатор) | 9 | эксперимент / нойз: Hörbar, Stubnitz, Strobreden |
| Frau Hedi | 8 | Balearic Disco Yachtride, Italo (без времени) |
| Kampnagel | 2 | только музыка (Überjazz, Pussy Riot); театр и Krimifestival отсеяны |

Не подключено: **YOTO** (сайт на Wix, всё через JS), **Logo** отдельно (старый сайт; его концерты приходят через KRACH),
**Concert News** (с сервера timeout, как раньше).

Дубли: новое правило «тот же клуб + день + первые два слова названия» (Holy Mother, Billy Zach, Next Time). 0 дублей
на локальном прогоне по живым сайтам. Тестов: 116, все зелёные.

Отклонения от CLAUDE.md (по решению Kirill): код без спеки и «утверждаю»; один коммит на 9 источников.
