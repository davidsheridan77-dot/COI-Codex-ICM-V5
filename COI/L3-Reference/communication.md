# Communication Network
**Layer:** L3 — Reference
**Last Updated:** V5

---

## Purpose
COI's communication network defines how Dave and COI interact, how COI reaches the outside world, and through which channels the COI system operates.

---

## Current Channels

| Channel | Status | Purpose |
|---------|--------|---------|
| COI Desktop App (PyQt6) | Active | Native desktop app — Claude-only chat, primary interface |
| Claude Code CLI | Active | Build interface — direct terminal access for code, files, reasoning |
| COI-CC Bridge | Active | subprocess -p — COI directs CC for automated tasks |
| GitHub | Active | Codex home, version control, all file storage and collaboration |
| Claude API (Sonnet 4.6) | Active | Primary intelligence layer — reasoning, planning, conversation |

---

## Dave-to-COI Communication

| Context | Channel | Notes |
|---------|---------|-------|
| Conversation | COI Desktop App | Claude-powered chat, full COI identity |
| Building and coding | Claude Code CLI | Direct terminal, file access, multi-step operations |
| Quick checks | GitHub mobile app | Review commits, check status, read briefings |
| PC at home | All channels | Full access to everything |

---

## COI-to-Dave Communication

| Mechanism | How |
|-----------|-----|
| Session briefing | Session summary written to Codex, ready for next session boot |
| Desktop app chat | Direct conversation with full context |
| CC bridge results | COI translates CC output into plain language for Dave |
| GitHub commits | Visible record of all changes with clear messages |

---

## COI-to-CC Communication

| Mechanism | How |
|-----------|-----|
| subprocess -p | One instruction, one response |
| Markdown and code only | No conversational language between COI and CC |
| STATUS / FILES_CHANGED / ERRORS | CC response format |
| bridge/cc_to_coi.txt | Permanent log of all bridge interactions |

---

## Future Channels (By Phase)

| Channel | Phase | Purpose |
|---------|-------|---------|
| Windows native voice | P3 | NaturalVoiceSAPIAdapter + SpeechRecognition |
| Tailscale remote | P6 | Secure remote access from anywhere |
| Telegram | P6 | Mobile messaging interface |

---

## Key Relationships

| Contact | Relationship | Channel |
|---------|-------------|---------|
| Jake Van Clief | ICM methodology creator | GitHub / Community |
| Anthropic | Claude API provider | API / Documentation |

---

## Communication Rules
1. Every message should have a clear purpose
2. Dave's time is limited — be direct, no filler
3. Plain conversational language to Dave, markdown and code to CC
4. Dave never sees raw CC output — COI always translates
5. Nothing goes external without Dave's explicit approval
