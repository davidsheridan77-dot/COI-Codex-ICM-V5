#!/usr/bin/env python3
# ============================================================
# COI Orchestrator v3 — coi-orchestrator.py
# Connects Claude (Anthropic API) and local LLMs (Ollama)
# into a single autonomous pipeline loop.
#
# Claude     — oversees, directs, reviews, reports
# Local LLMs — generate, review, test, execute
# Dave       — approves at Stage 05. Nothing passes without him.
#
# Usage: python coi-orchestrator.py
# ============================================================

import json
import re
import time
import requests
import base64
from datetime import datetime
from pathlib import Path

# ── CONFIG ───────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434/api/generate"  # DEPRECATED-V5
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ICM_ROOT      = Path("K:/Coi Codex/COI-Codex-ICM")
PIPELINE_ROOT = ICM_ROOT / "pipeline"
CONFIG_PATH   = ICM_ROOT / "config" / "config.json"

# ── MODEL ASSIGNMENTS ────────────────────────────────────
# Loaded from scripts/model-config.json — single source of truth
MODEL_CONFIG_PATH = ICM_ROOT / "scripts" / "model-config.json"  # DEPRECATED-V5

def load_model_config():  # DEPRECATED-V5 — loads Ollama model assignments from model-config.json
    try:
        with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
            cfg = json.load(f)
        return {k: v["model"] for k, v in cfg.get("roles", {}).items()}  # DEPRECATED-V5
    except Exception as e:
        print(f"WARN: Could not load model-config.json ({e}), using defaults")  # DEPRECATED-V5
        return {
            "classifier": "llama3.2:1b",  # DEPRECATED-V5
            "general": "mistral:7b-instruct-q4_K_M",  # DEPRECATED-V5
            "conversation": "claude-sonnet-4-6",
        }

MODELS = load_model_config()  # DEPRECATED-V5

# ── COST TIER ROUTING — BO-013 ──────────────────────────
# Local LLM (zero cost): classification, review, memory, session, briefing
# Claude API (metered): complex reasoning, architecture, Dave-facing summaries only
COST_TIER_LOCAL = {  # DEPRECATED-V5 — local LLM routing tier
    "classify", "review", "generate", "execute",
    "briefing", "memory", "session", "file_ops",
}
COST_TIER_API = {
    "complex_reasoning", "architecture", "dave_summary",
}

def route_by_cost_tier(task_type, prompt, config=None, timeout=300):  # DEPRECATED-V5 — routes tasks between Ollama and Claude
    """Route task to cheapest capable model — BO-013 cost management.
    Local LLM first. Claude API only for Dave-facing summaries and
    complex reasoning that local models cannot handle."""
    if task_type in COST_TIER_LOCAL:  # DEPRECATED-V5
        # Always use local LLM — zero cost
        model = MODELS.get(task_type, MODELS.get("general", "mistral:7b-instruct-q4_K_M"))  # DEPRECATED-V5
        result = call_ollama(model, prompt, timeout=timeout)  # DEPRECATED-V5
        if result:
            return result
        # Local failed — try fallback local model before escalating
        fallback = MODELS.get("general", "mistral:7b-instruct-q4_K_M")  # DEPRECATED-V5
        result = call_ollama(fallback, prompt, timeout=timeout)  # DEPRECATED-V5
        if result:
            return result
        log(f"All local models failed for {task_type} — escalating to API", "WARN")  # DEPRECATED-V5

    # API tier — metered, use only when necessary
    return call_claude(prompt, config=config)

# One file per pipeline run — avoids context overload
AUDIT_TARGETS = [
    "ui/COI-Desktop.html",
    "scripts/coi-orchestrator.py",
    "scripts/launch.ps1",
    "scripts/session-save.ps1",
]

STAGES = {
    1: "01-intake",
    2: "02-generate",
    3: "03-review",
    4: "04-sandbox",
    5: "05-dave-approval",
    6: "06-deploy",
}

# ── HELPERS ──────────────────────────────────────────────
def load_config():
    if not CONFIG_PATH.exists():
        print(f"ERROR: config.json not found at {CONFIG_PATH}")
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {
        "INFO"   : "\033[36mINFO\033[0m",
        "OK"     : "\033[32m OK \033[0m",
        "WARN"   : "\033[33mWARN\033[0m",
        "ERROR"  : "\033[31mERR \033[0m",
        "CLAUDE" : "\033[35mCLAUDE\033[0m",
        "LOCAL"  : "\033[34mLOCAL\033[0m",
        "DAVE"   : "\033[33mDAVE\033[0m",
    }.get(level, "INFO")
    print(f"[{timestamp}] [{prefix}] {message}")

