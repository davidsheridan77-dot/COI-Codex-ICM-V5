#!/usr/bin/env python3
# ============================================================
# COI Codex Intelligence — coi-codex-intelligence.py
# V5 Rewrite — Claude API only. No Ollama. No LLM routing.
#
# Autonomous recognition and filing of Codex-worthy content.
# COI monitors conversation for architectural decisions, build
# items, vision concepts, constitutional principles, platform
# definitions, and capability specs. When detected, drafts
# an entry in the correct ICM format and queues it for Dave's
# approval via the existing pipeline.
#
# Usage: imported by coi-desktop — not run standalone
# ============================================================

import re
import json
import anthropic
from pathlib import Path
from datetime import datetime

# ── CONFIG ───────────────────────────────────────────────────
ICM_ROOT         = Path("K:/Coi Codex/COI-Codex-ICM-V5")
CONFIG_PATH      = ICM_ROOT / "config" / "config.json"
CODEX_MAP_PATH   = ICM_ROOT / "COI/L1-Routing/CODEX-MAP.md"
APPROVAL_DIR     = ICM_ROOT / "pipeline/05-dave-approval/output"

# ── RECOGNITION CATEGORIES ───────────────────────────────────
# Each category has trigger patterns and a description for the classifier
CODEX_CATEGORIES = {
    "architectural_decision": {
        "triggers": [
            r"we(?:'re| are) going (?:to|with)",
            r"the architecture (?:is|will be|should)",
            r"decided to (?:use|build|implement|go with)",
            r"instead of .+ we(?:'ll| will)",
            r"(?:system|pipeline|layer) design",
            r"(?:chosen|selected|picked) .+ (?:over|instead)",
        ],
        "description": "Architectural decision — how or why something is built a specific way",
    },
    "build_order_item": {
        "triggers": [
            r"we need to build",
            r"add .{0,30}to (?:the )?build order",
            r"new (?:BO|build) item",
            r"should be (?:a |the )?next (?:build|task|item)",
            r"(?:queue|schedule) .+ for (?:later|future|next)",
        ],
        "description": "New build order item — something that needs to be built",
    },
    "vision_philosophy": {
        "triggers": [
            r"COI (?:is|exists|was built) (?:to|for|because)",
            r"the (?:vision|mission|purpose|goal) (?:is|of)",
            r"first principles?",
            r"north star",
            r"why (?:we|COI|this)",
            r"(?:philosophy|foundational|core belief)",
        ],
        "description": "Vision or philosophy concept — why COI exists or how Dave thinks",
    },
    "constitutional_principle": {
        "triggers": [
            r"(?:rule|principle|law|article).*(?:immutable|permanent|never|always)",
            r"COI (?:must|shall|will) (?:never|always)",
            r"this is (?:a |the )?hard (?:rule|stop|line)",
            r"non-negotiable",
        ],
        "description": "Constitutional principle — permanent rule governing COI's behavior",
    },
    "platform_definition": {
        "triggers": [
            r"(?:desktop|mobile|car|fire tv|tablet) (?:app|platform|version|ui)",
            r"platform (?:spec|definition|architecture|design)",
            r"(?:android|ios|web|pyqt|flutter) (?:app|build|deploy)",
            r"multi-(?:screen|platform|device)",
        ],
        "description": "Platform definition — spec for a COI platform (desktop, mobile, car, TV, tablet)",
    },
    "capability_spec": {
        "triggers": [
            r"(?:new|add|implement) (?:capability|feature|tool|function)",
            r"COI (?:can now|will be able to|should be able to|gains)",
            r"(?:tool|capability|feature) (?:spec|definition|architecture)",
            r"(?:voice|vision|memory|filing|routing|scheduling) (?:system|layer|engine)",
        ],
        "description": "Capability spec — new ability or tool being added to COI",
    },
}

# Compile patterns once
for cat in CODEX_CATEGORIES.values():
    cat["_compiled"] = [re.compile(p, re.IGNORECASE) for p in cat["triggers"]]


# ── CLAUDE API ───────────────────────────────────────────────
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
        return None
    return anthropic.Anthropic(api_key=api_key)


def call_claude(prompt, max_tokens=1024):
    """Call Claude API for classification and drafting"""
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
    except:
        return None


