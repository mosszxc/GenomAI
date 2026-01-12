# Issue #499: BuyerOnboardingInput telegram_id backward compatibility

## Problem
Tu onboarding workflow stuck - Temporal worker failed with:
```
TypeError: Failed converting field telegram_id on dataclass <class 'temporal.models.buyer.BuyerOnboardingInput'>
RuntimeError: Failed decoding arguments
```

## Root Cause
Type of `telegram_id` was changed from `int` to `str` in `BuyerOnboardingInput` model.
Temporal serializes workflow arguments at start time. When worker restarted with new model,
it couldn't deserialize old `int` value into new `str` type.

## Solution
Changed `telegram_id` type to `Union[str, int]` for backward compatibility:
```python
telegram_id: Union[str, int]  # Accept both for Temporal backward compat

def __post_init__(self):
    self.telegram_id = str(self.telegram_id)  # Normalize to str
```

## Files Changed
- `temporal/models/buyer.py` - Union type for telegram_id
- `LESSONS.md` - Added L024 lesson

## Verification
- Worker logs: No deserialization errors after deploy
- Deploy status: `live` at 12:29:11 UTC

## Notes
- Tu's original workflow likely timed out (step_timeout=60min)
- Tu may need to restart onboarding or receive manual completion message
- Future type changes in Temporal Input models MUST use Union for backward compat

## Lesson Added
L024: Type changes in workflow Input models break running workflows.
Use `Union[old, new]` for backward compat. Temporal deserializer fails BEFORE `__post_init__`.
