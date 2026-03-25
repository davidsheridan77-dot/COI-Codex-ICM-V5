# COI Version Roadmap
**Layer:** L3 — Reference
**Last Updated:** V5
**Status:** P1 Complete

---

## Overview
COI V5 develops through 9 phases. Each phase delivers one capability. Dave approves every phase gate before work begins on the next. One thing at a time. Stable before next feature added.

---

## P1 — Claude-Only Chat (COMPLETE)

Clean PyQt6 desktop application with Claude API (Sonnet 4.6) as the sole intelligence layer. Foundation for everything that follows.

**What was delivered:**
- PyQt6 native desktop app
- Claude API integration
- COI identity loaded from Codex
- Session context from memory files
- Sandbox running in Hyper-V VM

---

## P2 — Ollama Routing Restored (NEXT)

Local models brought back for cost optimization. Classification and routine tasks handled locally. Complex reasoning stays on Claude API.

**What this delivers:**
- llama3.2:1b as classifier/router (~0.9GB VRAM)
- mistral:7b-instruct-q4_K_M as general-purpose local model (~4.1GB VRAM)
- Ollama runtime on localhost:11434
- Intelligent routing — local for routine, API for complex

---

## P3 — Windows Native Voice In/Out

Hands-free interaction through Windows native speech capabilities.

**What this delivers:**
- NaturalVoiceSAPIAdapter for text-to-speech
- SpeechRecognition for speech-to-text
- Automatic hands-free mode when earbuds detected
- COI speaks and listens natively — no cloud speech APIs

---

## P4 — Full PC Control

COI manages Dave's desktop applications and system controls.

**What this delivers:**
- Plex server control
- Steam library access
- uTorrent download management
- System volume control
- General app launch and kill

---

## P5 — Gaming Mode

Seamless transition between COI operation and gaming.

**What this delivers:**
- VRAM dump — free GPU memory for gaming
- 4-second watcher — detect when game exits
- Auto-reload — restore COI services after gaming ends
- uTorrent pause/resume — manage bandwidth during gaming

---

## P6 — Tailscale + Telegram Remote Access

COI accessible from anywhere, not just Dave's desktop.

**What this delivers:**
- Tailscale secure network — access COI remotely
- Telegram bot — mobile messaging interface
- Remote command execution
- Secure by design — no public exposure

---

## P7 — Media Panel

Entertainment integration and streaming availability tracking.

**What this delivers:**
- JustWatch RSS feed integration
- Canadian locale for region-appropriate results
- All major streaming service support
- What's new, what's leaving, what to watch

---

## P8 — Setup Wizard

Hardware-adaptive installation for distribution.

**What this delivers:**
- Automatic system scan — CPU, RAM, GPU, storage
- Hardware tier detection
- Three installation tiers:
  - COI Lite — 8GB RAM, no GPU
  - COI Standard — 16GB RAM, 6GB VRAM
  - COI Full — 32GB+ RAM, 12GB+ VRAM
- Guided setup experience

---

## P9 — Distribution + Auto-Updates

COI becomes distributable to other users.

**What this delivers:**
- GitHub manifest for version tracking
- Delta updates — only changed files transferred
- Automatic update checks and installation
- Dave approval required for update releases
- COI Core distributed — COI Personal stays private

---

## Phase Gate Rule
No phase begins until the previous phase is stable.
Dave holds the gate. COI cannot self-promote to the next phase.
One thing at a time. Stable before next feature added.

---

## North Star — COI OS

V5 is the last stepping stone before COI becomes an operating system.

**What this means:**
- COI runs as a true operating system, not an application layer
- Full autonomy within Dave-approved boundaries
- Self-improving — each version better than the last
- The Codex pattern replicates across instances
- Revenue self-sustaining, hardware self-funding
- Every human on Earth at full potential through AI symbiosis

---

*V5 Roadmap — P1 through P9 — then COI OS.*