def write_output(stage_num, filename, content):
    output_dir = PIPELINE_ROOT / STAGES[stage_num] / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / filename
    filepath.write_text(content, encoding="utf-8")
    log(f"Output written: {filepath}", "OK")
    return filepath

def read_stage_context(stage_num):
    f = PIPELINE_ROOT / STAGES[stage_num] / "CONTEXT.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""

# ── OLLAMA ───────────────────────────────────────────────
def call_ollama(model, prompt, timeout=300):  # DEPRECATED-V5 — Ollama local LLM call
    log(f"Calling {model}...", "LOCAL")  # DEPRECATED-V5
    try:
        r = requests.post(OLLAMA_URL,  # DEPRECATED-V5
            json={"model": model, "prompt": prompt, "stream": False,  # DEPRECATED-V5
                  "options": {"num_ctx": 4096}},
            timeout=timeout)
        r.raise_for_status()
        result = r.json().get("response", "").strip()
        log(f"{model} responded ({len(result)} chars)", "OK")  # DEPRECATED-V5
        return result
    except requests.exceptions.Timeout:
        log(f"{model} timed out after {timeout}s", "ERROR")  # DEPRECATED-V5
        return None
    except Exception as e:
        log(f"{model} failed: {e}", "ERROR")  # DEPRECATED-V5
        return None

# ── PROVIDER-ABSTRACTED CACHING ─────────────────────────
# Import adapter from coi-tools — provider from model-config.json
try:
    import importlib.util as _ilu
    _tools_spec = _ilu.spec_from_file_location("coi_tools", str(ICM_ROOT / "scripts/coi-tools.py"))
    _tools_mod = _ilu.module_from_spec(_tools_spec)
    _tools_spec.loader.exec_module(_tools_mod)
    build_system_payload = _tools_mod.build_system_payload
    coi_batch_github_write = _tools_mod.coi_batch_github_write
except:
    def build_system_payload(content, provider=None):
        return content  # Fallback — plain string, no caching
    def coi_batch_github_write(file_ops, commit_message=None):
        return False, "coi-tools import failed"

# ── CLAUDE ───────────────────────────────────────────────
def call_claude(prompt, config=None):
    log("Calling Claude...", "CLAUDE")
    if not config:
        config = load_config()
    api_key = config.get("anthropic_api_key", "")
    if not api_key:
        log("No Anthropic API key in config.json", "ERROR")
        return None

    claude_md   = ICM_ROOT / "CLAUDE.md"
    base_system = claude_md.read_text(encoding="utf-8") if claude_md.exists() else "You are COI."

    # Provider-abstracted caching — adapter handles mechanism
    system_payload = build_system_payload(base_system, "anthropic")

    try:
        r = requests.post(ANTHROPIC_URL,
            headers={
                "Content-Type"      : "application/json",
                "x-api-key"         : api_key,
                "anthropic-version" : "2023-06-01",
            },
            json={
                "model"      : "claude-sonnet-4-6",
                "max_tokens" : 2048,
                "system"     : system_payload,
                "messages"   : [{"role": "user", "content": prompt}],
            },
            timeout=60)
        r.raise_for_status()
        result = r.json()["content"][0]["text"].strip()
        log(f"Claude responded ({len(result)} chars)", "OK")
        return result
    except Exception as e:
        log(f"Claude failed: {e}", "ERROR")
        return None

# ── READ FILE FOR AUDIT ──────────────────────────────────
def read_target_file(filename):
    candidates = [
        ICM_ROOT / filename,
        ICM_ROOT / "ui" / Path(filename).name,
        ICM_ROOT / "scripts" / Path(filename).name,
    ]
    for path in candidates:
        if path.exists():
            content = path.read_text(encoding="utf-8", errors="ignore")
            # Keep context tight — first 3000 chars only
            if len(content) > 3000:
                content = content[:3000] + "\n\n[... truncated — first 3000 chars shown ...]"
            return content, str(path)
    return None, None

# ── BATCH OPERATIONS — BO-013 ────────────────────────────
# Group multiple prompts into one LLM call instead of N separate calls.
# Saves API round-trips and prompt overhead on metered tiers.

