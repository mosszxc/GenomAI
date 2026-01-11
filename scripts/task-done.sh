#!/bin/bash
# Finish task: verify, create PR, merge, cleanup worktree
# Usage: ./scripts/task-done.sh <issue-number> [--process <name>] [--no-pr] [--skip-verify]

set -e

# Parse arguments
ISSUE_NUM=""
PROCESS=""
NO_PR=""
SKIP_VERIFY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --process)
            PROCESS="$2"
            shift 2
            ;;
        --no-pr)
            NO_PR="true"
            shift
            ;;
        --skip-verify)
            SKIP_VERIFY="true"
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

PROJECT_ROOT="$(git rev-parse --show-toplevel)"
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

if [ -z "$ISSUE_NUM" ]; then
    echo "Usage: $0 <issue-number> [--process <name>] [--no-pr] [--skip-verify]"
    echo ""
    echo "Options:"
    echo "  --process <name>  Process to verify with /rw and /valid"
    echo "  --no-pr           Skip PR creation"
    echo "  --skip-verify     Skip verification step (not recommended)"
    echo ""
    echo "Processes: decision-engine, learning-loop, hypothesis-factory, video-ingestion, keitaro-poller"
    echo ""
    echo "Active worktrees:"
    git worktree list
    exit 1
fi

# Find the worktree for this issue
WORKTREE_PATH=$(find "$WORKTREES_DIR" -maxdepth 1 -type d -name "issue-${ISSUE_NUM}-*" 2>/dev/null | head -1)

if [ -z "$WORKTREE_PATH" ] || [ ! -d "$WORKTREE_PATH" ]; then
    echo "Error: No worktree found for issue #$ISSUE_NUM"
    echo "Looking for: $WORKTREES_DIR/issue-${ISSUE_NUM}-*"
    exit 1
fi

# Get branch name
BRANCH_NAME=$(basename "$WORKTREE_PATH")

echo "=== Finishing task ==="
echo "Issue: #$ISSUE_NUM"
echo "Branch: $BRANCH_NAME"
echo "Worktree: $WORKTREE_PATH"

# Check for uncommitted changes in worktree
cd "$WORKTREE_PATH"
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "Warning: Uncommitted changes in worktree"
    git status --short
    echo ""
    read -p "Commit all changes? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git add -A
        git commit -m "feat: complete issue #$ISSUE_NUM"
    else
        echo "Aborting. Commit your changes first."
        exit 1
    fi
fi

# === PRE-MERGE CHECKS ===
if [ "$SKIP_VERIFY" != "true" ]; then
    echo ""
    echo "Running pre-merge checks (make ci)..."
    cd "$PROJECT_ROOT"
    if make ci; then
        echo "✓ Pre-merge checks passed"
    else
        echo ""
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║  ⛔ PRE-MERGE CHECKS FAILED                                  ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Fix the issues above, then re-run:"
        echo "  ./scripts/task-done.sh $ISSUE_NUM"
        echo ""
        echo "Or skip checks (not recommended):"
        echo "  ./scripts/task-done.sh $ISSUE_NUM --skip-verify"
        exit 1
    fi
    cd "$WORKTREE_PATH"
fi

# Push branch
echo ""
echo "Pushing branch..."
git push -u origin "$BRANCH_NAME"

