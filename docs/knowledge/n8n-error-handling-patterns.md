# n8n Error Handling Patterns

## onError Options

| Option | Behaviour |
|--------|-----------|
| `stopWorkflow` | Default. Workflow stops on error. |
| `continueRegularOutput` | Error ignored, continues with empty/error data in main output. |
| `continueErrorOutput` | Routes to error output (red connector). |

## Pattern: Handle HTTP Conflict (409)

При INSERT в Supabase с UNIQUE constraint — 409 Conflict.

```
HTTP Request (onError: continueRegularOutput)
    → IF ($json.id exists)
        ├─ true → success flow
        └─ false → handle duplicate/error
```

**Key:** Supabase returns `{"id": "uuid"}` on success, `{"code": "23505"}` on conflict.

## Pattern: Check Duplicate Before Insert

Альтернатива — проверить перед INSERT:

```
HTTP Request (SELECT where video_url=X AND tracker_id=Y)
    → IF (result.length > 0)
        ├─ true → already exists
        └─ false → INSERT
```

**Trade-off:** +1 запрос, но точнее определяет дубликат.

## Expression Format

Mixed literal + expression REQUIRES `=` prefix:

```javascript
// WRONG
"text": "Hello {{ $json.name }}"

// CORRECT
"text": "=Hello {{ $json.name }}"
```

## n8n_update_partial_workflow

Для добавления error handling:

```javascript
{type: "updateNode", nodeName: "HTTP Request", updates: {onError: "continueRegularOutput"}}
```

Для IF node routing:

```javascript
{type: "addConnection", source: "IF", target: "Success", branch: "true"}
{type: "addConnection", source: "IF", target: "Error", branch: "false"}
```
