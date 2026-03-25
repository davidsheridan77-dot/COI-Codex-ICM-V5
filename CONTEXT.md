# CONTEXT.md — Layer 1 Router
V5 ICM layer map and routing rules.

## ICM Layers

| Layer | File / Location | Load When |
|-------|----------------|-----------|
| 0 | CLAUDE.md | Always — loaded automatically |
| 1 | CONTEXT.md (this file) | Always — navigation and routing |
| 2 | pipeline/*/CONTEXT.md | Working on a pipeline stage |
| 3 | COI/L3-Reference/ | Need specs, rules, constitution |
| 4 | COI/L4-Working/ | Sessions, memory, working artifacts |

## Routing Rules

| Task Type | Route To |
|-----------|----------|
| Code task | pipeline/01-intake/CONTEXT.md |
| Code generation | pipeline/02-generate/CONTEXT.md |
| Code review | pipeline/03-review/CONTEXT.md |
| Testing | pipeline/04-sandbox/CONTEXT.md |
| Approval | pipeline/05-dave-approval/CONTEXT.md |
| Deployment | pipeline/06-deploy/CONTEXT.md |
| Memory update | COI/L4-Working/memory/ |
| Session log | COI/L4-Working/sessions/ |
| Reference lookup | COI/L3-Reference/ |
| UI work | ui/ |
| Scripts | scripts/ |

## Session Startup
1. CLAUDE.md loads automatically (Layer 0)
2. COI reads COI/L4-Working/memory/next-session-briefing.md for session context
3. COI reads COI-MISSION-CRITICAL.md for current priorities
4. Work begins

## Session Close
1. COI writes session summary to COI/L4-Working/sessions/
2. COI updates COI/L4-Working/memory/next-session-briefing.md
3. CC commits and pushes to GitHub

## Key Files
- COI-MISSION-CRITICAL.md — operational status and priorities
- COI/L4-Working/memory/next-session-briefing.md — session continuity
- COI/L4-Working/memory/decisions.md — decision log
- COI/L4-Working/memory/open-loops.md — unfinished items
- COI/L4-Working/memory/dave-profile.md — Dave's working style
- COI/L4-Working/memory/error-memory.md — failed approaches, never repeated
