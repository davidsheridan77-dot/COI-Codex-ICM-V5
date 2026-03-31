# COI Mission Critical — V5 Operational Status

## Current Phase
V5 P1 — COMPLETE
Codex Quantum — LightRAG + Three-Tier Intelligence IN PROGRESS.
49 Codex docs indexed. Tier engine built and wired. Testing in progress.

## Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| PyQt6 Desktop UI | Operational | Claude-only chat running |
| Claude API Integration | Operational | Sonnet 4.6 — Tier 3 escalation |
| COI-CC Bridge | Operational | Subprocess -p flag, one instruction one response |
| Codex (ICM-V5) | Operational | Memory structure in place |
| Codex Quantum Graph | Operational | 631-node knowledge graph |
| LightRAG Engine | Operational | 49 docs indexed, 631 nodes, 293 edges |
| tier_engine.py | In Testing | Three-tier pipeline. Answers correct. Timing issues being resolved. |
| gemma3:4b-cq | Operational | Custom model, 8190 ctx baked in, 4168MB VRAM |
| Startup Context Cache | Operational | Pre-computed at shutdown, instant load at startup |
| Response Cache | Operational | 24hr TTL — must clear before test runs |
| Graph Builder | Operational | gemma3:4b-cq extracts nodes from memory files |
| CQ Logger | Operational | 4-layer non-blocking logging |
| Snapshot System | Operational | Named snapshots, integrity hashing |
| Benchmark Suite | Operational | 50-query set, Tests A/B/C/D — NOT YET RUN against LightRAG |
| Training Script | Operational | 200+ diverse queries |
| Update Script | Operational | Incremental index on file change |
| Session Graph Writer | Operational | Shutdown creates decision + open_loop nodes |
| Audit Pipeline | Operational | Reads FM logs, writes recommendations to graph |
| Graph-Native FM Routing | Operational | FM loads department/model config from graph |
| Priority Pipeline | Operational | Backlog scorer + graph-aware FM queue scheduling |
| Morning Briefing | Operational | Overnight summary + top priority via Telegram |
| Config | Operational | config/config.json, gitignored |

## Critical Config Values (DO NOT CHANGE WITHOUT TESTING)
| Setting | Value | Reason |
|---------|-------|--------|
| num_ctx | 8190 | RX 6600 VRAM protection — hard cap everywhere |
| llm_model_max_async | 1 | One concurrent LLM worker max |
| CONFIDENCE_THRESHOLD | 7 | Below 7 = wrong answers pass |
| OLLAMA_TIMEOUT | 20s | Gemma inference cap |
| _TIER_HARD_TIMEOUT | 8s | Entire tier_query (LightRAG+gemma) cap |

## Build Order
- P1 — Claude-only chat — COMPLETE
- Codex Quantum Phase 0 — Graph foundation — COMPLETE
- Codex Quantum Phase 1 — COI V6 self-knowledge — COMPLETE
- Codex Quantum Phase 2 — Forge V2 — COMPLETE (Steps 14-15 deferred)
- P2 — Ollama routing restored — COMPLETE
- **NOW: Three-Tier Intelligence — in testing**
- P3 — Windows native voice in/out
- P4 — Full PC control
- P5 — Gaming mode
- P6 — Tailscale + Telegram remote access
- P7 — Media panel
- P8 — Setup wizard
- P9 — Distribution + auto-updates

## Next Priority
Complete tier engine testing:
1. Clear cache, restart COI, ask 3 test questions
2. Verify TIER logs in Dev panel show correct routing
3. Verify Tier 3 write-back fires (cq-writeback-log.jsonl)
4. Run benchmark Tests A and B once tier engine is stable

## Blockers
None.

## Open Loops
- Tier 3 write-back not yet confirmed firing in live run
- 8s hard timeout not yet tested with Sonnet as Tier 3
- Subprocesses health check showing "warn" — zombie process accumulation
- TTS repair still pending
- CC timeout root cause still undiagnosed
- deepseek-coder:6.7b VRAM estimate wrong in graph (3800MB est vs 5886MB actual)

## North Star
COI OS. V5 is the last stepping stone before COI becomes an operating system.
