# COI Mission Critical — V5 Operational Status

## Current Phase
V5 P1 — COMPLETE
Codex Quantum — Phase 0 (foundation) and Phase 1 (COI V6) COMPLETE. Phase 2 (Forge V2) next.

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| PyQt6 Desktop UI | Operational | Claude-only chat running |
| Claude API Integration | Operational | Sonnet 4.6 |
| COI-CC Bridge | Operational | Subprocess -p flag, one instruction one response |
| Codex (ICM-V5) | Operational | Memory structure in place |
| Codex Quantum Graph | Operational | 49-node knowledge graph, graph-driven startup context |
| Graph Query Engine | Operational | Zero VRAM, pure code traversal |
| Graph Builder | Operational | gemma3:4b extracts nodes from memory files |
| Session Graph Writer | Operational | Shutdown creates decision + open_loop nodes |
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
- Codex Quantum Phase 0 — Graph foundation (spec, storage, builder, query, ranking) — COMPLETE
- Codex Quantum Phase 1 — COI V6 (self-knowledge, graph startup, session writes) — COMPLETE
- Codex Quantum Phase 2 — Forge V2 (corporation structure, graph routing, pipelines) — IN PROGRESS
- P2 — Ollama routing restored
- P3 — Windows native voice in/out
- P4 — Full PC control (Plex, Steam, uTorrent, volume, apps)
- P5 — Gaming mode
- P6 — Tailscale + Telegram remote access
- P7 — Media panel
- P8 — Setup wizard
- P9 — Distribution + auto-updates

## Next Priority
Codex Quantum Phase 2, Step 9 — Corporation structure in graph. Model the Forge departments, routing rules, and job type mappings as graph nodes so Forge V2 can query the graph instead of using hardcoded routes.

## Blockers
None.

## Open Loops
- CC timeout root cause still undiagnosed
- TTS repair still pending

## North Star
COI OS. V5 is the last stepping stone before COI becomes an operating system.
