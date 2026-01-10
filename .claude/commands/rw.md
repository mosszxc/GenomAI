# Ralph Wiggum Loop (rw)

Итеративная проверка **КОНКРЕТНОГО завершённого результата**. НЕ для сканирования или исследования.

## Когда использовать

✅ **ПОСЛЕ завершения задачи** — проверить итог
✅ **После закрытия issue** — верификация что всё работает
✅ **После деплоя** — убедиться что изменения применились

## Когда НЕ использовать

❌ **Во время исследования/сканирования проекта**
❌ **При активном Task/Explore агенте**
❌ **Без конкретного завершённого результата**

### Cosmetic Exclusions (Token Optimization)

**SKIP /rw для:**
- Node position changes в workflow JSON
- Documentation updates (*.md files)
- Comments/formatting only changes
- CLAUDE.md rules updates
- Typo fixes

**Причина:** /rw тратит 5-10k токенов. Для cosmetic changes нет DB writes → нечего верифицировать.

## Формат

```
/rw {процесс} --max-iterations 5 --completion-promise 'VERIFIED'
```

**Обязательные параметры:**
- `--max-iterations N` — лимит итераций (рекомендуется 3-5)
- `--completion-promise 'ФРАЗА'` — условие остановки

## Действие

1. **СТОП если:** активен другой процесс (скан, explore, исследование)

2. Запусти bash скрипт:

```bash
/Users/mosszxc/.claude/plugins/cache/claude-plugins-official/ralph-loop/latest/scripts/setup-ralph-loop.sh $ARGUMENTS
```

3. Работай **СТРОГО** в рамках указанного процесса и результата.

4. После каждой итерации проверяй:
   - Результат соответствует ожиданию? → `<promise>VERIFIED</promise>`
   - Нужны исправления? → внеси и продолжи

## Процессы

| Процесс | Что проверяем | Критерий успеха |
|---------|---------------|-----------------|
| загрузка креатива | spy_creatives, decomposed_creatives | Данные в БД |
| learning loop | learnings, metrics_daily | Записи созданы |
| hypothesis factory | hypotheses, ideas | Гипотеза создана |
| decision engine | decisions, ideas | APPROVE/REJECT записан |
| video ingestion | videos, transcripts | Транскрипт есть |
| keitaro poller | metrics_daily, creatives | Метрики загружены |

## Правила

1. **ТОЛЬКО после завершения задачи** — не во время работы
2. **НЕ ТРОГАТЬ** workflows/таблицы/код вне указанного процесса
3. **ВСЕГДА указывать --max-iterations** — без лимита зациклится
4. Если задача требует изменений в другом процессе — СТОП
5. После успешной верификации — `/valid {process}`

## Примеры

```
# После fix issue #213
/rw decision engine --max-iterations 3 --completion-promise 'VERIFIED'

# После настройки workflow
/rw learning loop --max-iterations 5 --completion-promise 'WORKING'

# Проверка загрузки креатива
/rw загрузка креатива --max-iterations 3 --completion-promise 'DATA OK'
```

## Интеграция с workflow

```
1. Завершить задачу/issue
2. Commit + push
3. /rw {процесс} --max-iterations 3 --completion-promise 'VERIFIED'
4. Если VERIFIED → /valid {process} → done
5. Если не VERIFIED → fix → repeat
```
