# Issue #218: Keitaro Poller не работает 2+ дней

## Проблема
Метрики в `raw_metrics_current` устарели на 3+ дня. Последнее обновление: 2025-12-31 00:00 UTC.

## Диагностика
1. Workflow `0TrVJOtHiNEEAsTN` (Keitaro Poller) активен в n8n
2. API key валиден
3. **Домен Keitaro изменился:**
   - Старый: `https://uniaffburan.com` (возвращал 401)
   - Новый: `https://uniaffzhb.com` (работает)

## Решение
Обновлён домен в `genomai.keitaro_config`:
```sql
UPDATE genomai.keitaro_config
SET domain = 'https://uniaffzhb.com'
WHERE is_active = true;
```

## Верификация
- API тест: HTTP 200, 774 кампаний (565 активных)
- Workflow запустится по schedule и обновит метрики

## Root Cause
Изменение домена Keitaro без обновления конфигурации в GenomAI.

## Prevention
Добавить мониторинг Keitaro API health в Pipeline Health Monitor workflow.
