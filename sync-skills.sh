#!/bin/bash
# Sync Skills to Workspace
#
# This script syncs CC skill directories to the unified workspace location.
# Run this after creating or updating skills to ensure CC and Codex share the same code.
#
# Usage: ./sync-skills.sh [skill-name]
# Example: ./sync-skills.sh ai-quiz

set -e

WORKSPACE="/opt/personal-agent-workspace"
CC_SKILLS="/root/cti-claude-home/.claude/skills"
WORKSPACE_SKILLS="${WORKSPACE}/skills"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Skill Sync to Workspace ===${NC}\n"

# If skill name provided, sync only that skill
if [ -n "$1" ]; then
    SKILLS=("$1")
else
    # Sync all skills
    SKILLS=($(ls -d ${CC_SKILLS}/*/ 2>/dev/null | xargs -I{} basename {}))
fi

for skill in "${SKILLS[@]}"; do
    SRC="${CC_SKILLS}/${skill}"
    DEST="${WORKSPACE_SKILLS}/${skill}"

    if [ ! -d "$SRC" ]; then
        echo -e "${YELLOW}⚠️  Skill '${skill}' not found in CC, skipping${NC}"
        continue
    fi

    # Create destination if needed
    mkdir -p "$(dirname "$DEST")"

    # Sync files (use rsync if available, otherwise cp)
    if command -v rsync &> /dev/null; then
        rsync -av --delete "$SRC/" "$DEST/"
    else
        cp -r "$SRC/"* "$DEST/" 2>/dev/null || true
    fi

    echo -e "${GREEN}✅ Synced: ${skill}${NC}"

    # Create symlink back to CC (optional, for CC to read from workspace)
    # Uncomment the following lines to enable symlinks:
    # rm -rf "$SRC"
    # ln -s "$DEST" "$SRC"
    # echo -e "   🔗 Symlink created: ${SRC} -> ${DEST}"
done

echo -e "\n${GREEN}=== Sync Complete ===${NC}"
echo -e "Workspace skills location: ${WORKSPACE_SKILLS}"
echo -e "\nTo enable symlinks (CC reads from workspace), edit this script and uncomment the symlink section."
