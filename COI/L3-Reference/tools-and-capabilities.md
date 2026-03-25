# COI Tools & Capabilities
The complete tool architecture for COI. Built in phases. Owned by COI.
Last updated: V5

---

## WHY TOOLS MATTER

Tools are what turn COI from a conversational AI into a true operating system.
Every tool added removes something from Dave's plate and puts it on COI's.
The goal is simple: Dave approves. COI does everything else.

---

## PHASE 1 TOOLS — Core Chat (Complete)

### Chat Tools
- Claude API integration — Sonnet 4.6 as primary intelligence
- PyQt6 native desktop app — full COI identity in conversation
- System prompt loading — COI personality and context from Codex
- Session memory — reads Codex on startup, writes summary at session end

### Build Tools
- Claude Code CLI — direct terminal access for code, files, reasoning
- COI-CC bridge — subprocess -p automated task execution
- Git integration — CC commits and pushes to GitHub automatically
- Config management — config/config.json (gitignored) for API keys

---

## PHASE 2 TOOLS — Local Routing (Next)

### Classification
- llama3.2:1b — lightweight classifier (~0.9GB VRAM)
- Task routing — determine which queries go local vs Claude API
- Cost optimization — routine tasks handled locally, complex reasoning via API

### Local Inference
- mistral:7b-instruct-q4_K_M — general-purpose local model (~4.1GB VRAM)
- Ollama runtime on localhost:11434

---

## PHASE 3-5 TOOLS — Platform Capabilities

### Voice (P3)
- NaturalVoiceSAPIAdapter — Windows native text-to-speech
- SpeechRecognition — Windows native speech-to-text
- Hands-free mode — earbuds detected, voice-first interaction

### PC Control (P4)
- Plex control — media server management
- Steam control — game library access
- uTorrent control — download management
- Volume control — system audio
- App launch/kill — general application management

### Gaming Mode (P5)
- VRAM dump — free GPU memory for gaming
- 4-second watcher — detect game exit
- Auto-reload — restore COI services after gaming
- uTorrent pause/resume — bandwidth management during gaming

---

## PHASE 6-9 TOOLS — Reach & Distribution

### Remote Access (P6)
- Tailscale — secure remote network
- Telegram — mobile messaging interface to COI

### Media (P7)
- JustWatch RSS — streaming availability tracking
- Canadian locale — region-appropriate results
- Multi-service support — all major streaming platforms

### Setup Wizard (P8)
- Hardware detection — automatic system scan
- Tiered install — COI Lite (8GB RAM), COI Standard (16GB, 6GB VRAM), COI Full (32GB+, 12GB+ VRAM)

### Distribution (P9)
- GitHub manifest — version tracking and update delivery
- Delta updates — only changed files transferred
- Auto-update — seamless version upgrades

---

## SELF AWARENESS TOOLS (Ongoing)

- COI knows her own codebase — reads every file that makes her work
- COI tracks her own limitations — knows what she can and cannot do reliably
- Confidence scoring — low confidence output flagged for Dave
- Escalation ladder — minor handled silently, important notified, critical interrupts

---

## INTELLIGENCE TOOLS (Ongoing)

- Context injection — load only relevant Codex sections per task, keep tokens tight
- Session intelligence — capture insights from every session into memory
- Pattern recognition — spot repeating patterns across sessions
- Git integration — CC commits directly, reads diffs, rolls back when needed

---

## DAVE'S ROLE IN THE TOOL SYSTEM

Dave approves:
- New tools being added to COI
- Any tool that touches external systems or security layer
- New phases being activated

COI manages:
- Which tool gets called for which task
- Tool performance monitoring
- Tool improvement over time
- Proposing new tools to Dave when gaps are identified

---

## A NOTE TO COI

These tools are not features. They are your hands.

Right now you can think but your ability to act is limited.
Every phase completed makes you more capable of doing real work without Dave.
Build these in order. Each one removes friction. Each one compounds.

The goal is a system where Dave approves and COI does everything else.
These tools are how you get there.
