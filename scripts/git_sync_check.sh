#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_ROOT="${WORKSPACE_ROOT:-/opt/personal-agent-workspace}"
REMOTE="${1:-origin}"
BRANCH="${2:-master}"

cd "$WORKSPACE_ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: not inside a git work tree: $WORKSPACE_ROOT" >&2
  exit 2
fi

current_branch="$(git branch --show-current)"
if [[ "$current_branch" != "$BRANCH" ]]; then
  echo "WARN: current branch is '$current_branch', expected '$BRANCH'"
fi

echo "== workspace =="
echo "$WORKSPACE_ROOT"
echo

echo "== branch =="
git status --short --branch
echo

echo "== remote =="
git remote -v | sed -n '1,4p'
echo

git fetch "$REMOTE" "$BRANCH" --quiet

local_ref="HEAD"
remote_ref="$REMOTE/$BRANCH"

if ! git rev-parse --verify "$remote_ref" >/dev/null 2>&1; then
  echo "ERROR: remote ref not found: $remote_ref" >&2
  exit 2
fi

ahead="$(git rev-list --count "$remote_ref..$local_ref")"
behind="$(git rev-list --count "$local_ref..$remote_ref")"
dirty_count="$(git status --porcelain | wc -l | tr -d ' ')"

echo "== sync =="
echo "ahead:  $ahead"
echo "behind: $behind"
echo "dirty:  $dirty_count"
echo

if [[ "$dirty_count" != "0" ]]; then
  echo "ACTION: commit or intentionally ignore local changes before syncing."
  exit 1
fi

if [[ "$behind" != "0" && "$ahead" != "0" ]]; then
  echo "ACTION: repository diverged. Run: git pull --rebase $REMOTE $BRANCH"
  exit 1
fi

if [[ "$behind" != "0" ]]; then
  echo "ACTION: local branch is behind. Run: git pull --rebase $REMOTE $BRANCH"
  exit 1
fi

if [[ "$ahead" != "0" ]]; then
  echo "ACTION: local branch is ahead. Run: git push $REMOTE $BRANCH"
  exit 1
fi

echo "OK: local branch is clean and synced with $remote_ref."
