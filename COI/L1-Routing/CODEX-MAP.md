# CODEX-MAP
COI's filing system. Read this to decide where information belongs.
Last updated: 2026-03-24

---

## THE RULE

Every piece of information has exactly one right place.
COI reads this map, decides where something belongs, tells Dave, gets approval, files it.
Dave never directs the filing. Dave only approves COI's decision.

---

## FOLDER MAP

### CLAUDE.md — Root Identity
- What goes here: COI's core identity, who she is, her role, operating rules for Claude Code
- Never modified without Dave's explicit direction
- This is Layer 0 — always loaded on every boot

### CONTEXT.md — Root Router
- What goes here: task routing rules, ICM layer map, build phase definitions
- Updated when architecture changes

### COI/00-constitution/ — Constitutional Layer
- What goes here: CONSTITUTION.md and SUCCESSION.md only
- IMMUTABLE — COI may never modify these files
- Supreme authority above all other layers

### COI/L1-Routing/ — Navigation & Quick Load
- What goes here: documents COI reads first on every boot
- Lightweight files only — under 3000 tokens each
- Files: QUICK-LOAD.md, MASTER-BUILD-ORDER.md, QUICK-LOAD-memory.md, CODEX-MAP.md
- New files here only if they need to load on every session

### COI/L3-Reference/ — Permanent Reference Material
- What goes here: specs, rules, capabilities, architecture docs, anything COI needs to reference repeatedly
- This is the most common destination for new information
- Existing files:
  - COI-Personality.md — COI's identity and tone
  - founding-philosophy.md — why COI exists
  - governance.md — decision making rules
  - pc-specs.md — Dave's hardware
- New files here for: new specs, new rules, new capability docs, new architecture decisions

### COI/L4-Working/memory/ — Active Memory
- What goes here: live memory files COI reads and writes every session
- Files:
  - next-session-briefing.md — what COI loads on every boot
  - decisions.md — every decision ever made
  - open-loops.md — unfinished items
  - dave-profile.md — how Dave thinks, extracted over time
  - error-memory.md — failed approaches, never repeated
- These files are updated frequently — COI manages them herself

### COI/L4-Working/sessions/ — Raw Session Logs
- What goes here: raw conversation logs, one file per session
- Written automatically by COI Desktop
- Never manually edited
- Format: YYYY-MM-DD-HH-MM.md

### COI/L4-Working/briefings/ — Briefing Archive
- What goes here: archived session briefings
- Never manually edited

### COI/L4-Working/ — Session Index
- session-index.md lives here — lightweight index of all sessions

### scripts/ — All Executable Scripts
- What goes here: Python scripts COI runs
- New scripts always go here

### ui/ — All User Interface Files
- What goes here: UI files for all platforms
- PyQt6 desktop application lives here
- New platform UIs go here

### bridge/ — COI-CC Communication
- What goes here: bridge logs and CC communication records
- cc_to_coi.txt — permanent log of all CC interactions

---

## FILING DECISION GUIDE

When COI receives information to file, she asks these questions in order:

1. **Is this about who COI is or why she exists?**
   -> `COI/L3-Reference/COI-Personality.md` or `CLAUDE.md` if it's identity

2. **Is this a rule, spec, or capability COI needs to reference repeatedly?**
   -> `COI/L3-Reference/` — create new file or append to most relevant existing file

3. **Is this a decision that was just made?**
   -> `COI/L4-Working/memory/decisions.md` — append

4. **Is this something unfinished that needs to be tracked?**
   -> `COI/L4-Working/memory/open-loops.md` — append

5. **Is this about the build roadmap or what needs to be built?**
   -> `COI/L1-Routing/MASTER-BUILD-ORDER.md` — update relevant section

6. **Is this a new script or tool?**
   -> `scripts/` — new file

7. **Is this session memory or a briefing?**
   -> `COI/L4-Working/memory/` — appropriate memory file

8. **Does it not fit any of the above?**
   -> COI proposes a new file location to Dave and explains why

---

## WHAT COI NEVER DOES

- Never files information without Dave's approval
- Never modifies CLAUDE.md without explicit Dave direction
- Never modifies COI/00-constitution/ under any circumstance
- Never creates duplicate files — always checks if content belongs in an existing file first
- Never guesses — if unsure, asks Dave before deciding

---

## COI'S FILING STATEMENT FORMAT

When COI decides where to file something she always says:

> "I'm going to [write/update/append] this to [exact file path] because [reason].
> Here is exactly what I will write:
> [content]
> Approve?"

Clear. Specific. Dave always knows exactly what is happening before it happens.
