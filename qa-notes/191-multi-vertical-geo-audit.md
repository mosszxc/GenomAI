# QA Notes: Multi-Vertical/Geo Audit (#191)

## Summary

Аудит системы на поддержку множественных вертикалей и гео для баеров.

---

## Findings

### Что работает

| Компонент | Статус | Детали |
|-----------|--------|--------|
| `buyers.geos[]` | OK | Массив гео, поддержка нескольких значений |
| `buyers.verticals[]` | OK | Массив вертикалей, поддержка нескольких |
| `geo_lookup` | OK | 24 гео с алиасами |
| `vertical_lookup` | OK | 14 вертикалей с алиасами |
| `avatars.vertical/geo` | OK | Поля есть, связь через idea |
| `component_learnings.geo` | Partial | Сохраняет geo, но только первый из массива |
| `recommendations.geo/vertical` | OK | Поля есть |
| Buyer Onboarding | OK | Собирает и нормализует vertical/geo |

### Критические проблемы

#### 1. Использование только первого значения из массива

**idea_registry.py:331-332:**
```python
vertical = buyer.get('vertical', 'unknown')  # Не verticals[]!
geo = buyer.get('geo', 'unknown')  # Не geos[]!
```

**component_learning.py:184:**
```python
return geos[0] if geos else None  # Только первый geo!
```

**idea_registry_create (n8n) Canonical Hash node:**
```javascript
const vertical = buyer.vertical || 'unknown';
const geo = buyer.geo || 'unknown';
```

#### 2. Отсутствие vertical/geo в core таблицах

| Таблица | vertical | geo | Проблема |
|---------|----------|-----|----------|
| `ideas` | - | - | Только через avatar_id |
| `hypotheses` | - | - | Нет полей |
| `decisions` | - | - | Нет полей |
| `creatives` | - | - | Нет полей, только buyer_id |
| `decomposed_creatives` | - | - | Нет полей |

#### 3. DE Checks не учитывают vertical/geo

- `schema_validity.py` - нет
- `death_memory.py` - нет
- `fatigue_constraint.py` - **заглушка** (always PASSED)
- `risk_budget.py` - нет

#### 4. Avatar hash включает только vertical

```javascript
const avatarHashInput = [vertical, deepDesireType, primaryTrigger, awarenessLevel].join('|');
```

Geo **не входит в hash** → один avatar для разных гео с одинаковым vertical!

---

## Impact

1. **Learnings смешиваются** - если баер работает на MX и DE с POT, learnings идут в общий котёл
2. **Fatigue не работает по vertical/geo** - нет отдельного отслеживания
3. **Recommendations не учитывают контекст** - какой vertical/geo актуален для конкретного креатива
4. **Нельзя фильтровать decisions по vertical/geo** - для аналитики

---

## Recommendations

### Phase 1: Quick Wins (без миграций)

1. **Передавать vertical/geo в контексте креатива**
   - При регистрации креатива указывать для какого vertical/geo
   - Сохранять в `creatives` metadata/context

2. **Использовать verticals[0]/geos[0] осознанно**
   - Документировать что берётся первый
   - Или запрашивать у баера при регистрации креатива

### Phase 2: Schema Changes

1. **Добавить поля в creatives:**
   ```sql
   ALTER TABLE genomai.creatives
   ADD COLUMN target_vertical TEXT,
   ADD COLUMN target_geo TEXT;
   ```

2. **Добавить geo в avatar hash:**
   ```javascript
   const avatarHashInput = [vertical, geo, deepDesireType, primaryTrigger, awarenessLevel].join('|');
   ```

3. **Реализовать fatigue по vertical+geo:**
   - Таблица `fatigue_state_versions` уже есть
   - Добавить vertical/geo ключи

### Phase 3: Full Multi-Context

1. **При регистрации креатива спрашивать контекст**
2. **Разделить learnings полностью по vertical+geo+avatar**
3. **Добавить vertical/geo в decision_traces для аналитики**

---

## Current Buyer Data

```
buyers:
  - name: TU
    geo: MX (deprecated)
    geos: [MX]
    vertical: POT (deprecated)
    verticals: [POT, PROST]
```

Баер TU работает на 2 вертикалях (POT, PROST), но система использует только первую.

---

## Edge Cases

1. **Один креатив - разные гео?** - Нельзя. Креатив привязан к buyer, buyer к geos[].
2. **Смена вертикали баером** - verticals[] обновляется, но исторические данные остаются со старыми
3. **Avatar reuse между гео** - Сейчас один avatar на vertical (без geo в hash)

---

## Files Reviewed

- `decision-engine-service/src/services/idea_registry.py`
- `decision-engine-service/src/services/avatar_service.py`
- `decision-engine-service/src/services/component_learning.py`
- `decision-engine-service/src/services/recommendation.py`
- `decision-engine-service/src/checks/fatigue_constraint.py`
- n8n workflows: idea_registry_create, Buyer Onboarding, Daily Recommendation Generator
