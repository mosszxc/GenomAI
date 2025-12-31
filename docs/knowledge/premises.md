# Premises

Narrative vehicles for hypothesis generation. Premises add storytelling context to creatives.

## Table Schema

```sql
genomai.premises
├── id: uuid (PK, auto-generated)
├── premise_type: text (NOT NULL, constrained)
├── name: text (NOT NULL)
├── description: text
├── origin_story: text
├── mechanism_claim: text
├── source: text
├── status: text (default: 'emerging')
├── vertical: text
├── geo: text
├── created_at: timestamptz
└── updated_at: timestamptz
```

## Premise Types (constraint)

```sql
CHECK (premise_type IN (
  'method',
  'discovery',
  'confession',
  'secret',
  'ingredient',
  'mechanism',
  'breakthrough',
  'transformation'
))
```

## Status Values

| Status | Description |
|--------|-------------|
| `emerging` | New, not yet validated (default) |
| `active` | Validated, available for selection |
| `retired` | No longer in use |

## Usage in Hypothesis Factory

1. **Select Premise** node loads active premises from DB
2. **Prompt Assembly** randomly selects one premise
3. LLM receives premise context:
   - premise_type
   - name
   - origin_story
   - mechanism_claim
4. **Persist Hypotheses** saves `premise_id` to hypothesis

## Example Premises

```sql
INSERT INTO genomai.premises (premise_type, name, origin_story, mechanism_claim, status, vertical)
VALUES
  ('secret', 'Tibetan Monks Secret',
   'Discovered in a remote monastery by Dr. Chen during his 1987 expedition',
   'Activates the parasympathetic nervous system through specific breathwork patterns',
   'active', 'health'),
  ('breakthrough', 'Suppressed Stanford Study',
   'Published briefly in 1992 before being mysteriously retracted',
   'Natural compound X activates cellular regeneration pathways',
   'active', 'supplements');
```

## API Endpoints

- `POST /premise/select` - Select premise by filters (avatar_id, geo, vertical)
- Registered in `decision-engine-service/routers/premise.py`

## Workflow Integration

- **Hypothesis Factory** (`oxG1DqxtkTGCqLZi`): Uses Supabase node to load active premises
- **Premise Generator** (`x2Udd72hNe0ODduu`): Generates new premises via LLM (requires premise_learnings data)
- `hypotheses.premise_id` links to selected premise

## Seed Premises (11 total)

Migration 021 seeds these premises:

| Type | Name | Status |
|------|------|--------|
| method | Метод лимонной косточки | active |
| method | Метод гуавы | active |
| secret | Техника монахов | active |
| method | Домашний метод | active |
| discovery | Случайное открытие ученого | active |
| confession | Признание врача | active |
| ingredient | Один ингредиент | active |
| mechanism | Скрытая причина | active |
| secret | Tibetan Monks Secret | active |
| discovery | Hollywood Elite Method | active |
| breakthrough | Suppressed Stanford Study | active |

## Premise Generator Workflow

Workflow `x2Udd72hNe0ODduu` generates new premises based on winning examples.

**Requirements:**
- `premise_learnings` with `sample_size >= 5` must exist
- Called via webhook: `POST /webhook/premise-generate`

**Request body:**
```json
{
  "premise_type": "method",
  "vertical": "nutra",
  "geo": "RU",
  "count": 3
}
```

**Note:** Until Learning Loop populates `premise_learnings`, workflow returns error "No winning premises found".
