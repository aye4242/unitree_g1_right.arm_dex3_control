# /lz-execution

Write the approved knowledge documents. One file per topic.
Do not improvise structure — follow the approved outline from `/lz-summary` exactly.

---

## Pre-flight Checklist

Before writing a single word, verify:
- [ ] Approved outline exists in session state
- [ ] Output directory is known (default: `./lz-docs/` in project root, or ask user)
- [ ] Web search is available for references section
- [ ] File write access confirmed (or will display inline if not)

---

## Writing Each Document

Process docs in dependency order (if Doc B depends on Doc A, write A first).

For each document, follow this pipeline:

### Phase 1: Research (before writing)

Run web search queries for the references section *first*. This informs the writing.

```
Search queries to run:
1. "{topic title} explained" — for intuition sources
2. "{topic title} {discipline}" — for domain-specific material
3. "{topic title} tutorial" OR "{topic title} implementation" — for code references
4. Original paper / spec name if known
```

Collect 3–5 credible sources. Prioritize:
- Official documentation
- Peer-reviewed papers (arXiv, IEEE, ACM)
- Authoritative textbooks (cited online)
- High-quality engineering blogs (Towards Data Science, robotics.org, etc.)

### Phase 2: Write the document

Use `templates/knowledge-doc.md` as the file template. Fill every section.

**Section-by-section guidance:**

#### 主要观点 (Core Idea)
- Max 2 sentences
- No jargon in the first sentence
- Second sentence can introduce the key technical term
- Example: "Kalman filtering is a method for estimating the true state of a noisy system
  in real time. It combines predictions from a dynamic model with measurements from sensors,
  weighting each by how much we trust them."

#### 原理说明 (How It Works)
- Scale to depth level:
  - **Depth A**: Conceptual walkthrough, no equations required, use diagrams (ASCII or Mermaid)
  - **Depth B**: Include key equations with notation explained inline; derive the core result
  - **Depth C**: Full derivation, discuss assumptions, edge cases, numerical considerations
- Use step-by-step structure for algorithms
- For control/math content: define all symbols before using them

#### 实际应用 (In This Project)
- Reference specific files and line numbers from the project
- Explain what role this concept plays in the overall system
- If the project implements it imperfectly or partially, note that honestly
- Format:
  ```
  In this project, [concept] appears in `path/to/file.py` (lines ~N–M).
  The function `foo()` implements [specific part], while `bar()` handles [other part].
  The design choice to use [variant] over [alternative] was likely made because [reason].
  ```

#### 示例代码 (Code Example)
- Skip entirely if depth A or topic is non-computational
- Write **minimal, runnable** code (not copy-pasted from project)
- Always include:
  - A comment block at the top explaining what the snippet demonstrates
  - Inline comments on non-obvious lines
  - A sample input and expected output in a comment or doctest
- Languages: match project language; Python preferred for cross-disciplinary readability
- Max ~50 lines; if more is needed, split into labeled parts

#### 相关概念 (Related Concepts)
- List 3–5 concepts
- Format: `**Concept Name** — one-line description and relationship to this topic`
- Include at least one "simpler prerequisite" and one "natural next step"

#### 参考资料 (References)
- Use the search results from Phase 1
- Format:
  ```markdown
  1. [Title](URL) — one-line annotation on why this source is useful
  2. ...
  ```
- Minimum 3 references. Maximum 8.
- Never fabricate URLs. Only cite sources you actually found via search.

---

## Output

Save each document as:
```
./lz-docs/{slug}.md
```
where `{slug}` is the topic title lowercased with hyphens (e.g., `kalman-filter-state-estimation.md`).

After all documents are written, print a completion summary:

```
## ✅ Knowledge Docs Generated

| File | Topic | Length |
|---|---|---|
| `lz-docs/kalman-filter.md` | Kalman Filter: State Estimation | ~650 words |
| `lz-docs/inverse-kinematics.md` | Inverse Kinematics: Arm Control | ~800 words |

All docs saved to `./lz-docs/`.

Want to refine any of these? You can ask me to:
- Expand a section
- Add more code examples
- Translate to Chinese / English
- Export as PDF or DOCX
```

---

## Quality Gate (self-review before saving)

Before saving each doc, verify:
- [ ] Every section from the outline is present
- [ ] No section says "TODO" or is empty
- [ ] All code snippets are syntactically valid (mentally trace them)
- [ ] All references have real URLs (from search results)
- [ ] The "In This Project" section references actual files from the project
- [ ] Depth level is respected (no derivations in depth-A docs)
