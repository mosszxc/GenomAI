#!/bin/bash
# Create QA notes file with template for an issue
# Usage: ./scripts/create-qa-notes.sh <issue-number> [description]

set -e

ISSUE_NUM="$1"
DESCRIPTION="$2"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number> [description]"
    echo ""
    echo "Examples:"
    echo "  $0 275 'event table fix'"
    echo "  $0 276"
    exit 1
fi

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
QA_NOTES_DIR="$PROJECT_ROOT/qa-notes"

# Generate filename
if [ -n "$DESCRIPTION" ]; then
    # Convert description to kebab-case
    SLUG=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd 'a-z0-9-')
    FILENAME="issue-${ISSUE_NUM}-${SLUG}.md"
else
    FILENAME="issue-${ISSUE_NUM}.md"
fi

FILEPATH="$QA_NOTES_DIR/$FILENAME"

# Check if file already exists
if [ -f "$FILEPATH" ]; then
    echo "File already exists: $FILEPATH"
    echo "Opening existing file..."
    cat "$FILEPATH"
    exit 0
fi

# Get issue title from GitHub (if available)
ISSUE_TITLE=""
if command -v gh &> /dev/null; then
    ISSUE_TITLE=$(gh issue view "$ISSUE_NUM" --json title --jq '.title' 2>/dev/null || echo "")
fi

if [ -z "$ISSUE_TITLE" ]; then
    ISSUE_TITLE="[Issue Title]"
fi

# Create QA notes with template
cat > "$FILEPATH" << EOF
# Issue #${ISSUE_NUM}: ${ISSUE_TITLE}

## Problem
<!-- What was broken / what needed to be done -->


## Solution
<!-- What was changed to fix it -->


## Files Changed
<!-- List of modified files -->
-

## Test Commands
\`\`\`bash
# How to verify the fix works
\`\`\`

## Edge Cases
<!-- Any non-obvious scenarios or gotchas -->
-

## Verification
- [ ] Test executed (not just validated)
- [ ] Result verified (data in DB / HTTP 200 / etc)

## PR
<!-- Link to pull request -->

## Lesson (if applicable)
<!-- Заполни если issue выявил reusable pattern -->
<!-- Format: [Category] Root cause → Prevention rule -->
<!-- Затем добавь в LESSONS.md -->
EOF

echo "Created: $FILEPATH"
echo ""
echo "Template:"
cat "$FILEPATH"
