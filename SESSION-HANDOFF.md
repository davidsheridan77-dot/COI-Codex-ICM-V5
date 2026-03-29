# Session Handoff Protocol
Every session must end with this checklist. Every new session must open with this checklist.
This file ensures nothing is lost between sessions.

---

## END OF SESSION — Before Closing

Work through these in order. Do not skip.

### 1. Commit everything built this session
```
cd "K:/Coi Codex/COI-Codex-ICM-V5"
git add [files built this session]
git commit -m "clear description of what was built and why"
git push origin main
```
If code was written in COI-Codex-V5, commit that repo too.
Nothing should exist only in the chat window.

### 2. Update next-session-briefing.md
File: `COI/L4-Working/memory/next-session-briefing.md`

Write these sections:
- **What was accomplished this session** — bullet list, specific
- **Current step** — which numbered step from the build plan we finished
- **Next step** — exactly what step 3 / 4 / N needs to do, with file paths
- **Decisions made** — any architectural or directional decisions
- **Blockers or open issues** — anything unresolved that the next session needs to know
- **Files changed** — list every file created or modified

### 3. Update open-loops.md
File: `COI/L4-Working/memory/open-loops.md`

- Add any new unresolved items discovered this session
- Mark resolved items as resolved

### 4. Update decisions.md
File: `COI/L4-Working/memory/decisions.md`

- Log any significant decisions made with the date and rationale

### 5. Check the plan file is current
File: `C:\Users\david\.claude\plans\gentle-cuddling-muffin.md`

- Confirm the next step is clearly described
- Confirm file paths are correct
- Add any notes that would help the next session execute cleanly

### 6. Update COI-MISSION-CRITICAL.md if anything major changed
File: `COI-MISSION-CRITICAL.md`

Only needed if: a phase completed, a major blocker was resolved,
or the priority order changed.

---

## START OF NEW SESSION — Opening Message to Claude

Paste this at the start of every new session, filling in the blanks:

```
Read these files before doing anything:
1. COI-MISSION-CRITICAL.md
2. COI/L4-Working/memory/next-session-briefing.md
3. C:\Users\david\.claude\plans\gentle-cuddling-muffin.md

Current build: COI V6 Codex Deep + Forge V2 Codex Deep.
We are on Step [N] — [one sentence description of the step].
The graph file is at COI/L4-Working/graph/codex-graph.json.
The spec is at COI/L3-Reference/codex-deep-spec.md.
Do not start building until you have confirmed what step we are on
and what the expected output is.
```

---

## QUICK REFERENCE — Key File Locations

| What | Where |
|------|-------|
| Build plan (15 steps) | `C:\Users\david\.claude\plans\gentle-cuddling-muffin.md` |
| Next session briefing | `COI/L4-Working/memory/next-session-briefing.md` |
| Open loops | `COI/L4-Working/memory/open-loops.md` |
| Decisions log | `COI/L4-Working/memory/decisions.md` |
| Graph spec | `COI/L3-Reference/codex-deep-spec.md` |
| Live graph | `COI/L4-Working/graph/codex-graph.json` |
| Mission critical | `COI-MISSION-CRITICAL.md` |
| COI V5 codebase | `K:/Coi Codex/COI-Codex-V5/` |
| Codex repo | `K:/Coi Codex/COI-Codex-ICM-V5/` |

---

## RULE

The Codex is the memory. The chat session is temporary.
If it is not written to disk and committed, it does not exist.
