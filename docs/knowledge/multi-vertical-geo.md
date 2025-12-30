# Multi-Vertical/Geo Support

## Current State

Баеры могут работать на нескольких вертикалях и гео одновременно.

### Database

```sql
buyers.verticals[]  -- Array: {POT, PROST, WL}
buyers.geos[]       -- Array: {MX, DE, US}
```

### При регистрации креатива

Креатив получает контекст из **первого элемента** массивов:

```javascript
target_vertical: buyer.verticals[0]  // POT
target_geo: buyer.geos[0]            // MX
```

### Почему первый элемент?

1. Баер указывает основную вертикаль/гео первой
2. Система не спрашивает "для какой вертикали этот креатив"
3. Простое решение для MVP

---

## Affected Workflows

| Workflow | Как получает vertical/geo |
|----------|---------------------------|
| Buyer Creative Registration | Check Buyer → `verticals,geos` в select |
| Spy Creative Registration | Check Buyer → `verticals,geos` в select |
| Zaliv Session Handler | Parse Creative → `body.buyer.verticals/geos` |
| Idea Registry Create | Canonical Hash → `buyer.vertical` (deprecated single) |

---

## Known Issues

1. **Idea Registry** использует `buyer.vertical` (single) вместо `verticals[0]` → #192
2. **Avatar hash** не включает geo → #194
3. **Fatigue constraint** - заглушка → #195
4. **DE checks** не фильтруют по vertical/geo → #196

---

## Future Improvements

1. Спрашивать у баера при регистрации: "Для какой вертикали/гео этот креатив?"
2. Разделить learnings по vertical+geo+avatar
3. Добавить vertical/geo в decision_traces для аналитики
