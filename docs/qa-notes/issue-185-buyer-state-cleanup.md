# QA Notes: Buyer State Cleanup (Issue #185)

## Summary
Автоматический сброс buyer_states после 15 минут AFK.

## Workflow Details

### Current (Integrated)
- **ID:** H1uuOanSy627H4kg (Pipeline Health Monitor)
- **Schedule:** Every 6 hours
- **Timeout:** 15 minutes AFK
- **Nodes:** Check Buyer States → Filter AFK States → Reset Buyer State

### Deprecated
- **ID:** 5tJA4rinnJgd1LFO (Buyer State Cleanup standalone)
- **Status:** DEACTIVATE IN UI - functionality moved to Pipeline Health Monitor

## Edge Cases & Gotchas

### 1. Supabase Node useCustomSchema Bug
**Problem:** Supabase node в n8n игнорирует `options.useCustomSchema` при update через API.
**Solution:** Использовать HTTP Request с headers:
```
Content-Profile: genomai
Accept-Profile: genomai
```

### 2. updated_at Trigger
**Problem:** Таблица `buyer_states` имеет trigger `trigger_buyer_states_updated` который автоматически обновляет `updated_at` при любом UPDATE.
**Impact:** Нельзя вручную установить updated_at в прошлое без отключения trigger.
**Workaround for testing:**
```sql
ALTER TABLE genomai.buyer_states DISABLE TRIGGER trigger_buyer_states_updated;
UPDATE genomai.buyer_states SET updated_at = '...' WHERE ...;
ALTER TABLE genomai.buyer_states ENABLE TRIGGER trigger_buyer_states_updated;
```

### 3. Telegram "chat not found"
**Problem:** Telegram возвращает 400 если бот не добавлен к пользователю.
**Solution:** Добавлен `onError: continueRegularOutput` на Notify User node.

### 4. n8n Active Version Cache
**Problem:** После update workflow через API, active version может не обновиться.
**Solution:** Деактивировать и снова активировать workflow в UI после изменений через API.

## Test Results
| Test Case | Input | Expected | Actual | Status |
|-----------|-------|----------|--------|--------|
| Stuck state detection | state=awaiting_urls, age=20min | Reset to idle | idle | PASS |
| Fresh state skip | state=awaiting_urls, age=5min | No change | No change | PASS |
| Idle state skip | state=idle | No change | No change | PASS |
| DB update | Reset triggered | state=idle, context={} | state=idle, context={} | PASS |

## Monitoring
- Pipeline Health Monitor отслеживает stuck buyer_states И автоматически сбрасывает их каждые 6 часов

## Integration Notes
- Buyer state cleanup интегрирован в Pipeline Health Monitor для уменьшения количества executions
- Три новых ноды работают параллельно с основной health check логикой
- Filter AFK States корректно пропускает idle/completed/failed states
