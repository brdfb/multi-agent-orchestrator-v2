#!/usr/bin/env bash
set -euo pipefail

echo "Setting up project memory integration..."

# Ensure memory directories exist
mkdir -p ~/memory/{NOTES,HISTORY,BIN}

# Get project info
PROJECT_NAME=$(basename "$(pwd)")
PROJECT_PATH=$(pwd)

# Sync QUICKSTART.md to CORE_GUIDE if it exists
if [[ -f "QUICKSTART.md" ]]; then
    cp "QUICKSTART.md" ~/memory/CORE_GUIDE.md
    echo "✓ Synced QUICKSTART.md → ~/memory/CORE_GUIDE.md"
fi

# Add project to index
if [[ -x ~/memory/BIN/pm_add.sh ]]; then
    ~/memory/BIN/pm_add.sh "$PROJECT_NAME" "$PROJECT_PATH" "init"
else
    echo "⚠ Warning: ~/memory/BIN/pm_add.sh not found or not executable"
fi

echo "✓ Memory system initialized for project: $PROJECT_NAME"
echo "  - Index: ~/memory/INDEX.md"
echo "  - Notes: ~/memory/NOTES/${PROJECT_NAME}.notes"
echo "  - History: ~/memory/HISTORY/${PROJECT_NAME}.log"
