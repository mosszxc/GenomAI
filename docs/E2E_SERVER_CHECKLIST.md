# E2E Server Testing Checklist

После деплоя на production выполнить следующие проверки.

## Prerequisites

```bash
# Установить переменные окружения (если нужно для curl)
export API_KEY="..."
export E2E_TRACKER_ID="99999"  # тестовый tracker
```

## Quick Health Check (обязательно после каждого деплоя)

```bash
make e2e-quick
```

**Должно пройти:**
- [ ] Decision Engine health: HTTP 200
- [ ] Supabase connectivity: query работает
- [ ] No stuck pipeline stages

**Ручная проверка:**
```bash
curl -s https://genomai.onrender.com/health
# Ожидаем: {"status":"ok"}
```

## Full E2E Flow (после major changes)

```bash
make e2e
```

### Manual Test Steps

#### 1. Creative Registration (T+0)
Отправить тестовое видео через Telegram или webhook.

**Проверка:**
```sql
SELECT id, tracker_id, status, created_at
FROM genomai.creatives
WHERE tracker_id = '99999'
ORDER BY created_at DESC
LIMIT 1;
```
- [ ] Creative появился в БД
- [ ] `status IN ('pending', 'registered')`

#### 2. Transcription (T+2min)
```sql
SELECT t.id, t.creative_id, length(t.transcript_text) as text_length
FROM genomai.transcripts t
JOIN genomai.creatives c ON c.id = t.creative_id
WHERE c.tracker_id = '99999'
ORDER BY t.created_at DESC
LIMIT 1;
```
- [ ] Transcript создан
- [ ] `transcript_text` не пустой

#### 3. Decomposition (T+3min)
```sql
SELECT dc.id, dc.creative_id, dc.idea_id, dc.payload
FROM genomai.decomposed_creatives dc
JOIN genomai.creatives c ON c.id = dc.creative_id
WHERE c.tracker_id = '99999'
ORDER BY dc.created_at DESC
LIMIT 1;
```
- [ ] `decomposed_creatives` record exists
- [ ] `payload` содержит canonical fields
- [ ] `idea_id` linked

#### 4. Decision Engine (T+5min)
```sql
SELECT d.id, d.idea_id, d.decision, d.reason
FROM genomai.decisions d
JOIN genomai.ideas i ON i.id = d.idea_id
JOIN genomai.decomposed_creatives dc ON dc.idea_id = i.id
JOIN genomai.creatives c ON c.id = dc.creative_id
WHERE c.tracker_id = '99999'
ORDER BY d.created_at DESC
LIMIT 1;
```
- [ ] Decision в `decisions` table
- [ ] Result: approve/reject/defer

#### 5. Decision Trace
```sql
SELECT dt.id, dt.decision_id, dt.check_name, dt.result
FROM genomai.decision_traces dt
JOIN genomai.decisions d ON d.id = dt.decision_id
JOIN genomai.ideas i ON i.id = d.idea_id
JOIN genomai.decomposed_creatives dc ON dc.idea_id = i.id
JOIN genomai.creatives c ON c.id = dc.creative_id
WHERE c.tracker_id = '99999'
ORDER BY dt.created_at DESC;
```
- [ ] Traces для всех 4 checks (schema, death_memory, fatigue, risk_budget)

#### 6. Hypothesis (только для approve)
```sql
SELECT h.id, h.idea_id, h.status, length(h.content) as content_length
FROM genomai.hypotheses h
JOIN genomai.ideas i ON i.id = h.idea_id
JOIN genomai.decomposed_creatives dc ON dc.idea_id = i.id
JOIN genomai.creatives c ON c.id = dc.creative_id
WHERE c.tracker_id = '99999'
ORDER BY h.created_at DESC
LIMIT 1;
```
- [ ] `hypotheses` record exists (если decision = approve)
- [ ] `content` не пустой
- [ ] `status = 'delivered'`

#### 7. Metrics & Learning (T+1hour)
```sql
SELECT rm.id, rm.creative_id, rm.clicks, rm.conversions
FROM genomai.raw_metrics_current rm
JOIN genomai.creatives c ON c.id = rm.creative_id
WHERE c.tracker_id = '99999'
ORDER BY rm.created_at DESC
LIMIT 1;
```
- [ ] `raw_metrics_current` has tracker data

```sql
SELECT oa.id, oa.creative_id, oa.learning_applied
FROM genomai.outcome_aggregates oa
JOIN genomai.creatives c ON c.id = oa.creative_id
WHERE c.tracker_id = '99999'
ORDER BY oa.created_at DESC
LIMIT 1;
```
- [ ] `outcome_aggregates` created
- [ ] `learning_applied = true`

## Full Pipeline Verification Query

```sql
-- Полный статус pipeline для tracker_id
SELECT
  c.tracker_id,
  c.status as creative_status,
  t.id IS NOT NULL as has_transcript,
  dc.id IS NOT NULL as has_decomposed,
  dc.idea_id IS NOT NULL as idea_linked,
  d.decision as decision_type,
  h.status as hypothesis_status,
  oa.learning_applied
FROM genomai.creatives c
LEFT JOIN genomai.transcripts t ON t.creative_id = c.id
LEFT JOIN genomai.decomposed_creatives dc ON dc.creative_id = c.id
LEFT JOIN genomai.decisions d ON d.idea_id = dc.idea_id
LEFT JOIN genomai.hypotheses h ON h.idea_id = dc.idea_id
LEFT JOIN genomai.outcome_aggregates oa ON oa.creative_id = c.id
WHERE c.tracker_id = '99999';
```

## Regression Checks

```sql
-- Orphan ideas (ideas без decisions)
SELECT count(*) as orphan_ideas
FROM genomai.ideas i
LEFT JOIN genomai.decisions d ON d.idea_id = i.id
WHERE d.id IS NULL AND i.created_at > now() - interval '24 hours';

-- Approved без hypotheses
SELECT count(*) as approved_without_hypothesis
FROM genomai.decisions d
LEFT JOIN genomai.hypotheses h ON h.idea_id = d.idea_id
WHERE d.decision = 'approve' AND h.id IS NULL
  AND d.created_at > now() - interval '24 hours';
```

- [ ] orphan_ideas = 0
- [ ] approved_without_hypothesis = 0

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| No transcript | n8n transcription logs | Check AssemblyAI status |
| No decomposition | n8n decomposition logs | Check OpenAI API |
| Decision stuck | DE health + Render logs | Restart service |
| No hypothesis | Decision type | Only approve triggers hypothesis |
| No metrics | Keitaro config | Verify tracker_id in Keitaro |
| Pipeline timeout | Temporal UI | Check for stuck workflows |

## API Health Endpoints

```bash
# Decision Engine
curl https://genomai.onrender.com/health

# Temporal (если доступен)
curl http://localhost:8088/api/v1/namespaces/default/workflows
```