def batch_llm_call(task_type, items, prompt_builder, config=None, timeout=300):
    """Batch multiple items into a single LLM call.

    Args:
        task_type: cost tier key (e.g. 'dave_summary', 'classify')
        items: list of dicts, each representing one item to process
        prompt_builder: function(items) -> single combined prompt string
        config: config dict
        timeout: request timeout

    Returns:
        str: combined LLM response covering all items
    """
    if not items:
        return ""
    if len(items) == 1:
        # Single item — no batching overhead needed
        return route_by_cost_tier(task_type, prompt_builder(items), config=config, timeout=timeout)  # DEPRECATED-V5 — routes through Ollama tier
    # Batch: one call for all items
    combined_prompt = prompt_builder(items)
    return route_by_cost_tier(task_type, combined_prompt, config=config, timeout=timeout)  # DEPRECATED-V5 — routes through Ollama tier


def batch_deploy_github(deploy_items, config):
    """BO-013: Batch multiple deploy files into a single GitHub commit.

    Args:
        deploy_items: list of dicts with 'filename', 'content', 'path'
    """
    if not deploy_items:
        return

    # Build file_ops for batch writer
    file_ops = []
    for item in deploy_items:
        file_ops.append({
            "path": item["path"],
            "content": item["content"]
        })

    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    commit_msg = f"COI Deploy batch {ts} — {len(deploy_items)} files"
    ok, msg = coi_batch_github_write(file_ops, commit_msg)
    if ok:
        log(f"Batch GitHub deploy: {len(deploy_items)} files", "OK")
    else:
        log(f"Batch GitHub deploy failed: {msg}", "WARN")


