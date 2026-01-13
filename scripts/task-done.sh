#!/bin/bash
# Finish task: commit, push, create PR, wait for CI, merge, close issue
# Usage: ./scripts/task-done.sh <issue-number> [--no-pr] [--no-merge] [--skip-tests]

set -e

# Parse arguments
ISSUE_NUM=""
NO_PR=""
NO_MERGE=""
SKIP_TESTS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-pr)
            NO_PR="true"
            shift
            ;;
        --no-merge)
            NO_MERGE="true"
            shift
            ;;
        --skip-tests)
            SKIP_TESTS="true"
            shift
            ;;
        *)
            if [ -z "$ISSUE_NUM" ]; then
                ISSUE_NUM="$1"
            fi
            shift
            ;;
    esac
done

# Find main repo root (not worktree root)
CURRENT_ROOT="$(git rev-parse --show-toplevel)"
if [[ "$CURRENT_ROOT" == */.worktrees/* ]]; then
    PROJECT_ROOT="${CURRENT_ROOT%/.worktrees/*}"
else
    PROJECT_ROOT="$CURRENT_ROOT"
fi
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number> [--no-pr] [--no-merge] [--skip-tests]"
    echo ""
    echo "Options:"
    echo "  --no-pr       Skip PR creation and merge"
    echo "  --no-merge    Create PR with auto-merge label (merges after CI)"
    echo "  --skip-tests  Skip pre-merge tests"
    echo ""
    echo "Active worktrees:"
    git worktree list
    exit 1
fi

# Find the worktree for this issue
WORKTREE_PATH=$(find "$WORKTREES_DIR" -maxdepth 1 -type d -name "issue-${ISSUE_NUM}-*" 2>/dev/null | head -1)

if [ -z "$WORKTREE_PATH" ] || [ ! -d "$WORKTREE_PATH" ]; then
    echo "Error: No worktree found for issue #$ISSUE_NUM"
    exit 1
fi

BRANCH_NAME=$(basename "$WORKTREE_PATH")

echo "=== Finishing task ==="
echo "Issue: #$ISSUE_NUM"
echo "Branch: $BRANCH_NAME"

# Check for uncommitted changes
cd "$WORKTREE_PATH"
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "Committing changes..."
    git add -A
    git commit -m "feat: complete issue #$ISSUE_NUM

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
fi

# Check qa-notes exists
QA_NOTE=$(find "$PROJECT_ROOT/qa-notes" -name "*issue-${ISSUE_NUM}*" 2>/dev/null | head -1)
if [ -z "$QA_NOTE" ]; then
    QA_NOTE=$(find "$WORKTREE_PATH/qa-notes" -name "*${ISSUE_NUM}*" 2>/dev/null | head -1)
fi

if [ -z "$QA_NOTE" ]; then
    echo ""
    echo "⚠️  qa-notes/issue-${ISSUE_NUM}-*.md not found"
    echo "Create qa-notes with ## Test section before completing."
    exit 1
fi
echo "✓ qa-notes found: $(basename "$QA_NOTE")"

# Run tests unless skipped
if [ "$SKIP_TESTS" != "true" ]; then
    # Find dynamic FastAPI port from pid file
    echo ""
    echo "=== Pre-flight Checks ==="
    FASTAPI_PORT=""
    shopt -s nullglob
    for pf in /tmp/genomai-dev/server-*.pid; do
        [ -f "$pf" ] && FASTAPI_PORT=$(basename "$pf" .pid | sed 's/server-//')
    done

    if [ -z "$FASTAPI_PORT" ]; then
        echo "⚠️  FastAPI not running (no pid file found)"
        echo ""
        echo "Start the server first:"
        echo "  make up"
        echo ""
        echo "Or skip tests with --skip-tests flag"
        exit 1
    fi

    if ! curl -sf "http://localhost:${FASTAPI_PORT}/health" >/dev/null 2>&1; then
        echo "⚠️  FastAPI not responding on localhost:${FASTAPI_PORT}"
        echo ""
        echo "Restart the server:"
        echo "  make down && make up"
        echo ""
        echo "Or skip tests with --skip-tests flag"
        exit 1
    fi
    echo "✓ localhost:${FASTAPI_PORT} is healthy"
    export FASTAPI_PORT

    # Extract and run functional test from qa-notes
    echo ""
    echo "=== Functional Test ==="

    # Extract test command from qa-notes (between ```bash and ``` after ## Test)
    TEST_BLOCK=$(sed -n '/^## Test/,/^## /p' "$QA_NOTE" | sed -n '/```bash/,/```/p' | grep -v '```')
    TEST_CMD=$(echo "$TEST_BLOCK" | head -5)

    if [ -z "$TEST_CMD" ]; then
        echo "⚠️  No test command found in qa-notes"
        echo ""
        echo "Expected format in $(basename "$QA_NOTE"):"
        echo "  ## Test"
        echo "  \`\`\`bash"
        echo "  curl -sf localhost:\$FASTAPI_PORT/endpoint || echo 'OK'"
        echo "  \`\`\`"
        echo ""
        echo "Actual content:"
        cat "$QA_NOTE" | head -30
        exit 1
    fi

    # Substitute port placeholder (supports both $FASTAPI_PORT and hardcoded 10000)
    TEST_CMD=$(echo "$TEST_CMD" | sed "s/localhost:10000/localhost:${FASTAPI_PORT}/g")
    TEST_CMD=$(echo "$TEST_CMD" | sed "s/\\\$FASTAPI_PORT/${FASTAPI_PORT}/g")

    echo "Command: $TEST_CMD"
    echo ""

    cd "$WORKTREE_PATH"
    if eval "$TEST_CMD"; then
        echo ""
        echo "✓ Functional test passed"
    else
        echo ""
        echo "✗ Functional test failed"
        exit 1
    fi

    # Then unit tests
    echo ""
    echo "=== Unit Tests ==="
    if ! make -C "$WORKTREE_PATH" test-unit; then
        echo "Unit tests failed. Fix issues and re-run."
        exit 1
    fi
    echo "✓ All tests passed"
    cd "$WORKTREE_PATH"
fi

# Update issue status
echo ""
echo "Updating issue status..."
gh issue edit "$ISSUE_NUM" --add-label "status:pending-deploy" --remove-label "status:in-progress" 2>/dev/null || true

# Sync with develop before push (avoid merge conflicts)
echo ""
echo "Syncing with develop..."
git fetch origin develop
if ! git rebase origin/develop; then
    echo "⚠️  Rebase conflict detected"
    echo ""
    echo "Resolve conflicts and run again:"
    echo "  git rebase --continue"
    echo "  ./scripts/task-done.sh $ISSUE_NUM"
    exit 1
fi
echo "✓ Branch synced with develop"

# Push branch
echo ""
echo "Pushing branch..."
git push -u origin "$BRANCH_NAME" --force-with-lease

# Create PR to develop
PR_NUMBER=""
if [ "$NO_PR" != "true" ]; then
    echo ""
    echo "Creating PR to develop..."

    # Generate PR title and body from qa-notes
    PR_TITLE=$(head -1 "$QA_NOTE" | sed 's/^# //' | head -c 60)
    if [ -z "$PR_TITLE" ]; then
        PR_TITLE="Closes #$ISSUE_NUM"
    else
        PR_TITLE="$PR_TITLE (#$ISSUE_NUM)"
    fi

    # Extract "Что изменено" section for PR body
    PR_BODY=$(sed -n '/^## Что изменено/,/^## /p' "$QA_NOTE" | grep -v '^## ' | head -10)
    if [ -z "$PR_BODY" ]; then
        PR_BODY="Closes #$ISSUE_NUM"
    else
        PR_BODY="$PR_BODY

Closes #$ISSUE_NUM"
    fi

    PR_URL=$(gh pr create \
        --title "$PR_TITLE" \
        --body "$PR_BODY" \
        --head "$BRANCH_NAME" \
        --base develop \
        2>/dev/null || echo "")

    if [ -n "$PR_URL" ]; then
        echo "PR created: $PR_URL"
        PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')
    else
        echo "PR already exists, getting PR number..."
        PR_NUMBER=$(gh pr view "$BRANCH_NAME" --json number -q '.number' 2>/dev/null || echo "")
        if [ -n "$PR_NUMBER" ]; then
            echo "Found existing PR #$PR_NUMBER"
        fi
    fi

    # Add auto-merge label if --no-merge flag is set
    if [ "$NO_MERGE" = "true" ] && [ -n "$PR_NUMBER" ]; then
        gh pr edit "$PR_NUMBER" --add-label "auto-merge"
        echo "✓ Label 'auto-merge' added. PR will merge automatically after CI."
    fi
fi

# Wait for CI and merge
if [ "$NO_PR" != "true" ] && [ "$NO_MERGE" != "true" ] && [ -n "$PR_NUMBER" ]; then
    echo ""
    echo "=== Waiting for CI ==="
    # Wait for CI to start (GitHub needs a few seconds)
    echo "Waiting for CI to start..."
    sleep 5

    # Retry up to 3 times if no checks yet
    for i in 1 2 3; do
        if gh pr checks "$PR_NUMBER" --watch 2>/dev/null; then
            echo "✓ CI checks passed"
            break
        else
            if [ $i -lt 3 ]; then
                echo "CI not ready, retrying in 10s... ($i/3)"
                sleep 10
            else
                echo "✗ CI checks failed or not available"
                exit 1
            fi
        fi
    done

    # Close issue immediately after CI passes (before merge attempt)
    echo ""
    echo "=== Closing issue ==="
    gh issue close "$ISSUE_NUM" --comment "Fixed in PR #$PR_NUMBER" 2>/dev/null || true
    echo "✓ Issue #$ISSUE_NUM closed"

    echo ""
    echo "=== Merging PR ==="
    if gh pr merge "$PR_NUMBER" --squash --delete-branch; then
        echo "✓ PR #$PR_NUMBER merged"
    else
        echo "Trying auto-merge..."
        gh pr merge "$PR_NUMBER" --squash --delete-branch --auto || true
    fi
fi

cd "$PROJECT_ROOT"
echo ""
echo "=== Done ==="
if [ "$NO_MERGE" = "true" ]; then
    echo "PR created with auto-merge label. Will merge automatically after CI."
else
    echo "Issue #$ISSUE_NUM completed and merged to develop."
fi
echo "Run ./scripts/deploy.sh when ready to deploy to production."
