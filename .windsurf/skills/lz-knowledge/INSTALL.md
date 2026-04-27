# LZ Knowledge System — Installation Guide

Install once, use in any project. The system works by injecting the skill instructions
into each tool's context file. Pick your tool(s) below.

---

## Option A: Claude Code

Claude Code reads `CLAUDE.md` at the repo root (and `~/.claude/CLAUDE.md` globally).

### Per-project install (affects only this repo)

```bash
# From your project root:
cat >> CLAUDE.md << 'EOF'

---
## LZ Knowledge System

You have access to a 4-command knowledge documentation pipeline.
When the user runs any of these commands, read the skill file first:

  Skill location: ~/.claude/skills/lz-knowledge/SKILL.md

Commands:
  /lz-readproject  — Scan project, extract ≤10 knowledge points
  /lz-discussion   — Interactive dialogue to pick topics + depth
  /lz-summary      — Generate outline for user approval
  /lz-execution    — Write the knowledge documents

Always read the relevant reference file in
~/.claude/skills/lz-knowledge/references/ before executing each command.
EOF
```

### Global install (available in every project)

```bash
# Copy skill to Claude's global skills directory
mkdir -p ~/.claude/skills
cp -r /path/to/lz-knowledge ~/.claude/skills/

# Append to global CLAUDE.md
mkdir -p ~/.claude
cat >> ~/.claude/CLAUDE.md << 'EOF'

## LZ Knowledge System
Skill path: ~/.claude/skills/lz-knowledge/SKILL.md
Trigger on: /lz-readproject, /lz-discussion, /lz-summary, /lz-execution
EOF
```

### Verify

```bash
claude  # open Claude Code
# Then type: /lz-readproject
# Claude should acknowledge the skill and begin scanning
```

---

## Option B: OpenAI Codex CLI

Codex CLI reads `AGENTS.md` at the repo root and (if configured) a global agent file.

### Per-project install

```bash
cat >> AGENTS.md << 'EOF'

---
## LZ Knowledge System

You have access to a knowledge documentation pipeline with 4 slash commands.
The skill instructions live at: <absolute-path-to>/lz-knowledge/SKILL.md

When the user invokes a command, read the corresponding reference file:
- /lz-readproject → lz-knowledge/references/readproject.md
- /lz-discussion  → lz-knowledge/references/discussion.md
- /lz-summary     → lz-knowledge/references/summary.md
- /lz-execution   → lz-knowledge/references/execution.md

Use lz-knowledge/templates/knowledge-doc.md as the output template.
EOF
```

### Global install

Codex CLI supports a global `~/.codex/AGENTS.md`:

```bash
mkdir -p ~/.codex/skills
cp -r /path/to/lz-knowledge ~/.codex/skills/

cat >> ~/.codex/AGENTS.md << 'EOF'

## LZ Knowledge System
Skill: ~/.codex/skills/lz-knowledge/SKILL.md
Commands: /lz-readproject | /lz-discussion | /lz-summary | /lz-execution
EOF
```

### Verify

```bash
codex  # open Codex CLI in your project
# Type: /lz-readproject
```

---

## Option C: Gemini CLI

Gemini CLI reads `GEMINI.md` at the repo root and `~/.gemini/GEMINI.md` globally.

### Per-project install

```bash
cat >> GEMINI.md << 'EOF'

---
## LZ Knowledge System

Four-command pipeline for extracting and documenting technical knowledge from code.
Skill file: <absolute-path-to>/lz-knowledge/SKILL.md

Command routing:
- /lz-readproject  → read references/readproject.md, then scan the project
- /lz-discussion   → read references/discussion.md, then start dialogue
- /lz-summary      → read references/summary.md, then produce outline
- /lz-execution    → read references/execution.md, then write docs

Output template: lz-knowledge/templates/knowledge-doc.md
State file: .lz-state.md (create in project root)
EOF
```

### Global install

```bash
mkdir -p ~/.gemini/skills
cp -r /path/to/lz-knowledge ~/.gemini/skills/

cat >> ~/.gemini/GEMINI.md << 'EOF'

## LZ Knowledge System
Skill: ~/.gemini/skills/lz-knowledge/SKILL.md
Commands: /lz-readproject | /lz-discussion | /lz-summary | /lz-execution
EOF
```

### Verify

```bash
gemini  # open Gemini CLI
# Type: /lz-readproject
```

---

## One-liner: Install to All Three

```bash
#!/bin/bash
# install-lz.sh — run from the lz-knowledge directory

SKILL_DIR=$(pwd)

# Claude Code
mkdir -p ~/.claude/skills
cp -r "$SKILL_DIR" ~/.claude/skills/lz-knowledge
cat >> ~/.claude/CLAUDE.md << EOF

## LZ Knowledge System
Skill: ~/.claude/skills/lz-knowledge/SKILL.md
Commands: /lz-readproject | /lz-discussion | /lz-summary | /lz-execution
EOF

# Codex CLI
mkdir -p ~/.codex/skills
cp -r "$SKILL_DIR" ~/.codex/skills/lz-knowledge
mkdir -p ~/.codex
cat >> ~/.codex/AGENTS.md << EOF

## LZ Knowledge System
Skill: ~/.codex/skills/lz-knowledge/SKILL.md
Commands: /lz-readproject | /lz-discussion | /lz-summary | /lz-execution
EOF

# Gemini CLI
mkdir -p ~/.gemini/skills
cp -r "$SKILL_DIR" ~/.gemini/skills/lz-knowledge
cat >> ~/.gemini/GEMINI.md << EOF

## LZ Knowledge System
Skill: ~/.gemini/skills/lz-knowledge/SKILL.md
Commands: /lz-readproject | /lz-discussion | /lz-summary | /lz-execution
EOF

echo "✅ LZ Knowledge System installed to Claude Code, Codex CLI, and Gemini CLI"
```

```bash
chmod +x install-lz.sh && ./install-lz.sh
```

---

## Uninstall

Remove the skill directory and delete the lines added to each `*MD` file:

```bash
rm -rf ~/.claude/skills/lz-knowledge
rm -rf ~/.codex/skills/lz-knowledge
rm -rf ~/.gemini/skills/lz-knowledge
# Then manually remove the ## LZ Knowledge System blocks from each *MD file
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Command not recognized | Check the `*MD` file has the correct absolute path to SKILL.md |
| References not found | Verify `lz-knowledge/references/` was copied alongside `SKILL.md` |
| State lost between sessions | Create `.lz-state.md` manually in project root; agent will update it |
| Wrong language in output | Add "Respond in Chinese" to your `*MD` file or ask agent inline |
