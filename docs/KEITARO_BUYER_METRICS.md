# Keitaro Buyer Metrics

## Как найти данные buyer'а

### Источник данных
Buyers идентифицируются по `sub_id_10`, НЕ по `source`.

```bash
curl -s -X POST "https://{domain}/admin_api/v1/report/build" \
  -H "Api-Key: {api_key}" \
  -H "Content-Type: application/json" \
  -d '{
    "range": {"from": "2026-01-01", "to": "2026-01-10", "timezone": "UTC"},
    "metrics": ["clicks", "conversions", "sales", "revenue", "cost", "profit"],
    "dimensions": ["sub_id_10"]
  }'
```

### Метрики

| Метрика | Описание |
|---------|----------|
| `conversions` | Лиды (заявки) |
| `sales` | Апрувы (подтверждённые продажи) |
| `revenue` | **Gross revenue оффера** (НЕ payout байеру) |
| `cost` | Расходы на рекламу (FB Ads и т.д.) |
| `profit` | revenue - cost (некорректно для расчёта profit байера) |

### Расчёт реального profit байера

```
Payout байера = sales × payout_per_sale
Profit байера = Payout - cost
```

**Пример (TU, январь 2026):**
- Sales: 315
- Payout per sale: $30.5
- Payout: 315 × $30.5 = $9,607
- Cost: $7,818
- **Profit: $1,789** (buyer подтвердил ~$1,747.73)

### Почему revenue в Keitaro не равен payout

`revenue` в Keitaro — это gross revenue оффера (сколько оффер получает с клиента).
Buyer получает только часть — payout per sale × количество sales.

В примере TU:
- Revenue (Keitaro): $26,779
- Payout (реальный): $9,607
- Соотношение: ~36%

### Где хранится payout per sale

Payout per sale зависит от оффера и договорённости с buyer'ом.
Нужно хранить в `genomai.buyers` или получать из CRM/оффера.
