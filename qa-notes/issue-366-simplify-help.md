# QA Notes: Issue #366 - Simplify /help command

## Summary
Упрощён /help для баеров: 4 команды вместо 17.

## Changes
- **File:** `decision-engine-service/src/routes/telegram.py:405-414`
- **Removed from /help:** /genome (4 variants), /confidence, all admin commands, /knowledge
- **Kept:** /start, /stats, /feedback, /help + video upload instructions

## Testing
Требует деплоя для проверки. После деплоя:
```
/help в Telegram → должно показать только 4 команды
```

## Commands still working
Удалённые из /help команды продолжают работать:
- /genome, /confidence — для продвинутых пользователей
- Admin commands — только для admin (is_admin проверка)

## Risk
Low — UI-only change, no logic changes.
