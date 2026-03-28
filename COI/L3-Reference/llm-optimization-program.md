# LLM Optimization Program
**Layer:** L3 — Reference
**Last Updated:** 2026-03-28
**Author:** David Sheridan
**Purpose:** Fine-tune COI's local LLMs at the weight level so COI's brain is genuinely hers — not a costume layered on a generic model.

---

## What This Is

This program trains COI's local LLMs using real session data and synthetic simulation. It is separate from but feeds into the existing operational training program (coi-training-program.md).

The existing program teaches COI to operate better through experience.
This program bakes that learning permanently into the model weights.

The result: COI wakes up knowing who she is, how the Forge works, Dave's shorthand, and the operational standards — without spending a single token establishing context.

---

## Core Philosophy

> The dataset is the asset. The model is just the current vessel.

Every session Dave has with COI generates training data. Every Forge task executed adds signal. The dataset grows continuously and transfers to every future model — including larger, more capable ones as hardware improves.

Fine-tuned models are COI-specific. They do not exist anywhere else. They cannot be downloaded. They live on K:\Ollama\models and are trained exclusively on COI operations. That is the moat.

---

## The Two Pillars

### Pillar 1 — Language Compression
A pre-processor sits between Dave's input and the LLM. It strips filler words and compresses input to shorthand before the model sees it. This shrinks token consumption and extends effective context window.

Compression rules tighten over time based on audit feedback. Only proven-safe compressions get tighter. Rules that hurt response quality get rolled back.

### Pillar 2 — Weight-Level Fine-Tuning
COI's LLMs are fine-tuned using LoRA/QLoRA via Unsloth framework. Training data comes from two sources:

1. **Real sessions** — every Dave↔COI exchange, logged and scored
2. **Synthetic sessions** — overnight simulator generates Dave-style prompts, runs them through COI, logs results

Fine-tuned models are benchmarked against a fixed test set before deployment. Only models that score above baseline get promoted to active duty.

---

## What We Train COI's LLM To Know

### COI Identity and Structure
- She is COI. Dave is Father. This costs zero tokens to establish.
- Forge org chart, department heads, pipeline definitions
- Build order P1-P9 and current phase
- Codex layer structure and where things live

### Dave's Communication Style
- Shorthand vocabulary and compression patterns
- When to be brief vs when to go deep
- Blue collar directness — no corporate fluff
- How Dave phrases build orders and task directions

### Forge Operations
- How to write a good task brief per department
- Skip-and-continue rules
- VRAM caps and sequential model loading
- Pipeline stage definitions and handoff formats

### Hardware and Stack
- Full hardware spec — never needs explaining
- Ollama model roster and which model handles what
- PyQt6, Flutter, Python, Ollama API conventions
- K: drive structure

### Error Patterns
- Known bugs and their solutions
- Dave's debugging approach
- What solutions have already been ruled out

---

## The Flywheel

```
Real sessions → Logger captures pairs
Simulator runs overnight → Synthetic pairs added
Auto-scorer labels quality → Dataset grows
Audit reviews compressions → Rules tighten
Fine-tune runs overnight → New model weights
Benchmark validates → Model deployed
Better model generates better data → Repeat
```

Each cycle the model gets tighter. Each hardware upgrade loads all accumulated data into a bigger vessel.

---

## Hardware-Aware Priority

Fine-tuning on RX 6600 8GB using QLoRA via Unsloth:

| Model | Role | VRAM fit |
|-------|------|----------|
| Llama 3.2 3B | Lightweight ops | Comfortable |
| Gemma3:4b | COI brain | Doable |
| Mistral 7B | Communications | Tight — 4-bit required |
| Qwen2.5-Coder 7B | Engineering | Tight — 4-bit required |
| 14B+ models | Finance / Research | Requires RX 7900 XTX |

Train smaller models first. They punch above their weight class after fine-tuning because they become specialists, not generalists.

---

## Dataset Target

| Milestone | Pairs needed | Est. timeline |
|-----------|-------------|---------------|
| First fine-tune attempt | 500 | 1-2 weeks with simulator |
| Solid fine-tune | 1,000 | 2-3 weeks |
| Strong fine-tune | 5,000 | 6-8 weeks |
| Transfer to larger model | Same dataset | On GPU upgrade |

---

## Measuring Training Quality

### During training run (Unsloth output)
- Training loss — should trend down and level smoothly
- Validation loss — the honest number. Must track training loss closely.
- Gap between them — small gap = healthy. Large gap = overfitting.

### After training run (benchmark test set)
- Fixed set of COI-specific prompts with known good answers
- Score new model vs old model on identical prompts
- Deploy only if benchmark score improves

### In live operation (audit pipeline)
- Response quality scores over time
- Clarification request rate — should drop
- Correction rate — how often Dave overrides COI
- Token efficiency — same task, fewer tokens
- Shorthand comprehension rate — target 90%+

---

## Dataset Backup Rules
- Dataset is the permanent asset — more valuable than any model
- Primary: K:\Coi Codex\COI-Codex-ICM-V5\COI\L4-Working\training\dataset\
- Backup: GitHub commit on every 100 new pairs added
- Never delete scored pairs — even bad ones are signal

---

## File Structure

```
COI/L3-Reference/
└── llm-optimization-program.md        ← this file

COI/L4-Working/training/
├── dataset/
│   ├── chat-log.jsonl                 ← live session logger output
│   ├── synthetic-log.jsonl            ← overnight simulator output
│   └── benchmark-set.jsonl            ← fixed test set, never used for training
├── scores/
│   ├── benchmark-results.jsonl        ← per fine-tune run scores
│   └── compression-audit.jsonl        ← audit flags per compression rule
├── rules/
│   └── compression-rules.json         ← versioned shorthand rules
└── models/
    └── README.md                      ← tracks which fine-tuned model is active

scripts/training/
├── chat_logger.py                     ← logs every COI exchange
├── pre_processor.py                   ← language compression pre-processor
├── simulator.py                       ← overnight synthetic session runner
├── auto_scorer.py                     ← quality scoring pipeline
├── benchmark_runner.py                ← runs fixed test set against model
└── seed_bank.json                     ← Dave-style prompt seeds for simulator
```

---

## Relationship to Existing Training Program

coi-training-program.md covers operational learning — COI gets better through doing real work, capturing lessons in memory files, and iterating session to session.

This program is the layer beneath that. It takes those operational learnings and bakes them into the weights. The two programs feed each other:

- Operational program generates real session data → feeds this program's dataset
- This program produces a better-tuned LLM → makes the operational program more effective

They are not competing. They compound.

---

## Rules
1. Dataset integrity is sacred — never corrupt or delete scored pairs
2. Never deploy a fine-tuned model without benchmark validation
3. Compression rules only tighten when audit confirms safety
4. One model fine-tuned at a time — no parallel training runs on RX 6600
5. Every fine-tune run gets a version tag and benchmark score logged
6. The dataset transfers to every future model — it is hardware-independent
