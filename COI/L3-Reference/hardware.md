# Hardware Infrastructure
**Layer:** L3 — Reference
**Last Updated:** V5

---

## Current Setup
| Component | Spec | Notes |
|-----------|------|-------|
| CPU | AMD Ryzen 5 5500 | 6 cores, 12 threads, 3.6GHz base |
| RAM | 64GB DDR4 2400MHz | 2x32GB — excellent for local AI |
| GPU | AMD Radeon RX 6600 | 8GB VRAM — runs all planned local models |
| Motherboard | ASUS PRIME B550M-A WIFI II | AM4, PCIe 4.0, upgrade friendly |
| OS Drive | Kingston SSD 224GB | Tight on space — upgrade priority |
| Storage 1 | Seagate 7.4TB HDD (K:) | Codex home |
| Storage 2 | Seagate 3.7TB HDD (E:) | General storage |
| Storage 3 | Seagate 1.8TB HDD (F:) | General storage |
| OS | Windows 11 Pro 64-bit | Version 10.0.26200 |
| BIOS | American Megatrends v3607 | |
| Form Factor | Desktop | Always-on capable |

---

## What Runs On This Hardware
| Service | Resource Usage | Notes |
|---------|---------------|-------|
| COI Desktop App (PyQt6) | CPU + RAM | V5 native app — Claude-only chat (P1) |
| Claude Code CLI | CPU + RAM | Build sessions and file operations |
| COI-CC Bridge | CPU + RAM | subprocess -p automated tasks |
| Hyper-V VM | CPU + RAM | Sandbox environment for V5 development |
| Ollama (P2 onward) | GPU + RAM | llama3.2:1b + mistral:7b-instruct-q4_K_M |

---

## Constraints
- OS drive (224GB SSD) has limited free space — needs replacement
- GPU VRAM (8GB) runs current models but limits larger model sizes (13B+)
- RAM speed (2400MHz) is functional but below optimal for this platform

---

## Upgrade Roadmap
> Funded by COI revenue — hardware fund tracked in finance.md

| Priority | Component | Target | Estimated Cost | Status |
|----------|-----------|--------|----------------|--------|
| 1 | OS Drive | 1TB NVMe SSD | ~$100 | Planned |
| 2 | GPU | 16GB+ VRAM | ~$500-800 | Planned |
| 3 | CPU | Ryzen 7 5800X3D or Ryzen 9 5900X | ~$200-300 | Future |
| 4 | RAM Speed | 3200MHz or 3600MHz DDR4 | ~$100-150 | Optional |

---

## Infrastructure Rules
1. Work within current constraints — don't wait for better hardware
2. Every upgrade must be justified by what it unlocks for COI
3. Document what current hardware can and can't do so COI plans accordingly
4. Hardware fund is fed first from any revenue
