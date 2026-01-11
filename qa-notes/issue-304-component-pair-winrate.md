# QA Notes: Issue #304 - Component Pair Winrate Feature

## Summary
Implemented `component_pair_winrate` ML feature to track winrate for `hook_mechanism x angle_type` pairs.

## Changes
1. **New files:**
   - `src/services/features/__init__.py` - Features module init
   - `src/services/features/component_pair_winrate.py` - Main feature implementation

2. **Modified files:**
   - `src/services/learning_loop.py` - Added feature computation in `process_single_outcome()`

3. **Database:**
   - Registered feature in `genomai.feature_experiments` with status `shadow`
   - Feature ID: `4429939a-9663-4eaf-b694-e874d1dae6b1`

## Feature Details
- **Name:** `component_pair_winrate`
- **Status:** `shadow` (collecting data, not used in decisions)
- **Computation:** Winrate for each `hook_mechanism x angle_type` pair where CPA < 5 = win
- **Min sample size:** 10 outcomes per pair

## Test Results
- Syntax check: PASS
- Import test: PASS
- Feature registration: PASS (shadow mode)
- Data availability: No pairs with sufficient samples yet (expected for new feature)

## Validation Path
1. Learning Loop processes outcomes
2. For each outcome, `compute_and_store_for_idea()` called
3. Feature value stored in `derived_feature_values`
4. Correlation monitoring updates `feature_experiments.correlation_cpa`
5. After 30 days: check if |correlation| >= 0.08 for promotion

## Metrics to Track
- Sample size growth over time
- Correlation with CPA
- Number of unique pairs discovered

## Notes
- Feature is in shadow mode - will not affect decisions
- Correlation monitoring already integrated via LearningLoopWorkflow
- Auto-deprecation after 30 days if correlation < 0.05
