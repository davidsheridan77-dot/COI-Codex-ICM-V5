# COI Mission Critical — V5 Operational Status

## Current Phase
V5 P1 — COMPLETE
Codex Quantum — LightRAG integration IN PROGRESS.
All 49 Codex docs indexed into LightRAG. Supporting systems built. Benchmark testing next.

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| PyQt6 Desktop UI | Operational | Claude-only chat running |
| Claude API Integration | Operational | Sonnet 4.6 |
| COI-CC Bridge | Operational | Subprocess -p flag, one instruction one response |
| Codex (ICM-V5) | Operational | Memory structure in place |
| Codex Quantum Graph | Operational | 57-node knowledge graph, graph-driven startup context |
| Graph Query Engine | Operational | Zero VRAM, pure code traversal (preserved as fallback) |
| Graph Builder | Operational | gemma3:4b extracts nodes from memory files |
| LightRAG Engine | Operational | 49 docs indexed, graph+vector retrieval, 768-dim embeddings |
| CQ Logger | Operational | 4-layer non-blocking logging (graph, edges, queries, retrieval) |
| Snapshot System | Operational | Named snapshots, integrity hashing, one-command restore |
| Benchmark Suite | Operational | 50-query set, Tests A/B/C/D, all metrics recorded |
| Keyword Weights | Operational | TF-IDF weights across 49 docs, 2522 unique terms |
| Training Script | Operational | 200+ diverse queries, overnight operation, 100% success rate |
| Update Script | Operational | Incremental index on file change, watch mode, auto-snapshot |
| Session Graph Writer | Operational | Shutdown creates decision + open_loop nodes |
| Audit Pipeline | Operational | Reads FM logs, writes recommendations to graph |
| Graph-Native FM Routing | Operational | FM loads department/model config from graph at startup |
| Priority Pipeline | Operational | Backlog scorer + graph-aware FM queue scheduling |
| Morning Briefing | Operational | Overnight summary + top priority via Telegram |
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
- Codex Quantum Phase 2 — Forge V2 (corporation structure, graph routing, pipelines) — COMPLETE (Steps 14-15 deferred until products ship)
- P2 — Ollama routing tested and fixed — COMPLETE
- P2 — Ollama routing restored
- P3 — Windows native voice in/out
- P4 — Full PC control (Plex, Steam, uTorrent, volume, apps)
- P5 — Gaming mode
- P6 — Tailscale + Telegram remote access
- P7 — Media panel
- P8 — Setup wizard
- P9 — Distribution + auto-updates

## Next Priority
LightRAG integration — Run benchmark Tests A and B (V5 flat-file vs V6 LightRAG).
Create baseline_v6_pretest snapshot before any benchmark runs.
Wire LightRAG into startup.py (USE_LIGHTRAG toggle) so COI uses it for session context.

## Blockers
None.

## Open Loops
- CC timeout root cause still undiagnosed
- TTS repair still pending
- deepseek-coder:6.7b VRAM estimate wrong in graph (3800MB est vs 5886MB actual)
- LightRAG retrieve time ~50s/query (gemma3:4b keyword extraction) — may need speed optimisation
- startup.py not yet wired to USE_LIGHTRAG — still using graph_query.py for session context

## North Star
COI OS. V5 is the last stepping stone before COI becomes an operating system.
