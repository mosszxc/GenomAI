# Keitaro API Data Classification

**Последнее обновление:** 2026-01-13
**Версия API:** v1

## Endpoints

### 1. POST /admin_api/v1/report/build

#### 1.1 Get Trackers (dimensions: campaign_id)

> **Issue #705:** Изменено с `sub_id_1` на `campaign_id` для соответствия `creatives.tracker_id`.
> `campaign_id` работает для всех кампаний, включая те, где `sub_id_1` не настроен.

**Request:**
```json
{
  "range": {"interval": "yesterday"},
  "metrics": ["clicks"],
  "dimensions": ["campaign_id"]
}
```

**Response Structure:**
```json
{
  "rows": [
    {
      "campaign_id": 10228,
      "clicks": 1000
    }
  ],
  "total": 1,
  "meta": []
}
```

**Classification:**
- `rows`: Array<Object> - массив объектов с dimension и metrics
- `rows[].campaign_id`: Number - ID кампании в Keitaro (используется как tracker_id)
- `rows[].clicks`: Number - количество кликов
- `total`: Number - общее количество записей
- `meta`: Array - метаданные (опционально)

**Examples:**
- [Примеры реальных ответов будут добавлены после первого выполнения workflow]

#### 1.2 Get Campaign Metrics (filter: campaign_id = tracker_id)

**Request:**
```json
{
  "range": {"interval": "yesterday"},
  "metrics": ["clicks", "conversions", "revenue", "cost"],
  "filters": [
    {
      "name": "campaign_id",
      "operator": "EQUALS",
      "expression": "10228"
    }
  ]
}
```

**Response Structure:**
```json
{
  "rows": [
    {
      "clicks": 1000,
      "conversions": 50,
      "revenue": 5000.00,
      "cost": 2000.00
    }
  ],
  "total": 1
}
```

**Classification:**
- `rows`: Array<Object> - массив объектов с агрегированными метриками
- `rows[].clicks`: Number - количество кликов
- `rows[].conversions`: Number - количество конверсий (leads)
- `rows[].revenue`: Number (float) - доход
- `rows[].cost`: Number (float) - затраты (spend)
- `total`: Number - общее количество записей

**Examples:**
- [Примеры реальных ответов будут добавлены после первого выполнения workflow]

**Empty Response (tracker_id not found):**
```json
{
  "rows": [],
  "total": 0
}
```

## Changes Log

- 2025-12-22: Initial classification template created

