# Pipeline Health Monitor - Cold Start Fix

## Problem
False "Decision Engine is DOWN" alerts triggered every 3 hours due to insufficient cold start wait time.

## Root Cause
- Render free tier cold start: **up to 85+ seconds**
- Workflow wait: **45 seconds** (insufficient)
- Result: Health check ran before DE fully started

## Fix
Updated `Wait for Cold Start` node from 45s to **90 seconds**.

## Edge Cases
- Very slow cold starts (>90s) may still trigger false alerts
- Consider adding retry logic if problem persists
- `keep_alive_decision_engine` workflow runs every 14 minutes to minimize cold starts

## Testing
- Curl to /health after cold start: 85.58s
- After fix: workflow correctly waits for DE startup

## Workflow
`Pipeline Health Monitor` (H1uuOanSy627H4kg)
