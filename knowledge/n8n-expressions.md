# n8n Expressions: Common Patterns and Gotchas

## Data Access Patterns

### HTTP Request Node Output
Supabase REST API возвращает массив, но n8n разворачивает его:

```javascript
// Supabase returns: [{field: "value"}]
// n8n transforms to: item.json = {field: "value"}

// ПРАВИЛЬНО:
$('HTTP Request').first().json.field

// НЕПРАВИЛЬНО (json это объект, не массив!):
$('HTTP Request').first().json[0]?.field  // → undefined
```

### Multiple Items
Если HTTP Request возвращает несколько записей:
```javascript
// Supabase returns: [{id: 1}, {id: 2}, {id: 3}]
// n8n создаёт 3 items

$('Node').first().json.id   // → 1 (первый item)
$('Node').last().json.id    // → 3 (последний item)
$('Node').all()             // → все items
```

## Expression Debugging

### Проверка структуры данных
1. Открыть execution в n8n UI
2. Кликнуть на node → вкладка "Output"
3. Смотреть JSON structure

### Common Mistakes

| Ошибка | Исправление |
|--------|-------------|
| `json[0].field` | `json.field` |
| `json.body.data` когда body это string | `JSON.parse(json.body).data` |
| `$json.field` в Code node | `$input.first().json.field` |

## Node-Specific Patterns

### Supabase via HTTP Request
```javascript
// GET single row (with ?limit=1)
$('Get Row').first().json.column_name

// GET multiple rows
$('Get Rows').all().map(item => item.json.id)

// POST/PATCH with return=representation
$('Insert').first().json.id  // ID созданной записи
```

### Referencing Upstream Nodes
```javascript
// По имени node (пробелы разрешены)
$('Webhook Zaliv Done').item.json.body.telegram_id

// Первый item
$('Node Name').first().json.field

// С optional chaining (безопаснее)
$('Node Name').first().json?.field || 'default'
```

## Testing Expressions

Перед deploy:
1. Использовать Expression Editor в n8n UI
2. Preview показывает реальные данные из последнего execution
3. Проверить edge cases: пустой массив, null, undefined
