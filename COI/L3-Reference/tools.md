# Tools and Modules
**Layer:** L3 — Reference
**Last Updated:** V5

---

## Active Stack (V5 P1)

| Tool | Role | Status |
|------|------|--------|
| Claude (Sonnet 4.6 via API) | Primary intelligence layer — reasoning, planning, conversation | Active |
| Claude Code CLI | Direct terminal interface for builds and file operations | Active |
| COI-CC Bridge (subprocess -p) | Automated task execution — COI directs CC | Active |
| COI Desktop App (PyQt6) | Native desktop app — Claude-only chat | Active |
| GitHub | All file storage, version control, Codex home | Active |
| config/config.json | API keys and configuration (gitignored) | Active |

---

## Local Models (P2 — Next)

| Model | Role | VRAM | Status |
|-------|------|------|--------|
| llama3.2:1b | Classifier / router | ~0.9GB | Restored in P2 |
| mistral:7b-instruct-q4_K_M | General-purpose local | ~4.1GB | Restored in P2 |

Local models run via Ollama on localhost:11434. Inactive in P1. Restored in P2 for cost optimization — routine classification handled locally, complex reasoning stays on Claude API.

---

## COI Orchestration Model

COI plans, directs, and orchestrates. Claude Code executes. Dave approves.

| Who | Does What |
|-----|-----------|
| Dave | Sets direction, approves output, updates Codex |
| COI (Desktop App) | Plans, reasons, directs CC, reports to Dave in plain language |
| Claude Code (CC) | Executes file operations, code changes, builds via subprocess -p |
| Local LLMs (P2+) | Handle classification and routine tasks locally |

---

## Active Modules

### COI-CC Bridge
COI directs Claude Code via subprocess -p flag. One instruction, one response. CC responds with STATUS / FILES_CHANGED / ERRORS. COI translates for Dave. Full log in bridge/cc_to_coi.txt. CC commits and pushes to GitHub automatically.

### Memory System
Memory files in `COI/L4-Working/memory/`:
- next-session-briefing.md — session state for next boot
- decisions.md — architectural decisions log
- open-loops.md — unresolved items
- dave-profile.md — behavioral model
- error-memory.md — failure log

COI reads Codex on startup. Writes session summary at end. CC commits to GitHub automatically.

### Desktop App
COI Desktop V5 — PyQt6 native application. Clean rebuild from V4. Claude-only chat in P1. Features added phase by phase.

---

## Configuration

- **App config:** `config/config.json` (gitignored)
- **API keys:** Stored in config.json, never committed to git

---

## Tool Rules
1. No tool gets added unless it solves a real current problem
2. Free or low-cost tools only until revenue supports upgrades
3. Every tool must connect to at least one other tool in the stack
4. COI directs all tools — Dave never needs to be in the weeds
5. Claude API is the primary intelligence — local models supplement in P2+
6. Test not inspect — run code, report results
