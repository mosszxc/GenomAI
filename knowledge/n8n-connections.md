# n8n Connections Knowledge

## Connection Format

All n8n connections must use this format:

```json
"NodeName": {
  "main": [
    [  // Output 0
      {"node": "TargetNode", "type": "main", "index": 0}
    ],
    [  // Output 1 (for IF nodes, splitInBatches, etc.)
      {"node": "AnotherNode", "type": "main", "index": 0}
    ]
  ]
}
```

## Common Mistakes

### Wrong: Numeric keys

```json
"Loop Over Campaigns": {
  "1": [...]  // WRONG - should be "main"
}
```

### Wrong: Numeric type

```json
{"node": "Target", "type": "0", "index": 0}  // WRONG - should be "main"
```

## splitInBatches Node

splitInBatches has 2 outputs:
- **Output 0**: "Done" signal when all items processed
- **Output 1**: Current batch items for processing

Correct connection format:

```json
"Loop Over Campaigns": {
  "main": [
    [],  // Output 0 - empty or connect to "after loop" node
    [    // Output 1 - connect to processing node
      {"node": "Process Item", "type": "main", "index": 0}
    ]
  ]
}
```

## IF Node

IF node has 2 outputs:
- **Output 0**: True branch
- **Output 1**: False branch

```json
"Check Condition": {
  "main": [
    [{"node": "True Handler", "type": "main", "index": 0}],
    [{"node": "False Handler", "type": "main", "index": 0}]
  ]
}
```

## Debugging Connection Issues

1. **Check executedNodes count** - if less than expected, connection may be broken
2. **Use n8n_get_workflow mode:"structure"** to see current connections
3. **Compare with working workflows** - check connection format
4. **Use replaceConnections** to fix malformed connections

## Symptoms of Broken Connections

- Workflow shows "success" but expected nodes not executed
- Loop doesn't process items (splitInBatches → next node broken)
- IF branches not working (wrong output routing)

## Prevention

- Always validate workflow after manual edits
- Use MCP tools (addConnection, removeConnection) instead of manual JSON edits
- Check execution preview to verify all nodes execute

## Related Issues

- #186: Keitaro Poller broken connection Loop→GetMetrics
