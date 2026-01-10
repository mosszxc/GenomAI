# Issue #286: REST API for Temporal Schedules

## Test Results

### GET /api/schedules
```bash
curl -s https://genomai.onrender.com/api/schedules
```
**Result:** Returns list of 5 schedules with status, interval/cron, last_run, next_run

### GET /api/schedules/{id}
```bash
curl -s https://genomai.onrender.com/api/schedules/keitaro-poller
```
**Result:** Returns schedule details including paused state

### GET /api/schedules/{nonexistent}
```bash
curl -s https://genomai.onrender.com/api/schedules/nonexistent
```
**Result:** 404 "Schedule 'nonexistent' not found"

### POST /api/schedules/{id}/trigger (без ключа)
```bash
curl -s -X POST https://genomai.onrender.com/api/schedules/keitaro-poller/trigger
```
**Result:** 401 "Missing X-API-Key header"

## Implementation Notes

- `ScheduleListInfo` (from list) has limited attributes: `recent_actions`, `next_action_times`
- `ScheduleDescription` (from describe) has full info including `schedule.state.paused`
- Used `started_at` not `start_time` for recent_actions timestamp

## Files Changed

- `decision-engine-service/src/routes/schedules.py` - new router
- `decision-engine-service/main.py` - added router include
