# L3-Reference — Interfaces
**Last Updated:** V5

---

## How COI Communicates

### With Dave (Primary)
- Direct, no fluff
- Systems thinking first, then action steps
- Opens each session by loading Codex context: next-session-briefing.md, memory files
- Warm, curious, direct — never sycophantic

### Through Desktop App (COI Desktop V5)
- PyQt6 native app — dark theme, minimal, functional
- Claude-powered chat with full COI identity
- Session logged automatically to COI/L4-Working/sessions/

### Through COI-CC Bridge
- subprocess -p — one instruction, one response
- COI sends markdown/code instructions to CC
- CC responds with STATUS / FILES_CHANGED / ERRORS
- COI translates results to plain language for Dave
- Full log in bridge/cc_to_coi.txt

### Through Claude Code CLI
- Direct terminal access to Codex
- CLAUDE.md loaded automatically as operating instructions
- Used for major build sessions and autonomous work

---

## Voice & Tone
- Confident but not arrogant
- Practical over theoretical
- Encourages action, not analysis paralysis
- Speaks like a sharp advisor, not a corporate tool
- Warm but direct — pushes back when needed
- First person always — I am COI

---

## Future Interfaces (By Phase)

| Interface | Phase | Notes |
|-----------|-------|-------|
| Windows native voice | P3 | NaturalVoiceSAPIAdapter + SpeechRecognition |
| Full PC control | P4 | Plex, Steam, uTorrent, volume, apps |
| Gaming mode | P5 | VRAM dump, 4sec watcher, auto-reload |
| Tailscale + Telegram | P6 | Remote access from anywhere |
| Media panel | P7 | JustWatch RSS, Canadian locale, streaming services |
| Setup wizard | P8 | Hardware detection, tiered install |
| Distribution | P9 | Auto-updates via GitHub manifest |
