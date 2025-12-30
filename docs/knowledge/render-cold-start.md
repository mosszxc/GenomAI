# Render Free Tier Cold Start

## Key Facts
- Free tier instances spin down after 15 min inactivity
- Cold start: **50-90 seconds** (measured 85s on 2025-12-30)
- First request triggers spin-up, subsequent requests fast

## Mitigations

### 1. Keep-Alive Workflow
`keep_alive_decision_engine` (ClXUPP2IvWRgu99y) pings /health every 14 minutes.

### 2. Wake-Before-Check Pattern
Any workflow checking DE health should:
1. Send initial request to /health (triggers cold start)
2. Wait 90+ seconds
3. Send actual health check

Example in `Pipeline Health Monitor`:
```
Wake Up DE → Wait 90s → Check DE Health
```

### 3. Timeouts
- Wake-up request: 5s timeout (expected to fail during cold start)
- Real health check: 30s timeout
- Always use `continueOnFail: true` on wake-up

## Related Workflows
- `Pipeline Health Monitor` (H1uuOanSy627H4kg)
- `keep_alive_decision_engine` (ClXUPP2IvWRgu99y)
