# QA Notes: Issue #447 - CreativePipelineWorkflow decompose_creative fails in recovery mode

## Problem
Two issues were reported:
1. `decompose_creative` activity fails with "workflow execution already completed" during recovery
2. `get_import_by_campaign_id` fails to find import queue records

## Root Cause Analysis

### Problem 1: Recovery workflow conflicts
MaintenanceWorkflow was creating recovery workflows with unique IDs:
```python
id=f"recovery-{stuck['creative_id'][:8]}-{workflow.now().timestamp():.0f}"
```

This could cause conflicts when:
- Original workflow still running but detected as "stuck"
- Multiple recovery attempts for same creative

### Problem 2: Import queue lookup too strict
`get_import_by_campaign_id` only searched by exact `campaign_id + buyer_id` match.
If buyer_id didn't match (or was wrong), lookup failed.

## Fix Applied

### maintenance.py
- Changed workflow ID to match original: `creative-pipeline-{creative_id}`
- Added `WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY` - only restarts if previous FAILED
- Added exception handling for "already started" cases

### buyer.py (get_import_by_campaign_id)
- Step 1: Try exact match (campaign_id + buyer_id)
- Step 2: Fallback to campaign_id only
- Improved logging for debugging buyer_id mismatches

## Test Results

| Test | Result | Details |
|------|--------|---------|
| Syntax check | PASSED | `python3 -m py_compile` |
| Unit tests | PASSED | 157 tests passed |
| PR checks | PASSED | All 9 checks passed |
| Deploy | PASSED | Status: live |
| Health check | PASSED | HTTP 200, status: ok |

## Production Verification
- Deploy: `dep-d5ib481r0fns73e0q11g` - status: live
- Commit: `73f82d5997f2ba5e7240d9ea5b728e72bc17849a`
- Health: https://genomai.onrender.com/health - OK

## Follow-up
Full recovery test will occur at next MaintenanceWorkflow scheduled run (every 6 hours).
Monitor Temporal Cloud logs for:
- `workflow already running, skipping recovery` - expected for active workflows
- `Started recovery for creative` - successful recovery starts

## Files Changed
- `decision-engine-service/temporal/workflows/maintenance.py`
- `decision-engine-service/temporal/activities/buyer.py`

## PR
https://github.com/mosszxc/GenomAI/pull/454
