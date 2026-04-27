#!/bin/bash
# install-lz.sh
# Installs the LZ Knowledge System to Claude Code, Codex CLI, and Gemini CLI.
# Run from INSIDE the lz-knowledge directory:
#   chmod +x install-lz.sh && ./install-lz.sh

set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_BLURB='
## LZ Knowledge System
Commands: /lz-readproject | /lz-discussion | /lz-summary | /lz-execution
'

install_to() {
  local name="$1"
  local skills_dir="$2"
  local md_file="$3"

  mkdir -p "$skills_dir"
  cp -r "$SKILL_DIR" "$skills_dir/lz-knowledge"

  mkdir -p "$(dirname "$md_file")"
  touch "$md_file"

  if grep -q "LZ Knowledge System" "$md_file" 2>/dev/null; then
    echo "  ⚠️  Already installed in $md_file — skipping"
  else
    cat >> "$md_file" << EOF

---
## LZ Knowledge System
Skill: $skills_dir/lz-knowledge/SKILL.md
Commands: /lz-readproject | /lz-discussion | /lz-summary | /lz-execution
EOF
    echo "  ✅ $name → $md_file"
  fi
}

echo ""
echo "🔧 Installing LZ Knowledge System..."
echo ""

install_to "Claude Code"  "$HOME/.claude/skills"  "$HOME/.claude/CLAUDE.md"
install_to "Codex CLI"    "$HOME/.codex/skills"   "$HOME/.codex/AGENTS.md"
install_to "Gemini CLI"   "$HOME/.gemini/skills"  "$HOME/.gemini/GEMINI.md"

echo ""
echo "🎉 Done! Start any session and type /lz-readproject to begin."
echo ""
