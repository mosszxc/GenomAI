# Lessons Learned

База знаний из решённых issues. **Читай перед началом работы.**

---

## Schema Errors

| ID | Issue | Root Cause | Prevention Rule |
|----|-------|------------|-----------------|
| L001 | #272 | Wrong table (events vs event_log) | Verify table names: `docs/SCHEMA_REFERENCE.md` |
| L002 | #189 | Case sensitivity (approve vs APPROVE) | Check constraints before format assumptions |
| L003 | — | Generated columns (win_rate, avg_roi) | Never INSERT/UPDATE generated columns |

## Propagation Errors

| ID | Issue | Chain | Prevention |
|----|-------|-------|------------|
| L010 | #222,#226 | buyer_id: creative→decomposed→idea→hypothesis | Trace full data path before coding |

## Workflow Gotchas

| ID | Issue | Component | Gotcha |
|----|-------|-----------|--------|
| L020 | #268-270 | Temporal | Sandbox restrictions — use string activity names, not function refs |
| L021 | #210 | Render | Cold start = 50-90 sec, use keep_alive |
| L022 | — | Temporal | Activities must be in separate file from workflow |
| L023 | #256 | Temporal | No `datetime.utcnow()` in workflows — use `workflow.now()` |

## Anti-Patterns

| ID | Pattern | Better Approach | Token Save |
|----|---------|-----------------|------------|
| A001 | Multiple Edit for node positions | Single batch Edit via workflow_tools.py | 14k→15k total |
| A002 | Polling Render deploy (10x calls) | `sleep 180` then single check | 30k→5k |
| A003 | Search secrets in .env/Render | Ask user immediately | 15k→1k |
| A004 | Close issue without fresh test | Post-Task Loop checklist first | 20k→0 waste |
| A005 | Edit qa-notes/KNOWN_ISSUES 5+ times | One update per issue | 500k→20k |
| A006 | Say "done" + PR link without Post-Task Loop | qa-notes → knowledge → summary → THEN "done" | context loss |
| A007 | Work directly in main without worktree | `./scripts/task-start.sh {N}` → worktree → `task-done.sh` | PR review skip, risky deploys |
| A008 | Mark Post-Task Loop completed before checking all 4 items | TEST → qa-notes → docs check → summary → THEN completed | missed docs updates |

## Quick Lookup

| Symptom | Check Lesson |
|---------|--------------|
| "table not found" / "relation does not exist" | L001 |
| "constraint violation" / "check constraint" | L002 |
| "cannot insert into generated column" | L003 |
| "buyer_id is null" downstream | L010 |
| "activity not registered" / sandbox error | L020, L022 |
| Service unavailable after deploy | L021 |
| "RestrictedWorkflowAccessError" / "cannot access datetime" | L023 |

---

## How to Use

1. **Before coding:** `grep -i "keyword" LESSONS.md`
2. **After issue:** If discovered reusable pattern → add row to table
3. **Evolution:** After 20+ lessons → migrate to `lessons/` structure