# ── LAYER 1: RECOGNITION ────────────────────────────────────
def scan_for_codex_content(user_message, coi_reply):
    """Fast regex pre-scan of conversation for Codex-worthy triggers.
    Returns list of matched categories, or empty list if nothing found.
    Cost: zero — pure regex, no LLM call."""
    combined = user_message + " " + coi_reply
    matches = []
    for category, info in CODEX_CATEGORIES.items():
        for pattern in info["_compiled"]:
            if pattern.search(combined):
                matches.append(category)
                break  # One match per category is enough
    return matches


def classify_codex_content(user_message, coi_reply, categories):
    """LLM confirmation of regex hits. Filters false positives.
    Uses Claude API for classification.
    Returns list of confirmed categories with extracted content."""

    cat_descriptions = "\n".join(
        f"- {cat}: {CODEX_CATEGORIES[cat]['description']}"
        for cat in categories
    )

    prompt = f"""You are a content classifier for the COI Codex (a knowledge base).

Review this conversation exchange and determine if it contains information worth filing permanently.

CANDIDATE CATEGORIES:
{cat_descriptions}

CONVERSATION:
Dave: {user_message[:1500]}
COI: {coi_reply[:1500]}

For each category, respond with EXACTLY this format:
CATEGORY: [category_name]
CONFIRMED: [YES or NO]
CONTENT: [the specific Codex-worthy content, 1-3 sentences — only if CONFIRMED: YES]

If NONE of the categories apply, respond with just: NONE"""

    result = call_claude(prompt)
    if not result:
        return []

    if "NONE" in result.upper() and "CONFIRMED" not in result.upper():
        return []

    # Parse confirmed categories
    confirmed = []
    blocks = re.split(r"CATEGORY:\s*", result)
    for block in blocks:
        if not block.strip():
            continue
        cat_match = re.match(r"(\w+)", block)
        if not cat_match:
            continue
        cat_name = cat_match.group(1).strip()
        if "CONFIRMED: YES" in block.upper() or "CONFIRMED:YES" in block.upper():
            content_match = re.search(r"CONTENT:\s*(.+?)(?=\nCATEGORY:|\Z)", block, re.DOTALL)
            content = content_match.group(1).strip() if content_match else ""
            if content and cat_name in CODEX_CATEGORIES:
                confirmed.append({"category": cat_name, "content": content})

    return confirmed


# ── LAYER 2: DRAFT GENERATION ────────────────────────────────
def _load_codex_map():
    """Load CODEX-MAP.md for filing decisions"""
    try:
        return CODEX_MAP_PATH.read_text(encoding="utf-8")
    except:
        return ""


def generate_codex_draft(confirmed_item, user_message, coi_reply):
    """Generate a properly formatted Codex entry draft using Claude API.
    Returns dict with: path, content, category, reason, commit_message"""
    codex_map = _load_codex_map()
    category = confirmed_item["category"]
    extracted = confirmed_item["content"]

    prompt = f"""You are COI's Codex filing system. You must decide WHERE to file content and FORMAT it correctly.

CODEX MAP (use this to decide the correct file location):
{codex_map[:3000]}

CATEGORY: {category}
EXTRACTED CONTENT: {extracted}

FULL CONVERSATION CONTEXT:
Dave: {user_message[:800]}
COI: {coi_reply[:800]}

INSTRUCTIONS:
1. Decide the exact file path using the CODEX MAP filing decision guide
2. Decide if this should CREATE a new file, APPEND to an existing file, or UPDATE an existing file
3. Format the content in clean markdown — concise, specific, no fluff
4. Write a one-line commit message

Respond in EXACTLY this format:
ACTION: [write/append/update]
FILE: [exact codex-relative path, e.g. COI/L3-Reference/tools.md]
REASON: [one line — why this file]
COMMIT MESSAGE: [short commit message]
CONTENT:
```
[the formatted markdown content to file]
```"""

    result = call_claude(prompt, max_tokens=1536)
    if not result:
        return None

    # Parse the draft
    draft = {
        "category": category,
        "extracted": extracted,
        "action": "append",
        "path": None,
        "reason": None,
        "commit_message": None,
        "content": None,
    }

    action_match = re.search(r"ACTION:\s*(\w+)", result, re.IGNORECASE)
    if action_match:
        draft["action"] = action_match.group(1).strip().lower()

    file_match = re.search(r"FILE:\s*([^\n]+)", result, re.IGNORECASE)
    if file_match:
        draft["path"] = file_match.group(1).strip()

    reason_match = re.search(r"REASON:\s*([^\n]+)", result, re.IGNORECASE)
    if reason_match:
        draft["reason"] = reason_match.group(1).strip()

    commit_match = re.search(r"COMMIT\s*MESSAGE:\s*([^\n]+)", result, re.IGNORECASE)
    if commit_match:
        draft["commit_message"] = commit_match.group(1).strip()

    content_match = re.search(r"```(?:markdown|md|text)?\n(.*?)```", result, re.DOTALL)
    if content_match:
        draft["content"] = content_match.group(1).strip()

    # Validate — must have path and content at minimum
    if not draft["path"] or not draft["content"]:
        return None

    return draft


