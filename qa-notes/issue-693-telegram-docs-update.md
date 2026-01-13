# Issue #693: Обновление документации по Telegram интеграции

## Что изменено

- Удалён `infrastructure/TELEGRAM_WORKFLOWS_QUICK_START.md` — устаревший (описывал n8n)
- Удалён `infrastructure/TELEGRAM_SETUP_SUMMARY.md` — устаревший (описывал n8n)
- Обновлён `infrastructure/TELEGRAM_BOT_SETUP.md`:
  - Версия v3.0
  - Убраны все упоминания n8n
  - Добавлен полный список команд (buyer + admin)
  - Актуализирована архитектура (FastAPI + Temporal)
  - Добавлены env переменные для безопасности
  - Добавлены Temporal workflows

## Test

```bash
grep -q "n8n" infrastructure/TELEGRAM_BOT_SETUP.md && echo "FAIL: n8n still mentioned" && exit 1 || echo "OK: no n8n references"
```