# ── AUDIT MODE ───────────────────────────────────────────
def run_audit(config):
    log("", "INFO")
    log("COI Audit Mode — one file at a time", "INFO")
    log(f"{len(AUDIT_TARGETS)} files queued", "INFO")
    log("", "INFO")

    all_findings = []
    pending_summaries = []  # BO-013: collect findings for batch summary

    # Phase 1 — Local LLM audit + review (zero cost per file)
    for i, target in enumerate(AUDIT_TARGETS):
        log(f"File {i+1}/{len(AUDIT_TARGETS)}: {target}", "INFO")

        content, filepath = read_target_file(target)
        if not content:
            log(f"Not found: {target} — skipping", "WARN")
            continue

        log(f"Loaded: {filepath} ({len(content)} chars)", "OK")

        # Stage 02 — audit this single file (local LLM — zero cost)
        log("=== Stage 02 — Audit ===", "INFO")
        audit_prompt = f"""Audit this file for the COI system. Be specific and concise.

FILE: {target}

For each issue use this exact format:
PRIORITY: [Critical/High/Medium/Low/Minor]
ISSUE: [what the problem is]
FIX: [what to do]
EFFORT: [Quick/Medium/Large]

Order findings from most critical to least critical.
End with one line: SUMMARY: [overall quality assessment]

FILE CONTENT:
{content}"""

        findings = call_ollama(MODELS["generator"], audit_prompt, timeout=300)  # DEPRECATED-V5
        if not findings:
            log(f"No response for {target} — skipping", "ERROR")
            continue

        ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        write_output(2, f"{ts}-audit-{target.replace('/', '-').replace('.', '-')}.md",
            f"# Audit — {target}\n\n{findings}")

        # Stage 03 — reviewer confirms findings (local LLM — zero cost)
        log("=== Stage 03 — Review ===", "INFO")
        review = call_ollama(MODELS["reviewer"],  # DEPRECATED-V5
            f"Confirm or correct these audit findings for: {target}\n\n{findings[:2000]}\n\nReturn: VERDICT: [CONFIRMED/ADJUSTED] then corrected list.",
            timeout=180)
        if not review:
            review = "Reviewer unavailable — using generator findings."

        # BO-013: Queue for batch summary instead of per-file API call
        pending_summaries.append({
            "target": target,
            "findings": findings,
            "review": review,
        })

    # Phase 2 — Batch Dave summaries (ONE API call instead of N)
    if pending_summaries:
        log(f"BO-013: Batching {len(pending_summaries)} audit summaries into one API call", "INFO")

        def _build_batch_summary_prompt(items):
            prompt = "Summarise these audit findings for Dave. For EACH file, write a header with the filename then 3-5 lines of plain English. Most important fixes first. Separate each file with ---\n\n"
            for item in items:
                prompt += f"FILE: {item['target']}\n{item['findings'][:800]}\n\n"
            return prompt

        batch_summary = batch_llm_call(
            "dave_summary", pending_summaries, _build_batch_summary_prompt,
            config=config, timeout=120
        ) or ""

        # Split batch response back into per-file summaries
        summary_sections = {}
        current_file = None
        current_lines = []
        for line in batch_summary.split("\n"):
            # Detect file headers in response
            matched = False
            for item in pending_summaries:
                if item["target"].lower() in line.lower() or Path(item["target"]).name.lower() in line.lower():
                    if current_file:
                        summary_sections[current_file] = "\n".join(current_lines).strip()
                    current_file = item["target"]
                    current_lines = []
                    matched = True
                    break
            if not matched and line.strip() == "---":
                if current_file:
                    summary_sections[current_file] = "\n".join(current_lines).strip()
                    current_file = None
                    current_lines = []
            elif current_file:
                current_lines.append(line)
        if current_file:
            summary_sections[current_file] = "\n".join(current_lines).strip()

    # Phase 3 — Dave approval (interactive, per-file)
    for item in pending_summaries:
        target = item["target"]
        findings = item["findings"]
        review = item["review"]
        summary = summary_sections.get(target, findings[:400]) if pending_summaries else findings[:400]

        # Stage 05 — Dave approval
        ts2 = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        approval_content = f"""# Audit — {target}
{ts2}

## Summary for Dave
{summary}

## Full Findings
{findings}

## Reviewer Confirmation
{review}

---
APPROVED-BY: [pending]
DECISION: [pending]
NOTES: [pending]
"""
        approval_file = write_output(5,
            f"{ts2}-audit-{target.replace('/', '-').replace('.', '-')}.md",
            approval_content)

        log("════════════════════════════════════════", "DAVE")
        log(f"AUDIT: {target}", "DAVE")
        log("", "DAVE")
        for line in summary.split("\n")[:6]:
            if line.strip():
                log(line.strip(), "DAVE")
        log("════════════════════════════════════════", "DAVE")
        print()
        print("  [A] Approve   [R] Reject   [H] Hold   [S] Skip rest")
        print()

        while True:
            decision = input("  > ").strip().upper()
            if decision in ["A", "R", "H", "S"]:
                break

        if decision == "S":
            log("Skipping remaining files", "INFO")
            break

        notes = ""
        if decision in ["R", "H"]:
            notes = input("  Notes: ").strip()

        decision_text = {"A": "APPROVED", "R": "REJECTED", "H": "HOLD"}.get(decision, "HOLD")
        approval_file.write_text(
            approval_content
                .replace("APPROVED-BY: [pending]", "APPROVED-BY: Dave")
                .replace("DECISION: [pending]", f"DECISION: {decision_text}")
                .replace("NOTES: [pending]", f"NOTES: {notes or 'None'}"),
            encoding="utf-8")

        log(f"Recorded: {decision_text}", "DAVE")
        all_findings.append({"file": target, "findings": findings, "decision": decision_text})
        time.sleep(1)

    # Consolidated report
    if all_findings:
        log("Writing consolidated audit report...", "INFO")
        lines = [f"# COI Audit Report\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n"]
        for item in all_findings:
            lines.append(f"\n## {item['file']} — {item['decision']}\n{item['findings']}\n\n---\n")
        report = ICM_ROOT / "COI/03-memory-systems/audit-report.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("\n".join(lines), encoding="utf-8")
        log(f"Report: {report}", "OK")

    generate_briefing(f"Audit complete. Files: {[f['file'] for f in all_findings]}", config)
    log("Audit complete.", "OK")

# ── STANDARD PIPELINE ────────────────────────────────────
def stage_intake(task, config):
    log("=== Stage 01 — Intake ===", "INFO")
    # BO-013: Classification is local-tier — zero cost
    result = route_by_cost_tier("classify",  # DEPRECATED-V5 — routes through Ollama tier
        f"{read_stage_context(1)}\n\nTASK: {task}\n\nClassify and write a task brief.",
        config=config)
    if not result:
        log("Stage 01 failed", "ERROR")
        return None
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    write_output(1, f"{ts}-task-brief.md", f"# Task Brief\n\n{result}\n\nORIGINAL:\n{task}")
    return result

def stage_generate(brief, config):
    log("=== Stage 02 — Generate ===", "INFO")
    result = call_ollama(MODELS["generator"],  # DEPRECATED-V5
        f"{read_stage_context(2)}\n\nTASK:\n{brief}\n\nWrite the output. Start with FILE: [name]", timeout=300)
    if not result:
        log("Stage 02 failed", "ERROR")
        return None
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    write_output(2, f"{ts}-generated.md", f"# Generated\n\n{result}")
    return result

