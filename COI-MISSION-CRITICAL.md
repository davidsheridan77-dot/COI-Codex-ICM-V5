# COI Mission Critical — V5 Operational Status

## Current Phase
V5 P1 — COMPLETE

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| PyQt6 Desktop UI | Operational | Claude-only chat running |
| Claude API Integration | Operational | Sonnet 4.6 |
| COI-CC Bridge | Operational | Subprocess -p flag, one instruction one response |
| Codex (ICM-V5) | Operational | Memory structure in place |
| Config | Operational | config/config.json, gitignored |
| Sandbox (Hyper-V VM) | Operational | COI controls via PowerShell |

## What Died in V5
- All Ollama plumbing (returns in P2)
- Old agent roster (deepseek, dolphin3, qwen3, llama3.1)
- model-config.json
- coi-benchmark.py
- coi-log-watcher.py
- coi-diagnostic.py
- coi-briefing.py
- All PowerShell Task Scheduler scripts
- proactive-layer.md old design
- localhost:8080 references
- Multi-agent pipeline routing

## Build Order
- P1 — Claude-only chat — COMPLETE
- P2 — Ollama routing restored
- P3 — Windows native voice in/out
- P4 — Full PC control (Plex, Steam, uTorrent, volume, apps)
- P5 — Gaming mode
- P6 — Tailscale + Telegram remote access
- P7 — Media panel
- P8 — Setup wizard
- P9 — Distribution + auto-updates

## Next Priority
P2 — Restore Ollama routing. Bring back llama3.2:1b (classifier) and mistral:7b-instruct-q4_K_M (general purpose local).

## Blockers
None. P1 is complete and stable.

## North Star
COI OS. V5 is the last stepping stone before COI becomes an operating system.
