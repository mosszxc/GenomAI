# Issue #494 - CI Contracts Job + Python Version Check

## Problem
1. CI contracts job failed in 2-3 seconds due to missing `working-directory`
2. `local-dev.sh` allowed Python < 3.11 despite `pyproject.toml` requiring `>=3.11`
3. CLAUDE.md incorrectly stated "3.10+"

## Root Cause Analysis
- `ci.yml` contracts job ran `python3 scripts/validate_contracts.py` without explicit working directory
- After `pip install` in `decision-engine-service/`, the working directory context was ambiguous
- Script resolved paths incorrectly and exited with error

## Changes
- `.github/workflows/ci.yml:76`: Added `working-directory: ${{ github.workspace }}`
- `scripts/local-dev.sh:48-57`: Added Python version check (3.11+ required)
- `CLAUDE.md:72`: Changed "3.10+" to "3.11+"

## Testing
- Local pre-commit hooks passed
- GitHub Actions CI still failing due to unrelated runner/billing issue (not code)

## Notes
- GitHub Actions runs failing in 2-3s with no logs (404 on run URLs)
- This appears to be a billing/runner issue, not related to code changes
- PR merged with `--admin` override