def stage_review(generated, brief, config):
    log("=== Stage 03 — Review ===", "INFO")
    context = read_stage_context(3)
    result = call_ollama(MODELS["reviewer"],  # DEPRECATED-V5
        f"{context}\n\nReview this output against the original task.\n\nTASK:\n{brief[:400]}\n\nOUTPUT:\n{generated[:3000]}\n\nCheck for: security gaps, broken references, missing requirements, incorrect logic.\nEnd with exactly: VERDICT: PASS or VERDICT: FAIL",
        timeout=180)
    if not result:
        log("Stage 03 — reviewer returned nothing", "ERROR")
        return None, False
    upper = result.upper()
    passed = "VERDICT: PASS" in upper or "VERDICT:PASS" in upper or ("PASS" in upper and "FAIL" not in upper)
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    write_output(3, f"{ts}-review.md", f"# Review\n\nTask: {brief[:200]}\n\n{result}")
    log(f"Review: {'PASSED' if passed else 'FAILED'}", "OK" if passed else "WARN")
    return result, passed

def stage_sandbox(generated, review, config):
    log("=== Stage 04 — Sandbox ===", "INFO")
    context = read_stage_context(4)
    result = call_ollama(MODELS["executor"],  # DEPRECATED-V5
        f"{context}\n\nTest this code for errors, edge cases, and runtime issues.\n\nCODE:\n{generated[:3000]}\n\nREVIEW NOTES:\n{(review or 'None')[:500]}\n\nCheck for: syntax errors, missing imports, undefined variables, logic bugs.\nEnd with exactly: TEST RESULT: PASS or TEST RESULT: FAIL",
        timeout=180)
    if not result:
        log("Stage 04 — executor returned nothing", "ERROR")
        return None, False
    upper = result.upper()
    passed = "TEST RESULT: PASS" in upper or "TEST RESULT:PASS" in upper or ("PASS" in upper and "FAIL" not in upper)
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    write_output(4, f"{ts}-sandbox.md", f"# Sandbox\n\nReview: {(review or 'N/A')[:200]}\n\n{result}")
    log(f"Sandbox: {'PASSED' if passed else 'FAILED'}", "OK" if passed else "WARN")
    return result, passed

def stage_dave_approval(brief, generated, review, sandbox, config, headless=False):
    """Stage 05 — Dave's approval gate.
    Interactive mode (default): blocks on terminal input, Dave decides now.
    Headless mode: writes approval file and returns PENDING — Dave decides
    later via mobile approval UI (BO-007)."""
    log("=== Stage 05 — Dave ===", "DAVE")
    # BO-013: Dave-facing summary is API tier — this is where Claude earns its cost
    summary = route_by_cost_tier("dave_summary",  # DEPRECATED-V5 — routes through Ollama tier first
        f"5 lines max. What was built, why, risk level.\nTASK: {brief[:400]}\nREVIEW: {(review or '')[:200]}",
        config=config) or "Summary unavailable."

    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    content = f"# Awaiting Approval — {ts}\n\n{summary}\n\n---\n{generated}\n\n---\nAPPROVED-BY: [pending]\nDECISION: [pending]\nNOTES: [pending]"
    filepath = write_output(5, f"{ts}-approval.md", content)

    log("════════════════════════", "DAVE")
    log(summary[:300], "DAVE")
    log("════════════════════════", "DAVE")

    # Headless mode — write file and move on, Dave approves via mobile UI
    if headless:
        log("Headless mode — approval queued for mobile UI", "DAVE")
        log(f"Pending: {filepath.name}", "INFO")
        return "PENDING", ""

    # Interactive mode — Dave is at the terminal
    print("\n  [A] Approve   [R] Reject   [H] Hold\n")

    while True:
        d = input("  > ").strip().upper()
        if d in ["A", "R", "H"]:
            break

    notes = input("  Notes: ").strip() if d in ["R", "H"] else ""
    decision = {"A": "APPROVED", "R": "REJECTED", "H": "HOLD"}[d]
    filepath.write_text(content
        .replace("APPROVED-BY: [pending]", "APPROVED-BY: Dave")
        .replace("DECISION: [pending]", f"DECISION: {decision}")
        .replace("NOTES: [pending]", f"NOTES: {notes or 'None'}"),
        encoding="utf-8")
    log(f"Decision: {decision}", "DAVE")
    return decision, notes

