#!/bin/bash
# Helper script for creating issues with proper structure
# Usage: ./scripts/create-issue.sh

set -e

echo "=== GenomAI Issue Creator ==="
echo ""
echo "Type:"
echo "  1) Feature"
echo "  2) Task"
echo "  3) Bug"
read -p "Select [1-3]: " type_choice

case $type_choice in
  1) prefix="[FEATURE]"; label="enhancement" ;;
  2) prefix="[TASK]"; label="" ;;
  3) prefix="[BUG]"; label="bug" ;;
  *) echo "Invalid choice"; exit 1 ;;
esac

read -p "Title: " title
read -p "Description: " description
read -p "Blocked By (e.g. #123, #456): " blocked_by
read -p "Blocks (e.g. #789): " blocks
read -p "Related Issues (e.g. #111): " related
read -p "Sphere label (e.g. decision-engine): " sphere

body="## Description
${description}

---
## Dependencies

**Blocked By:** ${blocked_by:-None}
**Blocks:** ${blocks:-None}
**Related:** ${related:-None}

---
## Completion Summary
_Fill when closing_
"

labels=""
[[ -n "$label" ]] && labels="--label $label"
[[ -n "$sphere" ]] && labels="$labels --label sphere:$sphere"

gh issue create --title "$prefix $title" --body "$body" $labels

echo "Done!"
