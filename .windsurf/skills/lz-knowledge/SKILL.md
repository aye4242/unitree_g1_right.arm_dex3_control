---
name: lz-knowledge
description: >
  A meta-prompting system for turning any codebase into deep, structured knowledge documentation.
  Activate this skill whenever the user runs /lz-readproject, /lz-discussion, /lz-summary, or /lz-execution.
  Also trigger when the user says things like "读一下这个项目", "帮我整理知识点", "我想学习这个项目里的算法",
  "generate knowledge docs from this project", or any variant of wanting to understand and document
  the technical concepts hidden inside a codebase. Don't wait to be asked twice — if the project
  context is present and the user seems curious about the underlying principles, suggest starting with /lz-readproject.
---

# LZ Knowledge System

**LZ（了知）** — A lightweight pipeline for extracting, discussing, and documenting the algorithms
and domain knowledge buried inside any technical project.

```
/lz-readproject  →  /lz-discussion  →  /lz-summary  →  /lz-execution
     扫描               对话               大纲               生成
```

The four commands form a linear pipeline, but you can jump in at any stage.
Each stage builds on the last. See `references/` for detailed instructions per command.

---

## Quick Reference

| Command | What happens | Output |
|---|---|---|
| `/lz-readproject` | Scan project files, extract ≤10 knowledge points | Numbered knowledge map |
| `/lz-discussion` | Interactive dialogue to narrow focus | User's prioritized interest list |
| `/lz-summary` | Generate doc outline for user review | Structured outline, pending approval |
| `/lz-execution` | Write the full knowledge documents | Markdown `.md` files, one per topic |

---

## Core Principles

1. **Skim broad, dive deep** — `/lz-readproject` casts a wide net; later stages focus the beam.
2. **User drives depth** — Never write a doc without knowing which disciplines the user cares about.
3. **Every doc is self-contained** — Each knowledge document must make sense without the others.
4. **Code is optional but preferred** — Include runnable snippets whenever the concept has a
   computable form.
5. **Always cite** — Use web search for references. No bare claims.

---

## Command Details

Read the relevant reference file before executing each command:

- `/lz-readproject` → `references/readproject.md`
- `/lz-discussion`  → `references/discussion.md`
- `/lz-summary`     → `references/summary.md`
- `/lz-execution`   → `references/execution.md`

The knowledge document template lives at `templates/knowledge-doc.md`.

---

## State Management

Persist session state between commands by maintaining a block like this in your working memory
(or write it to `.lz-state.md` in the project root if you have filesystem access):

```yaml
# .lz-state.md
project_path: <path>
scan_date: <ISO date>
knowledge_points:        # populated by /lz-readproject
  - id: K1
    title: "..."
    category: robotics | cs | mechanical | math | control | other
    file_refs: [...]
user_interests:          # populated by /lz-discussion
  - K3
  - K7
approved_outline:        # populated by /lz-summary
  - topic: "..."
    sections: [...]
generated_docs: []       # populated by /lz-execution
```

---

## Installation

See `install/INSTALL.md` for step-by-step setup in Claude Code, Codex CLI, and Gemini CLI.