# === VERIFICATION STEP ===
if [ "$SKIP_VERIFY" != "true" ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    VERIFICATION CHECKPOINT                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Before merging, complete the verification cycle in Claude:"
    echo ""

    if [ -n "$PROCESS" ]; then
        echo "  1. /rw $PROCESS --max-iterations 3 --completion-promise 'VERIFIED'"
        echo "  2. /valid $PROCESS"
    else
        echo "  1. /rw {process} --max-iterations 3 --completion-promise 'VERIFIED'"
        echo "  2. /valid {process}"
        echo ""
        echo "  Hint: use --process <name> to auto-fill commands"
    fi

    echo ""
    echo "  3. Check qa-notes/issue-${ISSUE_NUM}-*.md exists"
    echo "  4. Update knowledge/{topic}.md if needed"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Check for qa-notes (BLOCKING!)
    QA_NOTE=$(find "$PROJECT_ROOT/qa-notes" -name "*issue-${ISSUE_NUM}*" 2>/dev/null | head -1)
    if [ -z "$QA_NOTE" ]; then
        # Also check in worktree
        QA_NOTE=$(find "$WORKTREE_PATH/qa-notes" -name "*${ISSUE_NUM}*" 2>/dev/null | head -1)
    fi

    if [ -n "$QA_NOTE" ]; then
        echo "✓ qa-notes found: $(basename "$QA_NOTE")"

        # Check for lesson
        if grep -q "## Lesson" "$QA_NOTE" && ! grep -q "<!-- Заполни если" "$QA_NOTE"; then
            echo ""
            echo "📚 LESSON DETECTED in qa-notes!"
            echo "   → Add to LESSONS.md before completing"
        fi
    else
        echo ""
        echo "╔══════════════════════════════════════════════════════════════╗"
        echo "║  ⛔ BLOCKED: qa-notes/issue-${ISSUE_NUM}-*.md NOT FOUND      ║"
        echo "╚══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Create qa-notes before completing task:"
        echo "  qa-notes/issue-${ISSUE_NUM}-description.md"
        echo ""
        echo "Template:"
        echo "  # Issue #${ISSUE_NUM}: Title"
        echo "  ## Problem"
        echo "  ## Solution"
        echo "  ## Test Commands"
        echo "  ## Edge Cases"
        echo ""
        exit 1
    fi

    echo ""
    read -p "Verification complete? Continue to PR? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Paused. Run verification, then re-run:"
        echo "  ./scripts/task-done.sh $ISSUE_NUM --skip-verify"
        exit 0
    fi
fi

# Create PR if not --no-pr
if [ "$NO_PR" != "true" ]; then
    echo ""
    echo "Creating PR with auto-merge label..."
    PR_URL=$(gh pr create --title "Closes #$ISSUE_NUM" --body "Closes #$ISSUE_NUM" --head "$BRANCH_NAME" --label "auto-merge" 2>/dev/null || echo "")

    if [ -n "$PR_URL" ]; then
        echo "PR created: $PR_URL"
        echo ""
        echo "Auto-merge enabled: PR will merge automatically when checks pass."
        echo ""
        read -p "Merge PR now (skip auto-merge)? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Check for active deploy before merge (multi-agent coordination)
            if [ -n "$RENDER_API_KEY" ]; then
                echo "Checking for active deploy..."
                if ! "$PROJECT_ROOT/scripts/safe-deploy.sh" --check-only; then
                    echo "⚠️  Waiting for deploy to complete..."
                    sleep 180
                    "$PROJECT_ROOT/scripts/safe-deploy.sh" --check-only || true
                fi
            else
                echo "⚠️  RENDER_API_KEY not set. Skipping deploy check."
                echo "   Tip: export RENDER_API_KEY for multi-agent coordination"
            fi

            # Note: не используем --delete-branch т.к. мы в worktree
            # Ветка удаляется ниже через git worktree remove + git branch -d
            gh pr merge "$BRANCH_NAME" --squash
            echo "PR merged!"
        else
            echo "PR will auto-merge when checks pass."
        fi
    else
        echo "PR already exists or couldn't be created"
        # Add label to existing PR
        gh pr edit "$BRANCH_NAME" --add-label "auto-merge" 2>/dev/null || true
        gh pr view "$BRANCH_NAME" --web 2>/dev/null || true
    fi
fi

# Return to main project
cd "$PROJECT_ROOT"

# Cleanup current worktree
echo ""
echo "Cleaning up worktree..."
git worktree remove "$WORKTREE_PATH" --force 2>/dev/null || true
git branch -d "$BRANCH_NAME" 2>/dev/null || true

# Run full cleanup to catch any other merged worktrees
echo ""
echo "Running cleanup for other merged worktrees..."
"$PROJECT_ROOT/scripts/cleanup-worktrees.sh" 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Task #$ISSUE_NUM completed"
