# /lz-summary

Synthesize everything from `/lz-readproject` and `/lz-discussion` into a doc outline
that the user approves **before** any writing begins.

No documents are written in this step. This is the blueprint stage.

---

## Why This Step Exists

Writing is cheap; planning is priceless. A 5-minute outline review catches misaligned
expectations that would otherwise waste 30 minutes of generation. Never skip this step.

---

## Outline Structure

For **each** topic in `user_interests`, produce one entry like this:

```markdown
### 📄 Doc N: <Title>

**Knowledge Point:** K{id}
**Discipline:** {discipline}
**Depth Level:** {A | B | C}

**Sections:**
1. **主要观点** (Core Idea) — 1–2 sentences that a smart non-expert can understand
2. **原理说明** (How It Works) — Mathematical / mechanical / computational derivation
3. **实际应用** (In This Project) — Where and how this appears in `{file_refs}`
4. **示例代码** (Code Example) — Runnable snippet demonstrating the concept *(if depth B or C)*
5. **相关概念** (Related Concepts) — 3–5 linked ideas with one-line descriptions
6. **参考资料** (References) — Will be fetched via web search during execution

**Estimated length:** {short: ~300w | medium: ~600w | long: ~1000w+}
**Depends on:** {other doc titles, if any}
```

---

## Presentation

Present all outlines together under a header:

```
## 📋 Knowledge Doc Outline

I'll create {N} document(s) based on our discussion:

[outline entries]

---

Does this look right? A few things you can ask me to change:
- Reorder the sections
- Add or remove a topic
- Change the depth of any doc
- Split one doc into two (for large topics)
- Merge two docs into one (for closely related topics)

When you're happy, run `/lz-execution` and I'll write everything.
```

---

## Approval Gate

**Do not proceed to `/lz-execution` without explicit user approval.**

Acceptable approval signals:
- "Looks good"
- "Go ahead"
- "执行" / "开始写" / "没问题"
- Any affirmative that refers to the outline

If the user modifies the outline, confirm the change: "Got it — I've updated Doc 2 to include
a section on numerical stability. Anything else before I start?"

---

## Handling Edge Cases

- **User wants only 1 doc**: That's fine. Don't force breadth.
- **User wants 6+ docs**: Warn that this is a large batch and suggest prioritizing 3 for now.
- **User wants a doc with no code** (depth A, non-computational topic): Remove the code section
  from that doc's outline, note it explicitly.
- **Conflicting depth levels** (e.g., K3 at depth A but K7 at depth C, and they share math):
  Note the dependency and ask if the user wants the shared math explained in one place.
