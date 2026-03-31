# Next Session Briefing
## Last Updated: 2026-03-31
## Source: Manual session close

## What Was Built This Session

### Three-Tier Intelligence Engine — tier_engine.py
- Tier 1: Response cache (<10ms)
- Tier 2: LightRAG context + gemma3:4b-cq (local, fast)
- Tier 3: Sonnet escalation + graph write-back (self-improving loop)
- Self-improving: Tier 3 Sonnet answers indexed back into LightRAG so Tier 2 learns

### gemma3:4b-cq — Custom Ollama Model
- Created Modelfile with `FROM gemma3:4b` + `PARAMETER num_ctx 8190`
- Baked-in 8190 ctx prevents LightRAG health checks from reloading at default 32768
- VRAM: 4168MB. Total with nomic-embed: ~4.7GB. Clean headroom on 8GB card.
- gemma3:4b (bare) fully deleted from Ollama and VRAM

### startup.py — LightRAG Startup Context Cache
- Pre-computed at shutdown via `python scripts/startup.py --precompute`
- Reads from cache file at startup — no LLM call, instant load
- Cache refreshed: 631 nodes, 293 edges in graph

### Key Config Values
- `CONFIDENCE_THRESHOLD = 7` (was 5 — too low, wrong answers scored above threshold)
- `OLLAMA_TIMEOUT = 20` (gemma inference hard cap)
- `_TIER_HARD_TIMEOUT = 8` (entire tier_query call — LightRAG + gemma — capped at 8s)
- `llm_model_max_async = 1` (RX 6600 can only run one concurrent LLM worker)
- `num_ctx = 8190` (hard cap everywhere — non-negotiable VRAM protection)

### ChatWorker Restored to Sonnet
- ChatWorker was incorrectly using Ollama/gemma chat as fallback
- Restored to Claude API (claude-sonnet-4-20250514) as Tier 3
- Gemma's role is ONLY inside tier_engine for Tier 2

### All gemma3:4b → gemma3:4b-cq Replacements
- main.py, vram_manager.py, forge_manager.py, coi_telegram_bot.py
- tools/graph_builder.py, tools/scan_script.py, tools/forge_pipeline.py
- forge_pipeline.py: num_ctx 16384 → 8192

### Zombie Process Fix
- 30+ coi_telegram_bot.py and forge_manager.py zombie processes found consuming CPU
- Root cause: repeated COI restarts without cleanup
- Killed manually this session

## Current Status

### Tier Engine — PARTIALLY WORKING
- Answers to all 3 test questions are CORRECT (vs Run 1 which were all wrong)
- Speed issue: tier_query LightRAG retrieval can hang without the 8s hard timeout
- 8s hard timeout added at end of session — NOT YET TESTED with Sonnet as Tier 3
- Response cache was masking test results — clear cache before every test run

### Test Protocol
1. Clear response cache: `rm scripts/response-cache.msgpack`
2. Restart COI
3. Ask: "What are you?", "What is the Forge?", "What is Codex Quantum?"
4. Check Dev panel TIER logs for routing
5. Check `logs/cq-writeback-log.jsonl` for Tier 3 write-backs

## Open Issues
- Tier engine timing: need to verify 8s timeout prevents hangs with new Sonnet Tier 3
- Write-back log still empty — need to confirm Sonnet write-back actually fires
- Subprocesses health check showing "warn" — zombie process cleanup needed at startup
- TTS repair still pending
- CC timeout root cause still undiagnosed

## Next Steps
1. Test with cache cleared + 8s timeout — verify no hang, check TIER logs in Dev panel
2. Confirm write-back fires when Tier 2 fails (check cq-writeback-log.jsonl)
3. Ask a question COI shouldn't know to force Tier 3 Sonnet → verify write-back
4. Once stable: run benchmark Tests A and B (V5 flat-file vs V6 LightRAG)