# ── LAYER 3: APPROVAL QUEUE ─────────────────────────────────
def queue_for_approval(draft):
    """Write draft to pipeline/05-dave-approval/output/ for Dave's review.
    Returns the filepath of the approval record."""
    APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    approval_content = f"""# Codex Filing — Awaiting Approval
{ts}

## Category
{draft['category'].replace('_', ' ').title()}

## Target
**Action:** {draft['action']}
**File:** `{draft['path']}`
**Reason:** {draft['reason']}

## Proposed Content
```markdown
{draft['content']}
```

## Commit Message
{draft['commit_message'] or 'COI Codex Intelligence — auto-filed'}

---
SOURCE: Codex Intelligence — auto-detected from conversation
APPROVED-BY: [pending]
DECISION: [pending]
NOTES: [pending]
"""

    filename = f"{ts}-codex-intel-{draft['category']}.md"
    filepath = APPROVAL_DIR / filename
    filepath.write_text(approval_content, encoding="utf-8")
    return filepath


# ── LAYER 4: AUTONOMOUS FILING ───────────────────────────────
def file_approved_entry(draft):
    """File an approved entry to the Codex using coi-tools.
    Called after Dave approves via mobile UI or desktop.
    Returns (success, message)."""
    try:
        import importlib.util
        tools_path = ICM_ROOT / "scripts/coi-tools.py"
        spec = importlib.util.spec_from_file_location("coi_tools", str(tools_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except:
        return False, "Could not load coi-tools.py"

    commit = draft["commit_message"] or f"COI Codex Intelligence: {draft['category']}"
    action = draft["action"]
    path = draft["path"]
    content = draft["content"]

    if action == "write":
        return mod.coi_write_file(path, content, commit)
    elif action == "append":
        return mod.coi_append_file(path, content, commit)
    elif action == "update":
        return mod.coi_update_file(path, content, commit)
    else:
        return mod.coi_append_file(path, content, commit)


# ── MAIN ENTRY POINT — CALLED BY DESKTOP ─────────────────────
def process_conversation(user_message, coi_reply):
    """Full pipeline: scan -> classify -> draft -> queue.
    Called after every conversation exchange.
    Returns list of draft dicts if something was queued, None otherwise.
    Cost: zero if no triggers (regex only), one Claude API call if triggered."""

    # Layer 1a: Fast regex scan — zero cost
    categories = scan_for_codex_content(user_message, coi_reply)
    if not categories:
        return None

    # Layer 1b: Claude confirmation — filters false positives
    confirmed = classify_codex_content(user_message, coi_reply, categories)
    if not confirmed:
        return None

    # Process ALL confirmed items
    drafts = []
    for item in confirmed:
        draft = generate_codex_draft(item, user_message, coi_reply)
        if draft:
            filepath = queue_for_approval(draft)
            draft["approval_file"] = str(filepath)
            drafts.append(draft)

    return drafts if drafts else None


# ── SELF TEST ────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("  COI Codex Intelligence — Self Test (V5)")
    print()

    # Test recognition (regex only — no API call)
    test_cases = [
        ("We decided to use FastAPI instead of Flask for the mobile approval server",
         "Good call. FastAPI gives us async support and auto-generated docs."),
        ("What's the weather like?",
         "I don't have access to weather data."),
        ("COI exists to be a ground-up operating system, not a chatbot",
         "That's the north star. Everything we build serves that vision."),
        ("Add voice recognition to the build order",
         "I'll queue that as a new BO item for after the mobile UI is complete."),
    ]

    for user_msg, coi_msg in test_cases:
        cats = scan_for_codex_content(user_msg, coi_msg)
        status = f"TRIGGERED: {cats}" if cats else "no trigger"
        print(f"  [{status}] Dave: {user_msg[:60]}...")

    print()
    print("  Codex map: " + ("loaded" if _load_codex_map() else "NOT FOUND"))
    print("  Approval dir: " + str(APPROVAL_DIR))
    print("  API key: " + ("configured" if _load_api_key() else "NOT FOUND"))
    print()
