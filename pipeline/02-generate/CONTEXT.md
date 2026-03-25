# Stage 02 — Generate
Layer 2. Read when writing code.

## Job
Receive the task brief and write the code.

## Execution
Claude API (Sonnet 4.6) via COI-CC bridge. One instruction, one response.

## Inputs
| Source | File | Why |
|--------|------|-----|
| Stage 01 | ../01-intake/output/task-brief.md | What to build |
| Layer 0 | CLAUDE.md | COI conventions and constraints |

## Process
1. Read task brief
2. Write code to solve the task
3. Add inline comments explaining decisions
4. Write output file
5. If task is unclear — write clarification request instead of guessing

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| Generated code | output/generated-code.md | Code with context header |

## Rules
- Never modify live files directly
- If uncertain — flag it, do not guess
- One task per output file
