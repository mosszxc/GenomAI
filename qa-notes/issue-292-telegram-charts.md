# Issue #292: Telegram Admin Dashboard - Charts Visualization

## Summary
Added win rate trends chart visualization for Telegram Admin Dashboard using QuickChart API.

## Changes Made

### 1. New Chart Service (`src/services/charts.py`)
- `generate_quickchart_url()` - builds QuickChart API URL from Chart.js config
- `build_win_rate_trend_chart()` - constructs line chart config with labels and datasets
- `get_emotion_win_rate_trends()` - fetches emotion_primary win rates from component_learnings
- `get_component_win_rate_trends()` - fetches top components by sample size
- `generate_win_rate_chart_url()` - main function combining all above

### 2. Telegram Router Updates (`src/routes/telegram.py`)
- Added `send_telegram_photo()` - sends images via Telegram Bot API `sendPhoto`
- Added `handle_trends_command()` - handles `/trends` command (admin only)
- Updated `/help` message to include `/trends` command
- Added command routing for `/trends`

## Testing

### Unit Tests
```bash
# Syntax check
python3 -m py_compile src/routes/telegram.py src/services/charts.py
# Result: OK

# Chart generation test
# Result: QuickChart returns 200, PNG 38KB
```

### Manual Test
Send `/trends` to Telegram bot (admin only) to see emotion win rate chart.

## Technical Notes

1. **QuickChart API** - Free tier, no auth required
2. **Chart.js v2 config** - Compatible with QuickChart
3. **Data source** - `component_learnings` table, `emotion_primary` type
4. **Future improvement** - Add daily snapshots for actual time series trends

## Rollback
Remove `/trends` handler and `charts.py` service if issues arise.
