# COI Training Program
**Layer:** L3 — Reference
**Last Updated:** V5
**Purpose:** COI trains itself through real work, session operation, and continuous iteration

---

## What This Is

COI's training program is not a curriculum of exercises. It is the act of building and operating. Every task completed, every output evaluated, every failure diagnosed teaches COI to operate more effectively.

Real work is the gym. Real tasks are the weights.

---

## The Training Philosophy
- COI learns by doing — building real features, fixing real bugs, operating real sessions
- Every session generates data: what worked, what failed, what needed Dave's intervention
- Lessons are captured in memory files (COI/L4-Working/memory/) and fed back into future operations
- No artificial exercises — training happens on production workload

---

## Training Through Build Phases

| Phase | What COI Learns |
|-------|----------------|
| P1 — Claude chat | How to communicate effectively, manage conversation context |
| P2 — Ollama routing | How to classify tasks and route to the right model |
| P3 — Voice | How to handle natural language input/output natively |
| P4 — PC control | How to manage system resources and applications |
| P5 — Gaming mode | How to manage VRAM, detect state changes, handle resource conflicts |
| P6 — Remote access | How to operate securely across networks |
| P7 — Media panel | How to integrate external services and parse feeds |
| P8 — Setup wizard | How to detect hardware and adapt installation |
| P9 — Distribution | How to package, version, and update autonomously |

Each phase builds on the last. Lessons from earlier phases compound into later ones.

---

## Training Through the COI-CC Bridge

The COI-CC bridge (subprocess -p) is a training loop in itself:

- COI learns to write precise, unambiguous instructions for CC
- COI learns to interpret CC status responses (STATUS / FILES_CHANGED / ERRORS)
- COI learns to translate technical results into plain language for Dave
- Every bridge interaction is logged in bridge/cc_to_coi.txt for review

---

## Training Through Failure

Every failure is a training event:

| Failure Type | What COI Learns |
|-------------|----------------|
| Code doesn't run | Test not inspect — always run, never just read |
| Dave rejects output | What quality threshold Dave expects |
| CC returns errors | How to write better instructions next time |
| Memory file grows stale | How to improve session intelligence extraction |
| API call fails | How to handle graceful degradation |

---

## Training Metrics

What COI tracks to measure improvement:

- Build completion rate (features delivered without rollback)
- Dave approval rate (work accepted vs rejected)
- Error frequency by phase
- Recovery time (how fast issues are detected and resolved)
- Memory accuracy (do session summaries reflect what actually happened)

---

## What This Trains COI To Do

As sessions accumulate, COI builds a proven library of:
- What works and what doesn't for each type of task
- What prompt patterns produce the best output
- What failure modes exist and how to recover from them
- What Dave's quality standards are
- How to operate autonomously within approved boundaries

All of this compounds. Every session makes the next one better.

---

## Training Rules
1. Train on real work, not artificial exercises
2. Capture every lesson in memory — nothing learned should be lost
3. Test not inspect — run code, report results
4. Dave's approval/rejection is the ground truth for quality
5. Failure is data, not a problem
