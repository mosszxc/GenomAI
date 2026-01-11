# QA Notes: Issue #300 - Knowledge Extraction System

## Summary
System for extracting structured knowledge from training transcripts (YouTube courses on creative strategy) with Telegram-based review.

## Changes Made

### Database
- `knowledge_sources` - stores transcript sources
- `knowledge_extractions` - stores extracted knowledge items pending review

### New Files
| File | Purpose |
|------|---------|
| `temporal/activities/knowledge_extraction.py` | LLM extraction activity |
| `temporal/activities/knowledge_db.py` | DB operations for knowledge |
| `temporal/models/knowledge.py` | Dataclasses for workflows |
| `temporal/workflows/knowledge_ingestion.py` | Process transcript → extract → save |
| `temporal/workflows/knowledge_application.py` | Apply approved knowledge |
| `src/routes/knowledge.py` | API endpoints |

### Modified Files
| File | Change |
|------|--------|
| `main.py` | Added knowledge router |
| `temporal/worker.py` | Added knowledge worker |
| `temporal/config.py` | Added TASK_QUEUE_KNOWLEDGE |
| `src/routes/telegram.py` | Added /knowledge, file upload, callbacks |

## Testing

### API Test
```bash
curl -X POST https://genomai.onrender.com/api/knowledge/sources \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "content": "Sample transcript...", "source_type": "manual"}'
```

### DB Verification
```sql
SELECT * FROM genomai.knowledge_sources LIMIT 5;
SELECT * FROM genomai.knowledge_extractions WHERE status = 'pending' LIMIT 5;
```

### Telegram Test
1. Upload .txt file with transcript to bot
2. Use /knowledge to view pending extractions
3. Click Approve/Reject buttons

## Knowledge Types
| Type | Target | Example |
|------|--------|---------|
| `premise` | `premises` table | "The 72-Hour Reset Method" |
| `creative_attribute` | schema extension | New hook_mechanism value |
| `process_rule` | `config` table | "Always UMP before UMS" |
| `component_weight` | `component_learnings` | Component correlations |

## Flow
```
.txt file → Telegram → KnowledgeIngestionWorkflow → LLM extraction
→ pending extractions → /knowledge → Approve/Reject cards
→ KnowledgeApplicationWorkflow → premises/config/etc.
```

## Notes
- Only admin telegram IDs can use knowledge extraction
- Schema extensions (creative_attribute) require manual deployment
- Extracted premises start as "emerging" status (need market validation)
