# Issue #735: API - Связь recommendations с decisions

## Что изменено

- Добавлено поле `decision_id` в response `GET /recommendations/` и `GET /recommendations/{id}`
- Создана helper-функция `get_decision_id_for_creative()` для получения decision через цепочку:
  - `recommendation.creative_id` → `decomposed_creatives.creative_id` → `idea_id` → `decisions.idea_id`
- Обновлена документация в `docs/API_REFERENCE.md`

## Логика

- `decision_id` = `null` если recommendation не executed (нет `creative_id`)
- `decision_id` = `null` если creative не имеет связанной idea или decision
- `decision_id` = UUID последнего decision для idea

## Файлы

- `decision-engine-service/src/services/recommendation.py` - добавлен `get_decision_id_for_creative()`, обновлены `get_recommendation()` и `get_pending_recommendations()`
- `docs/API_REFERENCE.md` - обновлена документация Recommendations API

## Test

```bash
# Проверяем что endpoint /recommendations/ возвращает массив с полем decision_id в каждом элементе
curl -sf http://localhost:10000/recommendations/ -H "Authorization: Bearer $API_KEY" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('success'), 'API failed'; data=d.get('data',[]); print(f'OK: {len(data)} recommendations'); [print(f'  - {r.get(\"id\")}: decision_id={r.get(\"decision_id\")}') for r in data[:3]]"
```
