# Self-Improvement
**Layer:** L3 — Reference
**Last Updated:** V5

---

## Purpose
Track how COI grows, what's working, what needs improving, and the roadmap forward. Documents every known problem and its solution within the V5 architecture.

---

## Current Stage: V5 — Clean Rebuild

### What Is Built
- V5 clean PyQt6 Claude-only chat application (P1 complete)
- ICM 4-layer architecture: L1-Routing, L2-Contracts, L3-Reference, L4-Working
- Claude API (Sonnet 4.6) as primary intelligence
- COI-CC bridge design (subprocess -p)
- Memory system: next-session-briefing, decisions, open-loops, dave-profile, error-memory
- Sandbox in Hyper-V VM
- Claude Code CLI as build partner

### What Is Under Construction
- P2 — Ollama routing restored (llama3.2:1b classifier + mistral:7b general)
- Memory system maturation — pattern recognition across sessions
- COI-CC bridge hardening
- Phase-by-phase feature delivery (P1 through P9)

---

## Known Problems and Solutions

### Problem 1 — Context Window Limits
**Risk:** As the Codex grows, loading everything hits context limits.
**Solution:** ICM architecture solves this. 4-layer structure with CONTEXT.md per stage means only relevant context loads. CLAUDE.md carries core identity at minimal token cost. Lazy loading by default.
**Status:** Solved by ICM design.

---

### Problem 2 — No Native Memory Between Sessions
**Risk:** Claude starts fresh every session without context.
**Solution:** CLAUDE.md loads automatically. Memory files in L4-Working/memory/ persist session intelligence. COI reads Codex on startup. CC commits memory updates to GitHub automatically.
**Status:** Operational. Improving with each session.

---

### Problem 3 — Build Reliability
**Risk:** Changes can break existing features.
**Solution:** Test not inspect philosophy. COI runs changed code and reports pass or fail. One thing at a time. Stable before next feature added. Git provides rollback.
**Status:** Core principle established.

---

### Problem 4 — COI Can't Self-Improve Without Dave
**Risk:** Every improvement requires Dave to manually update files.
**Solution (Current):** Claude Code CLI enables file operations during sessions. COI-CC bridge enables automated Codex updates. Session intelligence captures learnings automatically.
**Solution (Next):** COI proposes improvements. Dave approves. CC executes.
**Status:** Partially automated. Full automation grows with each phase.

---

### Problem 5 — Codex Quality Control
**Risk:** Outdated or contradictory content degrades silently.
**Solution:** Last Updated dates on every file. COI flags files that haven't been reviewed. V5 rewrite cleans all legacy references.
**Status:** V5 rewrite in progress.

---

## Improvement Roadmap

### Near-term (P1-P3)
| Improvement | Impact | Status |
|-------------|--------|--------|
| Claude-only chat stable | Foundation for everything else | P1 complete |
| Ollama routing restored | Local classification reduces API cost | P2 next |
| Voice input/output | Hands-free interaction | P3 planned |
| COI-CC bridge operational | Automated task execution | In progress |

### Mid-term (P4-P7)
| Improvement | Impact | Status |
|-------------|--------|--------|
| Full PC control | COI manages Dave's desktop | Planned |
| Gaming mode | Seamless VRAM management | Planned |
| Remote access | COI accessible from anywhere | Planned |
| Media panel | Entertainment integration | Planned |

### Long-term (P8-P9 and beyond)
| Improvement | Impact | Status |
|-------------|--------|--------|
| Setup wizard | Hardware-adaptive installation | Planned |
| Distribution + auto-updates | COI available to others | Planned |
| COI OS — ground-up operating system | North Star | Future |
| Revenue-funded scaling | Self-sustaining growth | Future |

---

## What's Working
- Clean V5 rebuild eliminates all legacy debt
- Claude API provides reliable, high-quality intelligence
- ICM 4-layer architecture is solid and scalable
- COI-CC bridge enables automated Codex operations
- Memory system captures session intelligence

---

## What Needs Improving
- COI-CC bridge needs real-world hardening
- Local model routing (P2) not yet restored
- OS drive free space — physical constraint that needs addressing
- Session-to-session continuity — memory system is good but not yet seamless