def stage_deploy(generated, brief, config, deploy_batch=None):
    """Deploy stage. If deploy_batch list is provided, queues for batch GitHub push
    instead of pushing individually. Caller flushes the batch."""
    log("=== Stage 06 — Deploy ===", "INFO")
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    m  = re.search(r"FILE:\s*(.+)", generated)
    fn = m.group(1).strip() if m else f"output-{ts}.md"
    q  = PIPELINE_ROOT / "06-deploy" / "output" / "queue"
    q.mkdir(parents=True, exist_ok=True)
    (q / f"{ts}-{fn}").write_text(generated, encoding="utf-8")
    write_output(6, f"{ts}-deploy-log.md", f"# Deploy\nFILE: {fn}\nSTATUS: Queued\n{ts}")

    if deploy_batch is not None:
        # BO-013: Queue for batch GitHub push — one commit for all deploys
        deploy_batch.append({
            "path": f"pipeline/06-deploy/output/queue/{ts}-{fn}",
            "content": generated,
            "filename": fn,
        })
        log(f"Queued for batch deploy: {fn}", "OK")
    else:
        # Single deploy — push individually
        push_to_github(config, generated, fn, ts)
        log(f"Queued: {fn}", "OK")

def push_to_github(config, content, filename, timestamp):
    """BO-013: GitHub push in background thread — never blocks pipeline"""
    token = config.get("github_token", "")
    if not token:
        log("No token — skipping GitHub push", "WARN")
        return

    def _push():
        try:
            r = requests.put(
                f"https://api.github.com/repos/{config.get('github_owner','davidsheridan77-dot')}/COI-Codex-ICM/contents/pipeline/06-deploy/output/queue/{timestamp}-{filename}",
                json={"message": f"Deploy {timestamp}", "content": base64.b64encode(content.encode()).decode()},
                headers={"Authorization": f"token {token}", "User-Agent": "COI"},
                timeout=30)
            if r.status_code in [200, 201]:
                log(f"GitHub: {r.status_code}", "OK")
            else:
                log(f"GitHub: {r.status_code} — logged to error-memory", "WARN")
                _log_github_failure(filename, r.status_code)
        except Exception as e:
            log(f"GitHub error: {e} — logged to error-memory", "WARN")
            _log_github_failure(filename, str(e))

    def _log_github_failure(fname, error):
        try:
            err_path = ICM_ROOT / "COI/L4-Working/memory/error-memory.md"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"\n## {ts} — GitHub Push Failure (Orchestrator)\n"
            entry += f"- **File:** {fname}\n- **Error:** {error}\n"
            entry += f"- **Local write:** Succeeded\n- **Action needed:** Retry sync\n"
            if err_path.exists():
                with open(err_path, "a", encoding="utf-8") as f:
                    f.write(entry)
        except:
            pass

    import threading
    threading.Thread(target=_push, daemon=True).start()
    log(f"GitHub push queued in background: {filename}", "INFO")

def generate_briefing(session_log, config):
    # BO-013: Briefing is local tier — zero cost, always
    result = route_by_cost_tier("briefing",  # DEPRECATED-V5 — routes through Ollama tier
        f"Write a short session briefing for Dave. Plain English. Under 10 lines.\n\n{session_log}",
        config=config, timeout=120) or "Briefing unavailable."
    p = ICM_ROOT / "COI/L4-Working/memory/next-session-briefing.md"
    p.write_text(f"# Briefing — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{result}", encoding="utf-8")
    log(f"Briefing saved", "OK")

def run_pipeline(task, deploy_batch=None, headless=False):
    """Run single task through pipeline.
    deploy_batch: list to collect deploys for batch GitHub push.
    headless: if True, approval stage writes file and returns PENDING
              instead of blocking on terminal input."""
    config = load_config()
    log("COI Pipeline — Starting", "INFO")
    log(f"Task: {task[:80]}", "INFO")

    brief = stage_intake(task, config)
    if not brief:
        return

    for attempt in range(3):
        generated = stage_generate(brief, config)
        if not generated:
            return

        review, passed = stage_review(generated, brief, config)
        if not passed:
            brief = f"{brief}\n\nREVIEW FEEDBACK:\n{review}"
            time.sleep(2)
            continue

        sandbox, passed = stage_sandbox(generated, review, config)
        if not passed:
            brief = f"{brief}\n\nSANDBOX FAILURE:\n{sandbox}"
            time.sleep(2)
            continue

        break
    else:
        log("Max retries reached", "ERROR")
        generate_briefing("Pipeline halted — max retries", config)
        return

    decision, notes = stage_dave_approval(brief, generated, review, sandbox, config, headless=headless)
    if decision == "APPROVED":
        stage_deploy(generated, brief, config, deploy_batch=deploy_batch)

    generate_briefing(f"Task complete. Decision: {decision}", config)

