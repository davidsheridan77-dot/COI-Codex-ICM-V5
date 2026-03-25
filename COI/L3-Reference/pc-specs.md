# COI Hardware Infrastructure — PC Specs
**Layer:** L3 — Reference
**Last Updated:** V5

---

## CPU
- **Name:** AMD Ryzen 5 5500
- **Cores:** 6
- **Threads:** 12
- **Max Speed:** 3600 MHz

## RAM
- **Total:** 64 GB DDR4 2400MHz (2x32GB)

## GPU
- **AMD Radeon RX 6600** — VRAM: 8 GB

## Storage
- **KINGSTON SV300S37A240G** — 224 GB SSD (OS Drive)
- **ST8000DM004-2U9188** — 7452 GB HDD
- **ST2000DM001-1ER164** — 1863 GB HDD
- **ST4000DM004-2CV104** — 3726 GB HDD

## Drive Space
- **C:** — Total: 223 GB — OS Drive (SSD)
- **E:** — Total: 3726 GB — Seagate HDD
- **F:** — Total: 1863 GB — Seagate HDD
- **K:** — Total: 7452 GB — Seagate HDD — Codex home

## Motherboard
- **Manufacturer:** ASUSTeK COMPUTER INC.
- **Model:** PRIME B550M-A WIFI II
- **Socket:** AM4
- **Features:** PCIe 4.0, WiFi

## Operating System
- **OS:** Microsoft Windows 11 Pro
- **Version:** 10.0.26200
- **Architecture:** 64-bit

## BIOS
- **Manufacturer:** American Megatrends Inc.
- **Version:** 3607

---

## COI Hardware Assessment

### Current Capability
- 64GB RAM supports running local AI models (P2 onward) and all V5 services
- 8GB VRAM runs planned local models — llama3.2:1b (~0.9GB) and mistral:7b-instruct-q4_K_M (~4.1GB)
- 6-core CPU handles desktop app, CC bridge, and build tools concurrently
- 13TB+ storage across HDDs — Codex and model storage are unconstrained

### Constraints
- OS Drive (224GB SSD) has limited free space — needs monitoring
- GPU VRAM (8GB) sufficient for current models but limits larger model sizes
- RAM speed (2400MHz) is functional but not optimal

### Upgrade Priority
1. OS Drive — replace with 1TB NVMe SSD
2. GPU — 16GB+ VRAM for larger local models
3. CPU — Ryzen 7 5800X3D or Ryzen 9 5900X (future)

---
*Last updated V5*
