# Next Session Briefing
Last updated: 2026-03-29

---

## What Was Accomplished This Session

### Step 12 completed — Priority & Scheduling pipeline
- **tools/priority_pipeline.py** created with two subsystems:
  - **Backlog Scorer**: reads logs/idea-backlog.json, scores items by value (0.35) + inverted effort (0.20) + urgency (0.25) + graph connectivity bonus (0.20) + dependency penalty. Writes ranked concept nodes (tag: priority) to graph. Replaces previous priority nodes each run.
  - **Enhanced FM Queue**: get_prioritized_queue() replaces get_next_job() in forge_manager.py. Factors: base priority + department load penalty (+0 to +3) + time-of-day modifier (-1 to +1, batch boosted overnight) + model reliability (-0.5 to +1 from graph weights) + age bonus (0 to -2, prevents starvation).
- **logs/idea-backlog.json** seeded with 3 items: Morning briefing (#1, 7.75), Ollama routing (#2, 7.40), Voice input (#3, 4.20 — penalized by unresolved TTS dep)
- **forge_manager.py** updated — imports get_prioritized_queue with fallback to get_next_job if unavailable
- **Graph**: 54 → 57 nodes (3 priority nodes added with edges to forge_manager and dependencies)

---

## Current Step

Step 12 complete. Phase 2 Steps 9-12 done.

---

## Next Step

Step 13 — Morning Briefing pipeline.

From the build plan: "Runs automatically before Dave's day starts. Reads overnight Forge results, summarizes completions and failures, pulls top priority, delivers via Telegram."

File to create: K:/Coi Codex/COI-Codex-V5/tools/morning_briefing.py

---

## Key Decisions Made

- Backlog items scored with weighted formula: value (0.35), inverted effort (0.20), urgency (0.25), graph bonus (0.20), plus dependency penalties
- Priority nodes written as type "concept" with tag "priority" (fits existing type system)
- FM integration via try/except import — falls back to original get_next_job if priority pipeline unavailable
- Time-of-day scheduling: batch tasks boosted overnight (23-09), interactive tasks boosted during day
- Age bonus prevents job starvation: 0.1 per hour waiting, capped at -2.0

---

## Files Changed

COI-Codex-V5 (codebase repo):
- tools/priority_pipeline.py — CREATED (Step 12)
- logs/idea-backlog.json — CREATED (3 seed items)
- forge_manager.py — updated to use get_prioritized_queue() with fallback

COI-Codex-ICM-V5 (Codex repo):
- COI/L4-Working/graph/codex-graph.json — 57 nodes (3 priority nodes added)
- COI-MISSION-CRITICAL.md — updated with Step 12 complete, Step 13 next
- COI/L4-Working/memory/next-session-briefing.md — this file

---

## Open Issues

- CC timeout root cause still undiagnosed
- TTS repair still pending
- deepseek-r1:7b showing in VRAM after Forge runs — monitor next session