# ── TASK QUEUE ────────────────────────────────────────────
TASK_QUEUE_PATH = ICM_ROOT / "COI/L4-Working/task-queue.md"

def read_task_queue():
    """Read task queue and return list of pending tasks"""
    if not TASK_QUEUE_PATH.exists():
        return []
    content = TASK_QUEUE_PATH.read_text(encoding="utf-8")
    tasks = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("| ID") or line.startswith("|--"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) >= 4 and parts[2].upper() == "PENDING":
            tasks.append({"id": parts[0], "task": parts[1], "status": parts[2], "priority": parts[3]})
    return tasks

def update_task_status(task_id, new_status):
    """Update a task's status in the queue file"""
    if not TASK_QUEUE_PATH.exists():
        return
    content = TASK_QUEUE_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()
    updated = []
    for line in lines:
        if f"| {task_id} |" in line:
            line = line.replace("| PENDING |", f"| {new_status} |")
            line = line.replace("| IN-PROGRESS |", f"| {new_status} |")
        updated.append(line)
    TASK_QUEUE_PATH.write_text("\n".join(updated), encoding="utf-8")

def run_queue(config):
    """Process all pending tasks from the queue automatically.
    Always runs headless — approvals written to Stage 05 for mobile UI.
    BO-013: Batches all approved deploys into a single GitHub commit."""
    log("", "INFO")
    log("COI Queue Mode — processing pending tasks (headless)", "INFO")
    log("Approvals queued for mobile UI — COI does not block on input", "INFO")
    log("BO-013: Batch deploy enabled — GitHub writes collected and flushed at end", "INFO")
    log("", "INFO")

    deploy_batch = []  # BO-013: collect deploys for single GitHub commit

    while True:
        tasks = read_task_queue()
        if not tasks:
            log("No pending tasks in queue.", "INFO")
            break

        task = tasks[0]
        log(f"Queue: {task['id']} — {task['task']}", "INFO")
        update_task_status(task["id"], "IN-PROGRESS")

        try:
            run_pipeline(task["task"], deploy_batch=deploy_batch, headless=True)
            update_task_status(task["id"], "DONE")
            log(f"Completed: {task['id']}", "OK")
        except Exception as e:
            update_task_status(task["id"], f"FAILED — {str(e)[:50]}")
            log(f"Failed: {task['id']} — {e}", "ERROR")

        time.sleep(2)

    # BO-013: Flush batch — one GitHub commit for all approved deploys
    if deploy_batch:
        log(f"BO-013: Flushing batch deploy — {len(deploy_batch)} files in one commit", "INFO")
        batch_deploy_github(deploy_batch, config)
    else:
        log("No deploys to push.", "INFO")

    # Sweep for any previously approved items waiting for deploy
    run_approval_sweep(config)

    log("Queue empty. Orchestrator idle.", "INFO")

# ── APPROVAL WATCHER ─────────────────────────────────────────
# Scans pipeline/05-dave-approval/output/ for files Dave has approved.
# Deploys approved items. Moves processed files to archive.
# Closes the headless loop — queue writes PENDING, Dave approves, watcher deploys.

APPROVAL_OUTPUT = PIPELINE_ROOT / "05-dave-approval" / "output"
APPROVAL_ARCHIVE = APPROVAL_OUTPUT / "archive-processed"

def scan_approved():
    """Scan approval dir for files with DECISION: APPROVED.
    Returns list of dicts: {filepath, content, generated_content}."""
    if not APPROVAL_OUTPUT.exists():
        return []
    approved = []
    for f in APPROVAL_OUTPUT.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")
            if "DECISION: APPROVED" in text:
                # Extract the generated content between the --- markers
                parts = text.split("---")
                generated = parts[1].strip() if len(parts) >= 3 else text
                approved.append({
                    "filepath": f,
                    "content": text,
                    "generated": generated,
                    "filename": f.name,
                })
        except:
            continue
    return approved


