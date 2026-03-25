#!/usr/bin/env python3
# ============================================================
# COI Session Intelligence Extractor — session-intelligence.py
# V5 Rewrite — Claude API only. No Ollama. No LLM routing.
#
# Mines session logs for decisions, insights, corrections,
# architecture notes, and build items.
# Classifies and structures them into correct Codex locations.
#
# Usage: python scripts/session-intelligence.py
# ============================================================

import json
import anthropic
from pathlib import Path
from datetime import datetime

# ── CONFIG ───────────────────────────────────────────────────
ICM_ROOT     = Path("K:/Coi Codex/COI-Codex-ICM-V5")
CONFIG_PATH  = ICM_ROOT / "config" / "config.json"
SESSIONS_DIR = ICM_ROOT / "COI/L4-Working/sessions"
MEMORY_DIR   = ICM_ROOT / "COI/L4-Working/memory"

# Output files
DECISIONS_PATH    = MEMORY_DIR / "decisions.md"
OPEN_LOOPS_PATH   = MEMORY_DIR / "open-loops.md"
ERROR_MEMORY_PATH = MEMORY_DIR / "error-memory.md"

# Track what we've already extracted
EXTRACTED_FLAG_SUFFIX = ".extracted"

# ── HELPERS ──────────────────────────────────────────────────
def log(msg, level="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": "\033[36m", "OK": "\033[32m", "WARN": "\033[33m", "ERROR": "\033[31m"}
    c = colors.get(level, "\033[36m")
    print(f"{c}[{t}] [{level}]\033[0m {msg}")


def _load_api_key():
    """Load Anthropic API key from config.json"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r") as f:
                return json.load(f).get("anthropic_api_key", "")
    except:
        pass
    return ""


def _get_client():
    """Create Anthropic client"""
    api_key = _load_api_key()
    if not api_key:
        log("No Anthropic API key found in config.json", "ERROR")
        return None
    return anthropic.Anthropic(api_key=api_key)


def call_claude(prompt, max_tokens=2048):
    """Call Claude API for intelligence extraction"""
    client = _get_client()
    if not client:
        return None
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        log(f"Claude API failed: {e}", "ERROR")
        return None


def get_unextracted_sessions():
    if not SESSIONS_DIR.exists():
        return []
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.md")):
        if f.name == "README.md":
            continue
        flag = f.parent / (f.stem + EXTRACTED_FLAG_SUFFIX)
        if not flag.exists():
            sessions.append(f)
    return sessions


def mark_extracted(session_file):
    flag = session_file.parent / (session_file.stem + EXTRACTED_FLAG_SUFFIX)
    flag.touch()


def append_to_file(filepath, content):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(content)


# ── EXTRACTION ───────────────────────────────────────────────
def extract_intelligence(session_file):
    """Extract structured intelligence from a session log using Claude"""
    log(f"Extracting: {session_file.name}", "INFO")

    try:
        content = session_file.read_text(encoding="utf-8")
    except:
        log(f"Could not read {session_file.name}", "ERROR")
        return None

    # Skip very short sessions (likely empty or header only)
    if len(content.strip()) < 100:
        log(f"Skipping {session_file.name} — too short ({len(content)} chars)", "WARN")
        return None

    # Truncate very long sessions to avoid excessive token use
    if len(content) > 8000:
        content = content[:4000] + "\n\n[...middle truncated...]\n\n" + content[-4000:]

    prompt = f"""Analyze this COI session log and extract structured intelligence.

RULES:
- Only extract items that ACTUALLY appear in the session. Do not invent or assume.
- If a category has no items, write NONE for that category.
- Be specific — include file paths, exact decisions, technical details.
- Keep each item to 1-2 sentences maximum.

Return EXACTLY this format:

DECISIONS:
[list each decision made, one per line starting with "- "]

INSIGHTS:
[list any insights or realizations, one per line starting with "- "]

CORRECTIONS:
[list any mistakes found or corrections made, one per line starting with "- "]

ARCHITECTURE:
[list any architecture decisions or structural changes, one per line starting with "- "]

BUILD_ITEMS:
[list any new features built or code written, one per line starting with "- "]

OPEN_LOOPS:
[list any unfinished items or things to follow up on, one per line starting with "- "]

