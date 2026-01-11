# Issue #293: Telegram Admin Dashboard - Genome Heatmap

## Summary
Implemented `/genome` command for Telegram that displays component performance matrix (heatmap) showing win rates by component × geography.

## Changes
1. **New file**: `decision-engine-service/src/services/genome_heatmap.py`
   - `get_heatmap_data()` - fetches component_learnings data
   - `format_heatmap_telegram()` - formats matrix with emoji indicators
   - `get_available_component_types()` - lists available component types

2. **Modified**: `decision-engine-service/src/routes/telegram.py`
   - Added `/genome` command handler
   - Updated `/help` to include new command

## Usage
```
/genome                  # Default: emotion_primary
/genome angle_type       # Specific component type
/genome hook_mechanism   # Another example
```

## Output Example
```
🧬 Component Performance Matrix

            MX    US    EU
fear        🔴    🟡    🔴
hope        🟢    🟢    🟡
curiosity   🟡    🟢    🟢

🟢 >30%  🟡 15-30%  🔴 <15%  ⬜ <3 samples

Type: emotion_primary
```

## Testing
1. Syntax validation: OK
2. Import test: OK
3. Data retrieval from component_learnings: OK
4. Telegram formatting: OK

## Data Source
- Table: `genomai.component_learnings`
- Key columns: `component_type`, `component_value`, `geo`, `win_rate` (generated), `sample_size`

## Thresholds
- 🟢 Green: win_rate > 30%
- 🟡 Yellow: win_rate 15-30%
- 🔴 Red: win_rate < 15%
- ⬜ No data: sample_size < 3
