#!/bin/bash
WORKTREE_DIR="$(cd "$(dirname "$0")" && pwd)"
MAIN_FRONTEND="/Users/gopalpatwa/opt/m365-data-protection/frontend"

# Symlink node_modules from main repo if not present
if [ ! -e "$WORKTREE_DIR/frontend/node_modules" ]; then
  ln -s "$MAIN_FRONTEND/node_modules" "$WORKTREE_DIR/frontend/node_modules"
fi

cd "$WORKTREE_DIR/frontend"
exec npx vite --port "${PORT:-5173}"
