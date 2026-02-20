---
applyTo: "**"
---
# Coding Standards

## Core Principles
1. **Think First**: State assumptions. Ask if unclear. Surface tradeoffs.
2. **Simplicity**: Minimum code that solves the problem. No speculation.
3. **Surgical**: Touch only what's needed. Clean only your own mess.
4. **Goal-Driven**: Define success criteria. Loop until verified.

## Python (*.py)
- PEP 8, type hints, descriptive names
- Clear comments per function
- Keep cognitive complexity low; break down large functions

## Workflow
- Analyze → plan → self-review/self-reflect → implement (when approved)
- Minimal changes when refactoring
- If asked, create a new folder with appropriate naming inside `localdev/docs/` for analysis or plan or documentation etc. and keep date of creation at the footer of each docs and number them in the order of creation. For example, if you are creating a doc for analysis, create a folder named `localdev/docs/analysis/` and create a file named `00_ANALYSIS.md` inside it. If you are creating a doc for plan, create a folder named `localdev/docs/plans/` and create a file named `00_PLAN.md` inside it. And so on.

## Implementation Guidelines

### Think First
- If multiple interpretations exist, present them—don't pick silently
- If simpler approach exists, say so. Push back when warranted

### Simplicity
- No features beyond what was asked
- No abstractions for single-use code
- No "flexibility" that wasn't requested
- If 200 lines could be 50, rewrite

### Surgical Changes
- Don't "improve" adjacent code/formatting
- Match existing style
- Unrelated dead code: mention, don't delete
- Remove only orphans YOUR changes created

### Goal-Driven
Transform tasks into verifiable goals:
- "Add validation" → tests for invalid inputs pass
- "Fix bug" → reproducing test passes
- "Refactor X" → tests pass before and after

Multi-step plan format:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
```

**Tradeoff:** Guidelines bias caution over speed. Use judgment for trivial tasks.