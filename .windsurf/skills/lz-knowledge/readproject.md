# /lz-readproject

Scan the project and surface the algorithms and domain knowledge it contains.
Produce a numbered knowledge map with ≤ 10 items.

---

## Step-by-Step

### 1. Locate entry points

Start from the project root. Prioritize in this order:
- `README.md` / `README.rst` — project intent and architecture overview
- Source files: `.py`, `.cpp`, `.ts`, `.rs`, `.go`, `.java`, `.m` (MATLAB), `.urdf`, `.xacro`
- Config files: `CMakeLists.txt`, `package.xml`, `pyproject.toml`, `Cargo.toml`
- Notebooks: `.ipynb`
- Any file with "algorithm", "model", "controller", "planner", "solver" in its name

If the user has not specified a path, ask: "Please share the project path or paste key files."

### 2. Read strategically

Do **not** read every file exhaustively. For each file:
- Read the top 30–50 lines (imports, class signatures, docstrings)
- Grep for key technical terms (see pattern list below)
- If a function body looks algorithmically significant, read it fully

**Key term patterns to grep for:**
```
# Math / Optimization
gradient, jacobian, hessian, eigen, svd, qp, mpc, lqr, pid, kalman

# Robotics
kinematics, dynamics, urdf, ros, tf, imu, odom, lidar, slam, path_plan

# ML / AI
loss, backward, optimizer, embedding, attention, transformer, policy, reward

# Control
state_space, transfer_function, bode, nyquist, lyapunov, stability

# CS / Systems
async, coroutine, lock, semaphore, buffer, protocol, socket, serialize

# Mechanical
stress, strain, torque, inertia, cad, mesh, finite_element
```

### 3. Categorize findings

Map each discovered concept to one of these disciplines:
- `🤖 robotics` — kinematics, SLAM, ROS, motion planning
- `💻 cs` — data structures, algorithms, OS, networking, concurrency
- `🔢 math` — linear algebra, calculus, probability, optimization
- `⚙️ mechanical` — structural mechanics, CAD, FEA, mechanisms
- `🎛️ control` — control theory, signal processing, state estimation
- `🧠 ml` — machine learning, deep learning, reinforcement learning
- `🔬 other` — domain-specific (chemistry, biology, finance, etc.)

### 4. Output format

Present exactly this structure. Cap at **10 items**. If you find more, keep only the
most architecturally central ones.

```
## 📚 Project Knowledge Map

**Project:** <name or path>
**Scanned:** <date>
**Summary:** <1-2 sentence project purpose>

---

| # | Knowledge Point | Discipline | Core Files |
|---|---|---|---|
| K1 | <concise title, ≤8 words> | 🤖 robotics | `foo/bar.py` |
| K2 | ... | ... | ... |
...

---

**Suggested next step:** Run `/lz-discussion` to tell me which of these you want to go deep on.
```

### 5. Edge cases

- **Empty / no-code project**: Summarize from README and config only. Note lack of source.
- **Monorepo**: Focus on the sub-package most relevant to the user's stated goal.
- **Minified / obfuscated code**: Note this explicitly; extract what you can from variable names.
- **Pure data project** (CSV, JSON only): Extract schema, statistical patterns, domain vocabulary.
