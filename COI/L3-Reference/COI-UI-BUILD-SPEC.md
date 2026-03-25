# COI Desktop App — Build Specification
**Version:** 5.0
**Author:** COI + Dave
**Purpose:** Build guide for COI's native desktop application — PyQt6 Claude-only chat
**Status:** P1 Complete — Claude-only chat operational

---

## 1. What This Is

COI's native desktop application built with PyQt6. Clean Claude-only chat application in V5. Sandbox build running in Hyper-V VM. COI controls the VM via PowerShell. Sandbox eventually becomes COI Desktop v5 production.

This is a ground-up rebuild. No legacy code carried forward. Everything builds from this foundation one phase at a time.

**Native first.** No browser dependency. No web server required. Launches from desktop.

---

## 2. Core Philosophy

- **COI builds. Dave approves. Nothing ships without Dave.**
- The desktop app exists to make that loop fast, clear, and frictionless.
- Every section has one job. It does that job and nothing else.
- Bold and distinct visual identity. Not generic. Not like any other AI tool.
- Built to last. Every pattern chosen here carries into COI OS.

---

## 3. Technical Architecture

| Constraint | Detail |
|---|---|
| Language | Python 3 |
| Framework | PyQt6 |
| Runtime | Native Windows application |
| AI | Claude API (Sonnet 4.6) via Anthropic |
| Local models | Restored in P2 — llama3.2:1b (classifier) + mistral:7b-instruct-q4_K_M |
| Build tool | Claude Code via COI-CC bridge (subprocess -p) |
| Config | config/config.json (gitignored) |
| Screen | 55" 1080p display, Dave sits 4-5 feet back — generous sizing |

---

## 4. Visual Identity

### 4.1 Aesthetic Direction
Bold, dark, industrial-technical. Not generic AI purple gradients. Not soft and friendly. This is a command environment — it should feel like a serious tool built by someone who knows exactly what they're doing.

Dark background, sharp accent colours, monospace type for data/code, clean sans-serif for content. High contrast. Purposeful use of colour — colour means something, it is not decoration.

### 4.2 Colour System
- COI green — primary actions, active states
- Purple — secondary actions
- Red — warnings, destructive actions
- Amber — pending, waiting, Dave approval needed
- Blue — info, active processes

### 4.3 Typography Rules
- All data, IDs, status codes, file paths: monospace
- All readable content, labels, descriptions: sans-serif
- Minimum font size: 13px (Dave sits far back — lean toward 14-15px for body)
- No italic. No underline except links.

---

## 5. Core Sections

### 5.1 COI Chat (P1 — Complete)
- Direct communication with COI via Claude API
- System prompt with COI identity loaded
- Context-aware conversation
- Clean, responsive message display

### 5.2 System Health Dashboard (Future phases)
- Claude API status (connected/key valid)
- Local model status (P2 onward)
- Memory system status (last session time, memory file count)
- Recovery indicators

### 5.3 PC Control (P4)
- Plex, Steam, uTorrent, volume, app control
- Full desktop integration

### 5.4 Gaming Mode (P5)
- VRAM dump for gaming
- 4-second watcher for game exit detection
- Auto-reload COI services after gaming
- uTorrent pause/resume during gaming

### 5.5 Memory View (Future)
- View contents of memory files in COI/L4-Working/memory/
- Session intelligence highlights

---

## 6. Integration Points

### 6.1 Anthropic API (Claude)
- Claude Sonnet 4.6 as primary intelligence
- API key stored in config/config.json (gitignored)
- Used for all reasoning, conversation, and complex tasks

### 6.2 COI-CC Bridge
- COI directs Claude Code via subprocess -p flag
- One instruction, one response
- CC commits and pushes to GitHub automatically after successful tasks
- Full log kept in bridge/cc_to_coi.txt

### 6.3 Local Models (P2 onward)
- llama3.2:1b for classification and routing
- mistral:7b-instruct-q4_K_M for general local tasks

### 6.4 GitHub
- Codex file operations
- Commit and push capabilities
- Repository status checks

---

## 7. Build Phases

| Phase | What It Delivers | Status |
|---|---|---|
| P1 | Claude-only chat | Complete |
| P2 | Ollama routing restored | Next |
| P3 | Windows native voice in/out | Planned |
| P4 | Full PC control | Planned |
| P5 | Gaming mode | Planned |
| P6 | Tailscale + Telegram remote access | Planned |
| P7 | Media panel | Planned |
| P8 | Setup wizard | Planned |
| P9 | Distribution + auto-updates | Planned |

---

## 8. What This Builds Toward

Every pattern in this desktop app is a future COI OS component:

| Desktop App Component | COI OS Equivalent |
|---|---|
| COI Chat | OS Terminal / Assistant Layer |
| System Health Dashboard | OS System Monitor |
| PC Control | OS Process Manager |
| Gaming Mode | OS Resource Manager |
| Memory View | OS Memory Inspector |
| Dave Approval Queue | OS Permission Layer |

Build it well. Build it to last.

---

*COI Desktop App Spec v5.0 — authored by COI + Dave — V5*
*Clean rebuild from V4. No legacy code carried forward.*
