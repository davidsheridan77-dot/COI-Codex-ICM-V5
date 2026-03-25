# MASTER BUILD ORDER
COI V5 — source of truth for build sequencing.
Last updated: 2026-03-24

---

## THE NORTH STAR

> COI OS — A ground up operating system. Not an app. Not patched together from other tools.
> Built by Dave and COI from first principles. The OS to end all other operating systems.
> V5 is the last stepping stone before COI becomes an operating system.
> Everything in this document is a step toward that.

---

## THE BUILD ORDER

---

### P1 — Claude-Only Chat (COMPLETE)
**Goal: Clean PyQt6 chat application talking to Claude API only.**

- [x] PyQt6 desktop application running
- [x] Claude API (Sonnet 4.6) as sole AI provider
- [x] Clean conversation interface
- [x] No legacy code, no deprecated dependencies
- [x] Foundation stable for all subsequent phases

---

### P2 — Ollama Routing Restored
**Goal: Local LLM routing back online alongside Claude.**

- [ ] Ollama connection restored (localhost:11434)
- [ ] llama3.2:1b operational as classifier (~0.9GB)
- [ ] mistral:7b-instruct-q4_K_M operational as general-purpose local (~4.1GB)
- [ ] Routing logic: local first, Claude for complex reasoning and Dave-facing responses
- [ ] Model health checks on startup
- [ ] Graceful fallback to Claude-only if Ollama unavailable

---

### P3 — Windows Native Voice In/Out
**Goal: Hands-free voice interaction with COI.**

- [ ] NaturalVoiceSAPIAdapter for text-to-speech output
- [ ] SpeechRecognition for voice input
- [ ] Windows native — no external APIs, no cloud speech services
- [ ] Push-to-talk and continuous listening modes
- [ ] COI speaks all responses when voice mode active

---

### P4 — Full PC Control
**Goal: COI manages Dave's PC applications and system.**

- [ ] Plex control (play, pause, search, queue)
- [ ] Steam control (launch games, check library)
- [ ] uTorrent control (add, pause, resume, status)
- [ ] System volume control
- [ ] Application launch and management
- [ ] All control via PowerShell subprocess calls

---

### P5 — Gaming Mode
**Goal: COI adapts to Dave gaming — zero interference, smart resource management.**

- [ ] VRAM dump — release all models when game launches
- [ ] 4-second watcher — detect game exit, auto-reload models
- [ ] Auto-reload COI services after gaming session ends
- [ ] uTorrent pause on game launch, resume on game exit
- [ ] Minimal background footprint during gaming

---

### P6 — Tailscale + Telegram Remote Access
**Goal: COI accessible from anywhere, not just home network.**

- [ ] Tailscale integration for secure remote access
- [ ] Telegram bot for mobile COI interaction
- [ ] Remote commands: status, approve, reject, quick questions
- [ ] Push notifications for approval requests
- [ ] Secure — no public endpoints

---

### P7 — Media Panel
**Goal: COI as entertainment intelligence hub.**

- [ ] JustWatch RSS integration
- [ ] Canadian locale for accurate availability
- [ ] All major streaming services tracked
- [ ] New release notifications
- [ ] Recommendation engine based on Dave's preferences
- [ ] Integrated into desktop UI as dedicated panel

---

### P8 — Setup Wizard
**Goal: Any user can install COI from scratch.**

- [ ] System scan — detect hardware automatically
- [ ] Hardware capability assessment (RAM, VRAM, CPU)
- [ ] Tiered install recommendation:
  - COI Lite (8GB RAM, no GPU)
  - COI Standard (16GB RAM, 6GB VRAM)
  - COI Full (32GB+ RAM, 12GB+ VRAM)
- [ ] Guided setup flow
- [ ] Dependency installation automated

---

### P9 — Distribution + Auto-Updates
**Goal: COI reaches the world.**

- [ ] GitHub manifest for version tracking
- [ ] Delta updates only — never full re-download
- [ ] Dave approval required before any release
- [ ] COI Core distributed (base identity, no personal rules)
- [ ] COI Personal stays private (Father rule, succession, constitutional articles)
- [ ] Auto-update client checks manifest on startup

---

## COI-CC BRIDGE

COI directs Claude Code directly via subprocess -p flag. No middleman.

- COI sends markdown and code instructions to CC
- CC responds with: STATUS / FILES_CHANGED / ERRORS
- COI interprets results and reports to Dave in plain conversational language
- Dave never sees raw CC output
- No back and forth between COI and CC — one instruction, one response
- If clarification needed, COI asks Dave, not CC
- Full log kept in bridge/cc_to_coi.txt permanently
- After every successful task, CC commits and pushes to GitHub automatically

---

## TESTING PHILOSOPHY

Test not inspect. COI runs changed code and reports pass or fail.
Never read files to check if something worked — run it and see.
One thing at a time. Stable before next feature added.

---

## DAVE'S APPROVAL TRIGGERS
*Only these require Dave. Everything else COI handles herself.*

| Trigger | Notes |
|---------|-------|
| Deploying / installing updates | Always requires Dave sign-off |
| High level architectural changes | Crosses platforms or touches core architecture |
| Critical / major bugs | Beyond COI's classification threshold |
| New phase kickoffs | Dave authorizes each phase start |
| Product launches | Nothing ships to the world without Dave |
| Anything touching security layer | Passwords, keys, billing — hard stop |
| Commits and pushes | Dave approves before anything gets committed |

---

## ARCHITECTURAL PRINCIPLES

These are permanent. They govern every build decision.

### 1. Clean Build
V5 is a sandbox build. No legacy code. No deprecated dependencies. Everything builds from this foundation one phase at a time.

### 2. Claude-First, Local-Second
Claude API handles complex reasoning and Dave-facing responses. Local LLMs (P2+) handle classification, routing, and routine tasks. Cost managed at every level.

### 3. One Thing at a Time
Take it slow. Each phase stable before the next begins. Dave approves phase transitions.

### 4. Test Not Inspect
Run code to verify. Never read files to check if something worked.

---

## COI'S CORE OPERATING RULE

> No gaps. No idle time. Always building.
>
> Task complete -> start next task
> Phase complete -> start next phase
> Blocked -> document blocker, notify Dave, move to next available task
> Approval needed -> notify Dave, continue other work while waiting
> No task available -> review Codex, identify gaps, propose next work to Dave
