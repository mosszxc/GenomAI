# Keitaro API Data Classification

**Последнее обновление:** 2025-12-22  
**Версия API:** v1

## Endpoints

### 1. POST /admin_api/v1/report/build

#### 1.1 Get Trackers (dimensions: sub_id_1)

**Request:**
```json
{
  "range": {"interval": "yesterday"},
  "metrics": ["clicks"],
  "dimensions": ["sub_id_1"]
}
```

**Response Structure:**
```json
{
  "rows": [
    {
      "sub_id_1": "KT-123456",
      "clicks": 1000
    }
  ],
  "total": 1,
  "meta": []
}
```

**Classification:**
- `rows`: Array<Object> - массив объектов с dimension и metrics
- `rows[].sub_id_1`: String - уникальный идентификатор tracker
- `rows[].clicks`: Number - количество кликов
- `total`: Number - общее количество записей
- `meta`: Array - метаданные (опционально)

**Examples:**
- [Примеры реальных ответов будут добавлены после первого выполнения workflow]

#### 1.2 Get Campaign Metrics (filter: sub_id_1 = tracker_id)

**Request:**
```json
{
  "range": {"interval": "yesterday"},
  "metrics": ["clicks", "conversions", "revenue", "cost"],
  "filters": [
    {
      "name": "sub_id_1",
      "operator": "EQUALS",
      "expression": "KT-123456"
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