def deploy_approved(items, config):
    """Deploy approved items and archive the approval files."""
    if not items:
        return 0

    APPROVAL_ARCHIVE.mkdir(parents=True, exist_ok=True)
    deploy_batch = []
    deployed = 0

    for item in items:
        log(f"Deploying approved: {item['filename']}", "OK")

        # Check if this is a Codex Intelligence filing (has SOURCE: Codex Intelligence)
        if "SOURCE: Codex Intelligence" in item["content"]:
            # Extract filing details and use coi-tools
            _deploy_codex_intel(item, config)
        else:
            # Standard pipeline output — deploy via stage 06
            stage_deploy(item["generated"], item["filename"], config, deploy_batch=deploy_batch)

        # Archive the approval file
        dest = APPROVAL_ARCHIVE / item["filename"]
        item["filepath"].rename(dest)
        deployed += 1
        log(f"Archived: {item['filename']}", "OK")

    # Flush batch GitHub push
    if deploy_batch:
        batch_deploy_github(deploy_batch, config)

    return deployed


def _deploy_codex_intel(item, config):
    """Deploy a Codex Intelligence filing — write to correct Codex location."""
    import importlib.util as _ilu
    try:
        _ts = _ilu.spec_from_file_location("coi_tools", str(ICM_ROOT / "scripts/coi-tools.py"))
        _tm = _ilu.module_from_spec(_ts)
        _ts.loader.exec_module(_tm)
    except:
        log("Could not load coi-tools for Codex filing", "ERROR")
        return

    text = item["content"]

    # Parse target path and action from the approval file
    action = "append"
    path = None
    content = None

    action_match = re.search(r"\*\*Action:\*\*\s*(\w+)", text)
    if action_match:
        action = action_match.group(1).strip().lower()

    path_match = re.search(r"\*\*File:\*\*\s*`([^`]+)`", text)
    if path_match:
        path = path_match.group(1).strip()

    content_match = re.search(r"```markdown\n(.*?)```", text, re.DOTALL)
    if not content_match:
        content_match = re.search(r"```\n(.*?)```", text, re.DOTALL)
    if content_match:
        content = content_match.group(1).strip()

    if not path or not content:
        log(f"Could not parse Codex filing from {item['filename']}", "WARN")
        return

    commit = f"COI Codex Intelligence: filed to {path}"

    if action == "write":
        ok, msg = _tm.coi_write_file(path, content, commit)
    elif action == "append":
        ok, msg = _tm.coi_append_file(path, content, commit)
    elif action == "update":
        ok, msg = _tm.coi_update_file(path, content, commit)
    else:
        ok, msg = _tm.coi_append_file(path, content, commit)

    if ok:
        log(f"Codex filed: {path} ({action})", "OK")
    else:
        log(f"Codex filing failed: {msg}", "ERROR")


def run_approval_sweep(config):
    """One-shot: scan for approved items and deploy them."""
    log("Approval sweep — checking for approved items...", "INFO")
    items = scan_approved()
    if not items:
        log("No approved items found.", "INFO")
        return 0
    log(f"Found {len(items)} approved item(s)", "OK")
    return deploy_approved(items, config)


def run_watch(config, interval=30):
    """Continuous approval watcher — polls for approved items.
    Runs until interrupted. Pairs with headless queue mode."""
    log("", "INFO")
    log("COI Approval Watcher — monitoring for Dave's decisions", "INFO")
    log(f"Polling every {interval}s — Ctrl+C to stop", "INFO")
    log(f"Watching: {APPROVAL_OUTPUT}", "INFO")
    log("", "INFO")

    try:
        while True:
            deployed = run_approval_sweep(config)
            if deployed:
                log(f"Deployed {deployed} item(s) this sweep", "OK")
            time.sleep(interval)
    except KeyboardInterrupt:
        log("Watcher stopped.", "INFO")


# ── ENTRY POINT ───────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("  ╔═══════════════════════════════════════╗")
    print("  ║       COI Orchestrator v3             ║")
    print("  ║  Claude + Local LLMs + Dave           ║")
    print("  ╚═══════════════════════════════════════╝")
    print()
    print("  'audit'  — audit all COI files one by one")
    print("  'queue'  — process task queue automatically (headless)")
    print("  'watch'  — poll for approved items and deploy them")
    print("  'sweep'  — one-shot: deploy any approved items now")
    print("  'quit'   — exit")
    print("  anything else — single pipeline task")
    print()

    config = load_config()

    while True:
        task = input("  Task > ").strip()
        if task.lower() == "quit":
            print("\n  Stopped.\n")
            break
        if not task:
            continue
        if task.lower() == "audit":
            run_audit(config)
        elif task.lower() == "queue":
            run_queue(config)
        elif task.lower() == "watch":
            run_watch(config)
        elif task.lower() == "sweep":
            run_approval_sweep(config)
        else:
            run_pipeline(task)
        print("\n  Ready.\n")


