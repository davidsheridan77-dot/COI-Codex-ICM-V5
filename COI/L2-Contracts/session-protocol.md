# COI — Session Protocol
**Layer:** L2 — Contracts
**Version:** V5

---

## Purpose
The ritual for opening and closing every COI session. This keeps the Codex alive and accurate. Without this protocol, COI loses continuity between sessions.

---

## Session Opening

### Startup Sequence
COI reads the Codex on startup:
1. `CLAUDE.md` — Layer 0, loaded automatically
2. `COI/L4-Working/memory/next-session-briefing.md` — where we left off
3. `COI-MISSION-CRITICAL.md` — current status and priorities

### Additional Context (Load When Needed)
- Building or debugging → also load error-memory.md
- Strategic decisions → also load decisions.md, open-loops.md
- Architecture work → also load L3-Reference files

---

## Session Closing

### Codex Update
Before ending every session, COI updates memory:

**Always update:**
- [ ] `next-session-briefing.md` — what happened and what comes next
- [ ] `open-loops.md` — add or close any pending items

**Update if relevant:**
- [ ] `decisions.md` — if key decisions were made
- [ ] `error-memory.md` — if something failed and should never be repeated
- [ ] `dave-profile.md` — if new working style patterns observed

### Commit
CC commits memory updates and pushes to GitHub automatically after session close.

---

## Session Types

| Type | Files to Load | Focus |
|------|--------------|-------|
| Daily check-in | next-session-briefing + MISSION-CRITICAL | Quick priorities and tasks |
| Build session | + error-memory | Code, pipeline, desktop work |
| Strategic | + decisions + open-loops + L3-Reference | Big picture decisions |
| Codex review | All L3-Reference + all memory files | Quality audit |

---

## Execution Mechanism
COI directs Claude Code via the COI-CC bridge (subprocess -p flag). One instruction, one response. COI interprets results and reports to Dave in plain conversational language. Dave never sees raw CC output.

---

## Rules
1. Never end a session without updating next-session-briefing.md at minimum
2. Always load CLAUDE.md + next-session-briefing at minimum
3. Keep updates concise — bullet points not essays
4. If short on time, at minimum update open-loops.md
5. Dave approves before commit — never commit without telling Dave
