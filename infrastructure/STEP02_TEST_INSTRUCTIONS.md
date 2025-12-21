# STEP 02 — Decomposition Workflow Test Instructions

**Workflow ID:** `mv6diVtqnuwr7qev`  
**Статус:** ✅ Workflow готов к тестированию

## 🧪 Способ тестирования

Я добавил **Manual Trigger (Test)** node для тестирования без webhook.

### Шаги для тестирования:

1. **Откройте workflow в n8n UI:**
   - URL: `https://kazamaqwe.app.n8n.cloud/workflow/mv6diVtqnuwr7qev`

2. **Найдите "Manual Trigger (Test)" node:**
   - Это временный trigger для тестирования
   - Находится в начале workflow

3. **Запустите workflow:**
   - Кликните на "Manual Trigger (Test)" node
   - Нажмите "Execute Node" или "Test workflow"
   - Workflow автоматически использует тестовые данные из "Set Test Data" node

4. **Проверьте результаты:**
   - Workflow должен пройти через все ноды:
     - Load Canonical Schema ✅
     - LLM Call (Classification) ✅
     - Schema Validation ✅
     - Persist Transcript ✅
     - Persist Decomposed Creative ✅
     - Emit TranscriptCreated ✅
     - Emit CreativeDecomposed ✅
     - Merge Results ✅
     - Success Response ✅

5. **Проверьте данные в БД:**
   ```sql
   -- Проверка transcripts
   SELECT * FROM genomai.transcripts 
   WHERE creative_id = '1770cbbb-3381-4ca5-8ae7-dfb85433655f';
   
   -- Проверка decomposed_creatives
   SELECT * FROM genomai.decomposed_creatives 
   WHERE creative_id = '1770cbbb-3381-4ca5-8ae7-dfb85433655f';
   
   -- Проверка событий
   SELECT * FROM genomai.event_log 
   WHERE event_type IN ('TranscriptCreated', 'CreativeDecomposed')
     AND payload::text LIKE '%1770cbbb-3381-4ca5-8ae7-dfb85433655f%'
   ORDER BY occurred_at DESC;
   ```

## ✅ Ожидаемые результаты

После успешного выполнения:

1. ✅ **Transcript создан** в `genomai.transcripts`
   - `creative_id`: `1770cbbb-3381-4ca5-8ae7-dfb85433655f`
   - `version`: `1`
   - `transcript_text`: тестовый транскрипт

2. ✅ **Decomposed Creative создан** в `genomai.decomposed_creatives`
   - `creative_id`: `1770cbbb-3381-4ca5-8ae7-dfb85433655f`
   - `schema_version`: `v1`
   - `payload`: JSON с классификацией по Canonical Schema

3. ✅ **События записаны** в `genomai.event_log`
   - `TranscriptCreated` event
   - `CreativeDecomposed` event

4. ✅ **Schema валидна**
   - Все обязательные поля присутствуют
   - Все enum значения корректны
   - Нет запрещённых полей (confidence, novelty, scores)

## 🧹 После тестирования

После успешного теста можно удалить временные ноды:
- "Manual Trigger (Test)"
- "Set Test Data"

Или оставить их для будущих тестов.

## ⚠️ Примечания

- Manual Trigger работает только для тестирования
- Для production используйте Webhook Trigger (требует активации через UI)
- Тестовые данные жестко закодированы в "Set Test Data" node


