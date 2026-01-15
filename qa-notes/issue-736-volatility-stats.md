# Issue #736: API: Volatility metrics in /recommendations/stats

## What Changed
- Added `volatility` field to `GET /recommendations/stats` response
- New helper function `_calculate_volatility()` computes:
  - `cpa_cv`: Coefficient of variation for CPA (std_dev / mean)
  - `success_rate_variance`: Variance in daily success rates
  - `interpretation`: low | medium | high | insufficient_data
  - `sample_size`: Number of outcomes used for calculation

## Response Structure
```json
{
  "success": true,
  "data": {
    "total_recommendations": 100,
    "by_mode": {"exploitation": 75, "exploration": 25},
    "exploration_rate": 0.25,
    "target_exploration_rate": 0.25,
    "with_outcome": 50,
    "successful": 30,
    "success_rate": 0.6,
    "volatility": {
      "cpa_cv": 0.2345,
      "success_rate_variance": 0.0512,
      "interpretation": "medium",
      "sample_size": 50
    }
  }
}
```

## Volatility Interpretation
- `< 0.1`: low (stable performance)
- `0.1-0.3`: medium
- `> 0.3`: high (unstable performance)
- `insufficient_data`: less than 2 outcomes

## Files Changed
- `decision-engine-service/src/services/recommendation.py`

## Test
```bash
curl -sf localhost:10000/recommendations/stats -H "Authorization: Bearer $API_KEY" | jq '.data.volatility'
```
