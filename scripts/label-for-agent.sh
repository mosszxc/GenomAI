#!/bin/bash
# Label bug issues for agent auto-fix
# Usage: ./scripts/label-for-agent.sh [--dry-run]
#
# Rules:
#   - Only MEDIUM bugs (skip CRITICAL, HIGH)
#   - No assignee
#   - Not already agent-ready or human-only

set -e

DRY_RUN=""
[ "$1" = "--dry-run" ] && DRY_RUN="true"

echo "=== Labeling bugs for agent ==="
[ -n "$DRY_RUN" ] && echo "(DRY RUN)"
echo ""

# Get open bugs without assignee
ISSUES=$(gh issue list \
    --label "bug" \
    --state open \
    --json number,title,labels,assignees \
    -L 100)

LABELED=0
SKIPPED=0

echo "$ISSUES" | python3 -c "
import sys, json

issues = json.load(sys.stdin)

for issue in issues:
    num = issue['number']
    title = issue['title']
    labels = [l['name'] for l in issue['labels']]
    assignees = issue.get('assignees', [])

    # Skip if has assignee
    if assignees:
        print(f'SKIP #{num}: has assignee')
        continue

    # Skip if already labeled
    if 'agent-ready' in labels or 'human-only' in labels or 'agent-failed' in labels:
        print(f'SKIP #{num}: already labeled')
        continue

    # Skip CRITICAL and HIGH
    title_upper = title.upper()
    if '[CRITICAL]' in title_upper or 'CRITICAL' in title_upper:
        print(f'SKIP #{num}: CRITICAL')
        continue
    if '[HIGH]' in title_upper:
        print(f'SKIP #{num}: HIGH')
        continue

    # This one is good
    print(f'LABEL #{num}: {title[:50]}')
" | while read -r line; do
    if [[ "$line" == LABEL* ]]; then
        NUM=$(echo "$line" | grep -oE '#[0-9]+' | tr -d '#')
        if [ -n "$DRY_RUN" ]; then
            echo "[DRY] Would label #$NUM"
        else
            gh issue edit "$NUM" --add-label "agent-ready"
            echo "✓ Labeled #$NUM"
        fi
        LABELED=$((LABELED + 1))
    else
        echo "$line"
        SKIPPED=$((SKIPPED + 1))
    fi
done

echo ""
echo "Done!"