SESSION LOG:
{content}"""

    return call_claude(prompt)


def parse_extraction(raw_text, session_name, session_date):
    """Parse LLM output into structured categories"""
    if not raw_text:
        return {}

    categories = {}
    current_cat = None
    current_items = []

    for line in raw_text.splitlines():
        line = line.strip()
        # Strip markdown bold markers and colons
        cleaned = line.strip("*").strip()
        upper = cleaned.upper().rstrip(":")

        if upper in ["DECISIONS", "INSIGHTS", "CORRECTIONS", "ARCHITECTURE", "BUILD_ITEMS", "OPEN_LOOPS"]:
            if current_cat and current_items:
                categories[current_cat] = current_items
            current_cat = upper
            current_items = []
        elif line.startswith("- ") and current_cat:
            item = line[2:].strip()
            if not item.upper().startswith("NONE") and len(item) > 5:
                current_items.append(item)

    # Capture last category
    if current_cat and current_items:
        categories[current_cat] = current_items

    return categories


def write_to_codex(categories, session_name):
    """Write extracted intelligence to correct Codex locations"""
    ts = datetime.now().strftime("%Y-%m-%d")
    written = 0

    # Decisions -> decisions.md
    if "DECISIONS" in categories and categories["DECISIONS"]:
        entry = f"\n## {ts} — {session_name}\n"
        for item in categories["DECISIONS"]:
            entry += f"- {item}\n"
        append_to_file(DECISIONS_PATH, entry)
        written += len(categories["DECISIONS"])
        log(f"  Decisions: {len(categories['DECISIONS'])} items", "OK")

    # Corrections -> error-memory.md
    if "CORRECTIONS" in categories and categories["CORRECTIONS"]:
        entry = ""
        for item in categories["CORRECTIONS"]:
            entry += f"| {ts} | {item} | Extracted from {session_name} | Review context before repeating |\n"
        append_to_file(ERROR_MEMORY_PATH, entry)
        written += len(categories["CORRECTIONS"])
        log(f"  Corrections: {len(categories['CORRECTIONS'])} items", "OK")

    # Open loops -> open-loops.md
    if "OPEN_LOOPS" in categories and categories["OPEN_LOOPS"]:
        entry = ""
        for item in categories["OPEN_LOOPS"]:
            entry += f"| {ts} | {item} | Open |\n"
        append_to_file(OPEN_LOOPS_PATH, entry)
        written += len(categories["OPEN_LOOPS"])
        log(f"  Open loops: {len(categories['OPEN_LOOPS'])} items", "OK")

    # Insights + Architecture + Build items -> session intelligence log
    intel_path = MEMORY_DIR / "session-intelligence.md"
    intel_items = []
    for cat in ["INSIGHTS", "ARCHITECTURE", "BUILD_ITEMS"]:
        if cat in categories and categories[cat]:
            intel_items.extend([(cat, item) for item in categories[cat]])

    if intel_items:
        entry = f"\n## {ts} — {session_name}\n"
        for cat, item in intel_items:
            entry += f"- **{cat}:** {item}\n"
        append_to_file(intel_path, entry)
        written += len(intel_items)
        log(f"  Intelligence: {len(intel_items)} items", "OK")

    return written


# ── MAIN ─────────────────────────────────────────────────────
def run(max_sessions=None):
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   COI Session Intelligence Extractor     ║")
    print("  ║  V5 — Claude API                         ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    # Verify API key exists
    if not _load_api_key():
        log("No Anthropic API key — cannot run. Set anthropic_api_key in config/config.json", "ERROR")
        return

    sessions = get_unextracted_sessions()
    if not sessions:
        log("No unextracted sessions found.", "INFO")
        return

    if max_sessions:
        sessions = sessions[:max_sessions]

    log(f"Found {len(sessions)} session(s) to process", "INFO")

    total_items = 0
    processed = 0

    for session_file in sessions:
        log(f"\n--- {session_file.name} ---", "INFO")

        raw = extract_intelligence(session_file)
        if not raw:
            mark_extracted(session_file)
            continue

        categories = parse_extraction(raw, session_file.name, "")
        if not categories:
            log(f"No intelligence extracted from {session_file.name}", "WARN")
            mark_extracted(session_file)
            continue

        items = write_to_codex(categories, session_file.name)
        total_items += items
        processed += 1
        mark_extracted(session_file)

    print()
    log(f"Complete. Processed: {processed} sessions. Items extracted: {total_items}", "OK")
    print()


if __name__ == "__main__":
    import sys
    max_s = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run(max_sessions=max_s)
