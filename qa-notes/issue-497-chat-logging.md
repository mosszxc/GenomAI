# Issue #497: Add full chat logging to buyer_onboarding workflow

## Summary
Added comprehensive logging of all Telegram interactions during buyer onboarding to `buyer_interactions` table.

## Changes
- **File**: `decision-engine-service/temporal/activities/buyer.py`
  - Added `LogInteractionInput` dataclass
  - Added `log_buyer_interaction` activity

- **File**: `decision-engine-service/temporal/workflows/buyer_onboarding.py`
  - Added `_log_outgoing(message, step)` helper
  - Added `_log_incoming(message, step)` helper
  - Added logging after every `send_telegram_message` call
  - Added logging after every user message received

- **File**: `decision-engine-service/temporal/worker.py`
  - Registered `log_buyer_interaction` activity

## Logged Steps
| Step | Direction | Message Type |
|------|-----------|--------------|
| welcome | out | bot |
| name_input | in | user |
| ask_geo | out | bot |
| geo_input | in | user |
| invalid_geo | out | bot |
| ask_vertical | out | bot |
| vertical_input | in | user |
| invalid_vertical | out | bot |
| ask_keitaro | out | bot |
| sub10_input | in | user |
| validating_sub10 | out | bot |
| sub10_found | out | bot |
| sub10_not_found | out | bot |
| sub10_retries_exhausted | out | bot |
| loading_history | out | bot |
| ask_videos_intro | out | bot |
| ask_campaign_video_N | out | bot |
| video_input_N | in | user |
| video_received_N | out | bot |
| invalid_video_url_N | out | bot |
| no_campaigns | out | bot |
| completed | out | bot |
| welcome_back | out | bot |
| timeout | out | bot |

## Context Stored
Each interaction includes:
- `telegram_id`: User's Telegram ID
- `direction`: "in" or "out"
- `message_type`: "bot" or "user"
- `content`: Message text (truncated to 2000 chars)
- `context`: `{"step": "step_name", "state": "current_state"}`
- `buyer_id`: Buyer UUID (if available)

## Tests
- Unit tests: PASSED
- Syntax check: PASSED
- Pre-commit hooks: PASSED

## Production Test
- Type: Workflow (requires real Telegram interaction)
- Will be verified after deploy by onboarding a new buyer
