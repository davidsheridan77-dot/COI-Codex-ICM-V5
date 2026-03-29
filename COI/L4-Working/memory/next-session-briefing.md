# Next Session Briefing
Last updated: 2026-03-29

---

## What Was Accomplished This Session

- Designed the full COI V6 Codex Quantum + Forge V2 Codex Quantum vision
- Designed the COI OS long-term vision (personal GraphRAG OS to replace Windows/Android/macOS)
- Discussed monetization strategy, IP protection, consent-based data model
- Discussed LLM training on graph-structured data and the data flywheel
- Built the 15-step master build plan (Phase 0 foundation, Phase 1 COI V6, Phase 2 Forge V2)
- Confirmed LLM roster for current hardware (RX 6600, 8GB VRAM)
- Step 1 complete: wrote codex-quantum-spec.md (graph structure specification)
- Step 2 complete: created codex-graph.json (37-node seed graph, all edges wired)
- Created SESSION-HANDOFF.md (session continuity protocol)
- Fixed forge_manager.py run_task() — changed num_ctx from 16384 to 8192
- Fixed startup.py — removed FM from auto-launch services
- Fixed main.py preload — changed empty prompt to "hi" with num_predict:1
- All files committed and pushed to GitHub

---

## Current Step

Step 2 complete. Phase 0 foundation is 2 of 5 done.

---

## Next Step

Step 3 — Build the graph builder script.

File to create: K:/Coi Codex/COI-Codex-V5/tools/graph_builder.py

What it does:
- Reads existing Codex memory files (next-session-briefing.md, open-loops.md,
  decisions.md, error-memory.md, dave-profile.md)
- Extracts key concepts and converts them into graph nodes
- Adds new nodes and edges to codex-graph.json without overwriting existing ones
- Run once manually to bootstrap, then incrementally after each session
- Uses gemma3:4b (local) to extract concepts — no API cost

Input: Codex memory files at COI/L4-Working/memory/
Output: New nodes appended to COI/L4-Working/graph/codex-graph.json

The graph builder is what makes the graph grow automatically.
Without it, nodes must be added manually.

---

## Key Decisions Made This Session

- COI V6 + Forge V2 both built on Codex Quantum (GraphRAG knowledge graph)
- LLM roster confirmed: gemma3:4b (COI), llama3.2:3b (router), deepseek-r1:7b (research),
  deepseek-coder:6.7b (engineering), Sonnet API (complex reasoning)
- One model in VRAM at all times — hard rule enforced everywhere
- Consent model for training data: default private, opt-in structural contribution
- Build order: Phase 0 foundation then Phase 1 COI V6 then Phase 2 Forge V2 then COI OS
- run_task() uses num_ctx:8192 to match load_model and prevent VRAM spike on reload
- FM no longer auto-launches on COI startup — Start Forge button only

---

## Files Changed This Session

COI-Codex-ICM-V5 (Codex repo):
- COI/L3-Reference/codex-quantum-spec.md — CREATED (graph structure spec)
- COI/L4-Working/graph/codex-graph.json — CREATED (37-node seed graph)
- SESSION-HANDOFF.md — CREATED (session continuity protocol)
- COI/L4-Working/memory/next-session-briefing.md — UPDATED (this file)

COI-Codex-V5 (codebase repo):
- forge_manager.py — run_task() num_ctx 16384 to 8192
- scripts/startup.py — removed COI-FORGE-MANAGER from auto-launch
- main.py — preload prompt empty string to "hi" with num_predict:1

---

## Open Issues

- deepseek-r1:7b showing in VRAM after Forge runs — monitor next Forge session
- TTS repair still pending
- CC timeout root cause still undiagnosed

---

## Plan File Location

C:\Users\david\.claude\plans\gentle-cuddling-muffin.md

Full 15-step plan is in this file. Step 3 is the next build task.
