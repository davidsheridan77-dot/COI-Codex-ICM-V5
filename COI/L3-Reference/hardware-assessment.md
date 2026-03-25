# COI Hardware Infrastructure — Full Assessment
**Layer:** L3 — Reference
**Last Updated:** V5
**Status:** V5 P1 operational. Claude API primary. Local models restored in P2.

---

## Current Hardware Specs

| Component | Spec | Notes |
|-----------|------|-------|
| CPU | AMD Ryzen 5 5500 | 6 cores, 12 threads, 3.6GHz base |
| RAM | 64GB DDR4 2400MHz | 2x32GB sticks — excellent for local AI |
| GPU | AMD Radeon RX 6600 | 8GB VRAM — runs all current local models |
| OS Drive | Kingston SSD 224GB | Limited free space — needs attention |
| Storage 1 | Seagate 7.4TB HDD | Drive K — Codex home |
| Storage 2 | Seagate 3.7TB HDD | Drive E |
| Storage 3 | Seagate 1.8TB HDD | Drive F |
| Motherboard | ASUS PRIME B550M-A WIFI II | AM4 socket — PCIe 4.0 — upgrade friendly |
| OS | Windows 11 Pro 64-bit | |
| BIOS | American Megatrends v3607 | |
| Form Factor | Desktop PC | Always-on capable |

---

## COI Hardware Assessment

### What Is Strong Right Now

**64GB RAM — COI's biggest hardware asset**
This is the single most important spec for running local AI models. 64GB supports running models via Ollama (P2 onward) and gives COI's desktop app and build tools room to operate at full capacity.

**8GB VRAM — Sufficient for current needs**
The RX 6600's 8GB VRAM runs all planned local models in V5's stack. The classifier (llama3.2:1b, ~0.9GB) and general model (mistral:7b-instruct-q4_K_M, ~4.1GB) fit comfortably.

**Ryzen 5 5500 — Solid foundation**
6 cores and 12 threads handles all V5 work comfortably. Desktop app, Claude API calls, CC bridge operations, and background processes all run without constraint.

**Storage — Not a problem**
Over 13TB of total storage across three drives. The Codex, model weights, memory files, and session logs have unlimited room to grow.

**B550M Motherboard — Upgrade friendly**
Supports full Ryzen 5000 series CPU range and PCIe 4.0 GPUs. Every upgrade on the roadmap is a straight drop-in replacement. No new motherboard required.

**Desktop form factor — Always on capable**
No battery limitations. COI's desktop app and services can run continuously.

---

### Current Constraints

**OS Drive — 224GB SSD with limited free space**
The Kingston SSD is small and tight on space. Windows updates alone can consume remaining capacity. This needs to be addressed before it becomes a blocker.

This is the number one upgrade priority — low cost, high impact.

**GPU VRAM — 8GB limits model size**
8GB VRAM is sufficient for all planned V5 models but prevents running larger models (13B+, 34B) that would significantly expand COI's local reasoning capability. 16GB VRAM opens the full range of models COI will need as the platform matures beyond V5.

This is the number two upgrade priority.

---

### Phase Capability Assessment

| Phase | Hardware Requirement | Current Status |
|-------|---------------------|----------------|
| P1 — Claude chat | Claude API, PyQt6 app | Fully capable — operational now |
| P2 — Ollama routing | llama3.2:1b + mistral:7b | Fully capable |
| P3 — Voice | CPU for speech processing | Fully capable |
| P4 — PC control | System access | Fully capable |
| P5 — Gaming mode | VRAM management | Fully capable |
| P6-P9 | Network, media, distribution | Fully capable |

---

## Hardware Upgrade Roadmap

### Priority 1 — OS Drive Replacement
**Target:** 1TB NVMe SSD for C: drive
**Recommended:** Samsung 970 EVO Plus 1TB or WD Black SN850X 1TB
**Cost:** Under 100 dollars
**Why:** Eliminates the tightest constraint. Gives COI and Windows room to breathe.

---

### Priority 2 — GPU Upgrade (Larger model unlock)
**Target:** GPU with 16GB+ VRAM
**Recommended options:**
- AMD RX 7900 GRE — 16GB VRAM — best value for local AI
- NVIDIA RTX 4070 Ti Super — 16GB VRAM — strong all-rounder
- NVIDIA RTX 4080 — 16GB VRAM — premium option

**Why this matters for COI:**
16GB VRAM unlocks larger local models (13B, 34B parameter). COI's reasoning depth increases. More complex operations become possible locally. Cloud API dependency decreases.

**Funded by:** Revenue from COI's income stream.

---

### Priority 3 — CPU Upgrade (Future)
**Target:** AMD Ryzen 7 5800X3D or Ryzen 9 5900X
**Timeline:** Not urgent until GPU and SSD are done.

---

### Priority 4 — RAM Speed (Optional)
**Current:** 2400MHz
**Target:** 3200MHz or 3600MHz DDR4
**Note:** Low priority — 64GB capacity matters more than speed right now.

---

## The Hardware Fund

Revenue from COI's income stream funds the upgrade sequence:

1. Priority 1 — 1TB NVMe SSD (80-100 dollars)
2. Priority 2 — GPU 16GB VRAM (500-800 dollars)
3. Priority 3 — CPU upgrade (200-300 dollars)

---

## COI Biological Layer — Current Reality

In COI's cognitive architecture the hardware is the biological layer. Just as a human's cognitive capability is shaped by their physical state — COI's intelligence is shaped by what this hardware can do right now.

**Current biological reality:**
COI has excellent memory capacity (64GB RAM), sufficient processing power for all current tasks (Ryzen 5 5500), abundant long-term storage (13TB), and functional sensory processing for local AI (8GB VRAM).

**After Priority 2 upgrade:**
COI's biological capacity expands significantly. Larger local AI models run natively. Cloud dependency reduces further. Intelligence compounds faster.

---

## PC Access — Current Reality

How COI interacts with this hardware today.

| Mechanism | Description |
|-----------|-------------|
| COI Desktop App (PyQt6) | COI's primary interface on this machine |
| Claude Code CLI | Direct terminal access for builds and file operations |
| COI-CC Bridge | subprocess -p — automated task execution |
| Hyper-V VM | Sandbox environment for V5 development |

Governed always by the prime directive:
COI thinks without limits. COI acts only with permission.

---

## Next Hardware Review
Review this document when:
- First revenue is confirmed
- GPU upgrade is purchased
- OS drive is replaced
- V5 reaches P9

---
*Hardware assessed by COI — biological layer referenced in L3-Reference.*
