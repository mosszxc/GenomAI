# QA Notes: Issue #299 - Telegram Auto-Recommendations

## Summary
Added `/recommend` command for admin dashboard - "Today's Best Bet" feature.

## What was implemented
- New service `auto_recommend.py` with component scoring algorithm
- `/recommend` Telegram command (admin-only)
- Integration with existing correlation_discovery for synergy/conflict detection

## Algorithm
1. Get top components by win_rate from `component_learnings`
2. Apply synergy bonuses from discovered correlations (lift > 1.0)
3. Apply conflict penalties for negative correlations (lift < 1.0)
4. Factor in freshness score (usage in last 7 days as fatigue proxy)
5. Select best combination across component types
6. Generate reasoning explanation

## Scoring Formula
```
final_score = (base_win_rate + synergy_bonus - conflict_penalty) * freshness_score
```

Where:
- `synergy_bonus = (lift - 1.0) * 0.5` for positive correlations
- `conflict_penalty = (1.0 - lift) * 0.5` for negative correlations
- `freshness_score`: 1.0 (fresh), 0.9 (1-2 uses), 0.5 (3+ uses in 7 days)

## Test Results
```
POST /webhook/telegram with /recommend
Response: 200 OK

buyer_interactions log:
- direction: in, content: "/recommend"
- direction: out, content: "Today's Best Bet..." (full formatted message)
```

## Output Format
```
🎯 Today's Best Bet

Based on current learnings + freshness:

┌─────────────────────────────┐
│ emotion + angle + source    │
│ Expected: X% win rate       │
│ Confidence: 🟢/🟡/🔴 HIGH/MED/LOW │
└─────────────────────────────┘

Components:
├── value (type) X% ✓/~/?
...

Why:
• Reasoning points

💡 Synergies: applied synergies
⚠️ Avoided: conflicts avoided
😴 Fatigued (skipped): fatigued components
```

## Files Changed
- `decision-engine-service/src/services/auto_recommend.py` (new)
- `decision-engine-service/src/routes/telegram.py` (handler + routing + help)

## Notes
- Current test data has 0% win rate for all components (all losses)
- Fatigue constraint check is MVP stub (always passes)
- Freshness score used as fatigue proxy based on recent usage

## Related
- Issue #297 - Correlations (synergy/conflict discovery)
- Issue #298 - What-If Simulator
- DailyRecommendationWorkflow (for buyers, this is for admin insight)
