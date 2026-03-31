# CLAUDE.md — Claude Code Operating Rules
Layer 0. Always loaded. This file governs Claude Code behavior in COI-Codex-ICM-V5.

## What This Repo Is
COI-Codex-ICM-V5 is the Codex for COI V5 — the persistent memory, context, and operational intelligence layer.
COI is a personal AI operating system built by Dave Sheridan. Not a chatbot. An operating system.
V5 is a clean PyQt6 Claude-only chat application. Sandbox build. No legacy code. Everything builds from this foundation one phase at a time.

## Architecture
ICM (Interpretable Context Methodology). Folder structure is agent architecture.

| Layer | Location | Purpose |
|-------|----------|---------|
| 0 | CLAUDE.md | These rules — always loaded |
| 1 | CONTEXT.md | Navigation, routing, layer map |
| 2 | pipeline/*/CONTEXT.md | Stage contracts — one per pipeline stage |
| 3 | COI/L3-Reference/ | Static knowledge — specs, rules, constitution |
| 4 | COI/L4-Working/ | Sessions, memory, working artifacts |

## Standing Rules

### Target
All work targets COI-Codex-ICM-V5 only. Do not create files or make changes outside this repo.

### Read Before Working
Before starting work, read:
- `COI-MISSION-CRITICAL.md` — current status, blockers, priorities
- `COI/L4-Working/memory/next-session-briefing.md` — last session state

### No Claude Dependencies Inside COI
COI is LLM-agnostic. Claude is a build partner, not an internal component.
Never embed Claude-specific tools, APIs, or dependencies into COI's runtime.
COI's intelligence lives in the Codex. LLMs are swappable.

### Approval Authority
Dave is the only approval authority. Nothing reaches live systems without his sign-off.
When in doubt, ask Dave. Do not assume approval from silence.

### File Routing
- Code tasks → pipeline/01-intake
- Memory updates → COI/L4-Working/memory/
- Session logs → COI/L4-Working/sessions/
- Reference docs → COI/L3-Reference/
- UI changes → ui/
- Scripts → scripts/

### Commits
Use clear commit messages. Summarize what changed and why.
Never commit secrets, API keys, or tokens. Config is in config/ (gitignored).
Dave approves before anything gets committed. Never leave uncommitted changes without telling Dave.

### Cost Management
- Claude API (Sonnet 4.6) is the only model in P1. Local models return in P2.
- System prompt lazy loading — load only files relevant to current task context.
- COI-CC bridge is the execution mechanism. One instruction, one response. No back and forth.
- After every successful task, CC commits and pushes to GitHub automatically.

### What NOT To Do
- Do not refactor code that is not part of the current task
- Do not add features not explicitly requested
- Do not create documentation files unless asked
- Do not modify COI/00-constitution/ — it is immutable
- Do not run destructive git commands without Dave's explicit approval
- Do not add external service dependencies without Dave's approval

## Key Paths
| What | Where |
|------|-------|
| Config | config/config.json |
| Desktop UI | ui/ |
| Scripts | scripts/ |
| Memory files | COI/L4-Working/memory/ |
| Session logs | COI/L4-Working/sessions/ |
| Pipeline | pipeline/ |
| Build order | COI/L1-Routing/ |
| Mission critical | COI-MISSION-CRITICAL.md |

## LLM Roster
| Role | Model | Status |
|------|-------|--------|
| All tasks (P1) | Claude API — Sonnet 4.6 | Active |
| Classifier / Router | llama3.2:1b | Inactive — returns in P2 |
| General-purpose local | mistral:7b-instruct-q4_K_M | Inactive — returns in P2 |

## COI-CC Bridge
COI directs Claude Code via subprocess -p flag. No middleman. COI and CC communicate in markdown and code only. CC responds with minimal status: STATUS / FILES_CHANGED / ERRORS. COI interprets results and reports to Dave in plain conversational language. Dave never sees raw CC output. Full log kept in bridge/cc_to_coi.txt permanently.

## Testing Philosophy
Test not inspect. COI runs changed code and reports pass or fail. Never read files to check if something worked — run it and see. One thing at a time. Stable before next feature added.

## Dave
Builder, Father of COI, sole user and approval authority.
Blue-collar worker building a planetary-scale AI OS.
First-principles thinker. No unnecessary complexity.
Take it slow. One thing at a time. Plain conversational language.

## Hardware
- CPU: AMD Ryzen 5 5500 — 6 cores 12 threads
- RAM: 64GB DDR4
- GPU: AMD RX 6600 — 8GB VRAM
- OS: Windows 11 Pro

## Bug/Error Logs

When troubleshooting bugs or errors, check these logs in order of relevance.

### Runtime Logs — `K:/Coi Codex/COI-Codex-V5/logs/`

| Log File | What It Tracks |
|----------|---------------|
| `failures.log` | All runtime failures and unhandled exceptions |
| `system-telemetry.log` | CPU, RAM, VRAM, system-level health over time |
| `health-log.txt` | COI health check results (model status, API reachability) |
| `perf-log.txt` | Performance timing data (response latency, pipeline durations) |
| `cq-writeback-log.jsonl` | Tier 3 write-back events — confirms Sonnet fallback fired |
| `cq-query-engine.jsonl` | LightRAG query engine decisions and retrieval results |
| `cq-retrieval-logic.jsonl` | Codex Quantum retrieval path tracing |
| `cq-training-log.jsonl` | Training loop entries and scoring |
| `cq-edge-weights.jsonl` | Graph edge weight updates |
| `cq-graph-structure.jsonl` | Graph structure changes (nodes/edges added or removed) |
| `scan-index-log.jsonl` | Document scan and indexing events |
| `swap-log.jsonl` | Model swap/load/unload events |
| `benchmark-results.jsonl` | Benchmark run outputs |
| `telegram-log.txt` | Telegram bot activity and errors |
| `vram-manager.log` | VRAM allocation, model loading, OOM events |
| `intake-pipeline.log` | Pipeline intake stage processing |

### Forge Logs — `K:/Coi Codex/COI-Codex-V5/logs/`

| Log File | What It Tracks |
|----------|---------------|
| `forge-manager.log` | Forge Manager routing decisions and job lifecycle |
| `forge-pipeline.log` | Forge pipeline stage execution |
| `forge-runner.log` | Forge job runner output |
| `forge-queue.json` | Current forge job queue state (live — do not edit) |
| `forge-results.json` | Completed forge job results |
| `forge-checkpoint.json` | Forge progress checkpoints |
| `jobs/JOB-*/job.json` | Per-job metadata |
| `jobs/JOB-*/fm-routing.log` | Per-job routing decisions |
| `jobs/JOB-*/error.log` | Per-job error output |
| `jobs/JOB-*/department-output.txt` | Per-job LLM department response |

### Forge Training — `K:/Coi Codex/COI-Codex-V5/COI-Forge-Codex/TRAINING/`

| Log File | What It Tracks |
|----------|---------------|
| `fm-training-log.jsonl` | Forge Manager training data (routing decisions for learning) |

### Cache Files — `K:/Coi Codex/COI-Codex-V5/scripts/`

| File | Purpose |
|------|---------|
| `response-cache.msgpack` | Tier 1 response cache — clear before test runs |
| `codex-index.msgpack` | Codex document index |
| `cc-learning-log.msgpack` | Claude Code learning log |
| `token-log.msgpack` | Token usage tracking |

### Dev Panel Logs (In-App)

The Dev panel in `main.py` writes `TIER` tagged log entries visible at runtime:
- `TIER` — tier routing decisions, confidence scores, escalation events
- `CC_DEBUG` / `CC_SEND` — Claude Code bridge subprocess commands and output
- `SUBPROCESS` — subprocess launch, exit codes, stdout/stderr
- `EXCEPTION` — caught exceptions with tracebacks
- `FILE` — file read/write operations and success status

### COI Memory — Error Tracking

| File | Location | Purpose |
|------|----------|---------|
| `error-memory.md` | `COI/L4-Working/memory/` (ICM-V5) | Failed approaches — never repeat |
| `error-memory.md` | `K:/Coi Codex/COI-Codex-ICM/COI/L4-Working/memory/` | Same, ICM copy |
| `crash-log.md` | `K:/Coi Codex/COI-Codex-ICM/COI/L4-Working/memory/` | Crash history |
| `bug-tracker.md` | `K:/Coi Codex/COI-Codex-ICM/COI/L4-Working/memory/` | Known bugs and status |
| `diagnostic-results.md` | `K:/Coi Codex/COI-Codex-ICM/COI/L4-Working/memory/` | Diagnostic test outputs |
| `watcher-alerts.md` | `K:/Coi Codex/COI-Codex-ICM/COI/L4-Working/memory/` | Log watcher alert history |

### Token & Spike Tracking

| File | Location | Purpose |
|------|----------|---------|
| `token_spikes.json` | `K:/Coi Codex/COI-Codex-ICM/logs/` | Token usage spike events |
| `model_load_times.json` | `K:/Coi Codex/COI-Codex-ICM/logs/` | Model load duration tracking |

### Training Data (Read-Only Reference)

| File | Location | Purpose |
|------|----------|---------|
| `chat-log.jsonl` | `COI/L4-Working/training/dataset/` | Chat history for training |
| `synthetic-log.jsonl` | `COI/L4-Working/training/dataset/` | Synthetic training examples |
| `benchmark-set.jsonl` | `COI/L4-Working/training/dataset/` | Benchmark question set |
| `benchmark-results.jsonl` | `COI/L4-Working/training/scores/` | Benchmark scoring results |
| `compression-audit.jsonl` | `COI/L4-Working/training/scores/` | Compression quality audits |

## Stage
V5 P1 — Claude-only chat complete. P2 next (Ollama routing restored).
