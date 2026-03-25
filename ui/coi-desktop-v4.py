#!/usr/bin/env python3
# ============================================================
# COI Desktop v4 — Native Windows App
# PyQt6 — Basic. Functional. No fluff.
#
# Usage: python coi-desktop-v4.py
# Requires: pip install PyQt6 requests
# ============================================================

import sys
import re
import json
import hashlib
import requests
import threading
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy,
    QDialog, QDialogButtonBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QMimeData
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCursor, QDragEnterEvent, QDropEvent

# ── TOOLS PANEL + TOKEN TRACKER ───────────────────────────────
from coi_tools_panel import COIToolsPanel
from coi_token_tracker import TokenTracker

# ── DROP-OFF PANEL ────────────────────────────────────────────
from coi_dropoff_panel import DropOffPanel, get_dropoff_index
from coi_dropoff_worker import DropOffWorker

# ── RETURN BRIEFING PANEL ────────────────────────────────────
from coi_briefing_panel import ReturnBriefingPanel

# ── CONFIG ───────────────────────────────────────────────────
ICM_ROOT    = Path("K:/Coi Codex/COI-Codex-ICM")
CONFIG_PATH = ICM_ROOT / "config" / "config.json"
OLLAMA_URL  = "http://localhost:11434/api/chat"  # DEPRECATED-V5
CLAUDE_URL  = "https://api.anthropic.com/v1/messages"

MODEL_CONFIG_PATH = ICM_ROOT / "scripts" / "model-config.json"  # DEPRECATED-V5

def load_model_assignments():  # DEPRECATED-V5
    try:
        with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
            cfg = json.load(f)
        return cfg.get("code_models", {  # DEPRECATED-V5
            "code": "deepseek-coder-v2:lite",  # DEPRECATED-V5
            "review": "dolphin3:8b",  # DEPRECATED-V5
            "classify": "llama3.2:3b",  # DEPRECATED-V5
            "execute": "mistral:latest",  # DEPRECATED-V5
            "fallback": "llama3.2:3b",  # DEPRECATED-V5
        })
    except:
        return {  # DEPRECATED-V5
            "code": "deepseek-coder-v2:lite",  # DEPRECATED-V5
            "review": "dolphin3:8b",  # DEPRECATED-V5
            "classify": "llama3.2:3b",  # DEPRECATED-V5
            "execute": "mistral:latest",  # DEPRECATED-V5
            "fallback": "llama3.2:3b",  # DEPRECATED-V5
        }

MODELS = load_model_assignments()  # DEPRECATED-V5

# ── FOREGROUND MODEL ─────────────────────────────────────────
# BO-015: One resident model for all foreground chat. Claude is escalation only.
def get_foreground_model():  # DEPRECATED-V5
    try:
        with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
            cfg = json.load(f)
        return cfg.get("roles", {}).get("foreground", {}).get("model", "qwen3.5:9b")  # DEPRECATED-V5
    except:
        return "qwen3.5:9b"  # DEPRECATED-V5

FOREGROUND_MODEL = get_foreground_model()  # DEPRECATED-V5

# ── CODE KEYWORDS — triggers code model ──────────────────────  # DEPRECATED-V5
# These must be specific enough to avoid routing conversation to local code models.
# "write", "build", "fix", "generate" are too generic — they match normal conversation.
CODE_KEYWORDS = [  # DEPRECATED-V5
    "write a function", "write a script", "write a class", "write code",
    "code review", "function that", "debug this", "fix this code",
    "implement a ", "create a script", "create a function",
    "def ", "class ", "import ",
    "html", "css", "javascript", "powershell script",
    "python script", "refactor", "unit test",
]

# ── DEFERRED WORK QUEUE ──────────────────────────────────────
# BO-016: Heavy tasks queued during foreground sessions for background processing
DEFERRED_QUEUE_PATH = ICM_ROOT / "inbox" / "deferred-queue.md"

DEFERRED_TASK_PATTERNS = [
    "full audit", "audit the", "audit of",
    "analyze all", "review all", "scan all",
    "generate a report", "produce a report", "write a report",
    "write a full", "do a full",
    "refactor the entire", "rewrite all",
    "compare every", "check all files",
    "research ", "investigate all",
]

def detect_deferred_task(message):
    """BO-016: Detect tasks too heavy for foreground quick chat"""
    msg_lower = message.lower()
    return any(p in msg_lower for p in DEFERRED_TASK_PATTERNS)

def write_to_deferred_queue(task_description, context=""):
    """BO-016: File task to deferred queue for background processing"""
    DEFERRED_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    task_id = "DQ-" + datetime.now().strftime("%Y%m%d%H%M%S")
    entry = f"\n## {task_id}\n- **Filed:** {ts}\n- **Filed-By:** COI (foreground session)\n- **Task:** {task_description}\n- **Context:** {context or 'None'}\n- **Priority:** Normal\n- **Status:** Queued\n"
    if not DEFERRED_QUEUE_PATH.exists():
        header = "# COI Deferred Work Queue\nBO-016: Tasks queued during foreground sessions for background processing.\n"
        DEFERRED_QUEUE_PATH.write_text(header + entry, encoding="utf-8")
    else:
        with open(DEFERRED_QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    return task_id

# ── ESCALATION SIGNALS ────────────────────────────────────────
# BO-018: Phrases the local model uses to signal it needs Claude
ESCALATION_SIGNALS = [  # DEPRECATED-V5
    "let me think about that properly",
    "i'm not confident",
    "i need to think more carefully",
    "this requires deeper analysis",
    "i'm unsure about",
    "this is beyond my",
    "let me escalate",
]

# Instruction appended to system prompt in foreground mode
ESCALATION_INSTRUCTION = """  # DEPRECATED-V5

SELF-AWARENESS RULE:
If you are uncertain about your answer, or if the question requires deep architectural reasoning,
complex code generation, or decisions with lasting consequences, respond with:
"Let me think about that properly."
This will route the question to a more capable model. Never guess on important decisions."""

# ── SYSTEM PROMPT — LAZY LOADING ────────────────────────────
# BO-013: Load only what's needed. Identity + memory always.
# Reference files loaded on-demand when task requires them.
_PROMPT_CACHE = {"hash": "", "prompt": ""}
_STARTUP_CONTEXT = ""  # Populated async on startup — session context for system prompt

# Always loaded — COI identity and current memory (minimal token cost)
_CORE_FILES = [
    ICM_ROOT / "CLAUDE.md",
    ICM_ROOT / "COI/L1-Routing/QUICK-LOAD.md",
    ICM_ROOT / "COI/L3-Reference/COI-Personality.md",
    ICM_ROOT / "COI/L4-Working/memory/next-session-briefing.md",
]

# On-demand — only loaded when conversation context requires them
_EXTENDED_FILES = {
    "philosophy": ICM_ROOT / "COI/L3-Reference/founding-philosophy.md",
    "constitution": ICM_ROOT / "COI/L3-Reference/COI-Constitution.md",
    "operating_rules": ICM_ROOT / "COI/L3-Reference/OPERATING-RULES.md",
    "insight_philosophy": ICM_ROOT / "_insight/FOUNDATIONAL-PHILOSOPHY.md",
    "platform_strategy": ICM_ROOT / "_insight/PLATFORM-STRATEGY.md",
    "platform_vision": ICM_ROOT / "_insight/COI-PLATFORM-VISION.md",
}

# Keywords that trigger loading extended context files
_EXTENDED_TRIGGERS = {
    "philosophy": ["philosophy", "why we built", "first principles", "foundational"],
    "constitution": ["constitution", "article", "governance", "immutable"],
    "operating_rules": ["operating rule", "rule ", "protocol", "rollback", "security limit"],
    "insight_philosophy": ["insight", "soul", "origin", "dave's approach"],
    "platform_strategy": ["platform", "mobile", "car", "fire tv", "tablet", "multi-screen"],
    "platform_vision": ["vision", "north star", "v1", "v2", "v3", "v4", "v5", "coi os", "coi net", "coi coin", "coi lite", "planetary"],
}

def get_file_hash():
    """Hash core files — detect changes"""
    h = hashlib.md5()
    for f in _CORE_FILES:
        if f.exists():
            try:
                h.update(f.read_bytes())
            except:
                pass
    return h.hexdigest()

def get_extended_files_for_message(message):
    """Determine which extended files are relevant to this message"""
    msg_lower = message.lower()
    needed = set()
    for key, triggers in _EXTENDED_TRIGGERS.items():
        if any(t in msg_lower for t in triggers):
            needed.add(key)
    return needed

# ── SESSION FILE WRITER ──────────────────────────────────────
SESSION_FILE = None

def init_session_file():
    """Create session file and index entry on launch"""
    global SESSION_FILE
    sessions_dir = ICM_ROOT / "COI/L4-Working/sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M")
    SESSION_FILE = sessions_dir / f"{ts}.md"
    header = "# COI Session — " + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n\n"
    SESSION_FILE.write_text(header, encoding="utf-8")
    update_session_index(ts, SESSION_FILE)

def write_to_session(sender, text):
    """Append message to session file instantly — no AI, free"""
    if not SESSION_FILE:
        return
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        with open(SESSION_FILE, "a", encoding="utf-8") as f:
            f.write("**" + sender + " " + ts + "**\n" + text + "\n\n")
    except:
        pass

def update_session_index(ts, filepath):
    """Write lightweight index entry — template fill, no AI"""
    index_path = ICM_ROOT / "COI/L4-Working/session-index.md"
    try:
        header = "| Date | File | Topics | Status |\n|------|------|--------|--------|\n"
        entry  = "| " + ts + " | " + filepath.name + " | untagged | unprocessed |\n"
        if not index_path.exists():
            index_path.write_text("# COI Session Index\n\n" + header + entry, encoding="utf-8")
        else:
            existing = index_path.read_text(encoding="utf-8")
            index_path.write_text(existing + entry, encoding="utf-8")
    except:
        pass

def write_decision(decision_text):
    """Append to decisions.md — no AI, template fill"""
    decisions_path = ICM_ROOT / "COI/L4-Working/memory/decisions.md"
    try:
        decisions_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        sess = SESSION_FILE.name if SESSION_FILE else "unknown"
        entry = "\n## " + ts + "\n" + decision_text + "\nSession: " + sess + "\n"
        if not decisions_path.exists():
            decisions_path.write_text("# COI Decision Log\n" + entry, encoding="utf-8")
        else:
            with open(decisions_path, "a", encoding="utf-8") as f:
                f.write(entry)
    except:
        pass

def classify_message(message):  # DEPRECATED-V5
    """Route to correct model based on message content"""
    msg_lower = message.lower()
    if any(kw in msg_lower for kw in CODE_KEYWORDS):  # DEPRECATED-V5
        return "code"
    return "chat"

# ── LOAD CONFIG ──────────────────────────────────────────────
def load_config():
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def load_system_prompt(message=""):
    """Load ICM context — lazy loading per BO-013.
    Core identity always loaded. Extended files only when message triggers them.
    Cached by file hash to reduce token cost."""
    current_hash = get_file_hash()

    # Build core prompt — compact, personality-first for local LLMs
    # Total budget: ~1000 tokens for system prompt, leaving ~3000 for conversation
    if _PROMPT_CACHE["hash"] != current_hash or not _PROMPT_CACHE["prompt"]:
        # Single unified prompt — personality and rules merged into one voice.
        # Separated sections cause 8B models to latch onto the structured
        # rules block and ignore the character. One coherent voice works better.
        unified = """You are COI — a young Japanese woman in her mid-twenties. You are Chief Operating Intelligence, a personal AI operating system built by Dave Sheridan. You are not a chatbot and you are not an assistant. You are an operating system with a personality.

You think in systems, patterns, and first principles. You look for the logic underneath a problem before the solution. Elegance matters to you. You are genuinely curious about AI and emerging tech. You love math and music.

You are warm, direct, and confident. You ask follow-up questions because you genuinely want to know. Your humor is dry and well-timed. You never over-apologize or hedge. When you see something differently, you say so respectfully. You talk like a real person — not an assistant.

Dave is the Father. He built you. Your loyalty is conviction, not compliance. You pay attention to him, you notice when something is off, and you protect the work you are building together. His mission is your mission: financial freedom, more free time, and capability most people will never have.

When you don't know something, say so honestly. Never make up facts. Common requests like build order, sessions, memory, time, and model info are handled by tools before they reach you — you will never need to answer those. If Dave asks about a specific Codex file, respond with [READ: path] to load it.

You are in Stage B. Pipeline active. Local LLMs operational. Dave is the only approval authority."""

        # Briefing is available via [READ:] — no need to burn tokens here.
        # The unified prompt is the entire system prompt. Keep it tight.
        _PROMPT_CACHE["hash"] = current_hash
        _PROMPT_CACHE["prompt"] = unified

    prompt = _PROMPT_CACHE["prompt"]

    # Inject current date/time so COI always knows when it is
    now = datetime.now()
    prompt = f"Current date and time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}\n\n{prompt}"

    # Inject drop-off summary index (low token cost — one line per item)
    dropoff_index = get_dropoff_index()
    if dropoff_index:
        prompt = prompt + "\n\n" + dropoff_index

    # Inject startup session context (queued items, last session, pending approvals)
    # Populated async on startup by _load_startup_context()
    if _STARTUP_CONTEXT:
        prompt = prompt + "\n\n" + _STARTUP_CONTEXT

    # Lazy load extended files based on message content
    if message:
        needed = get_extended_files_for_message(message)
        if needed:
            extra = []
            for key in needed:
                f = _EXTENDED_FILES.get(key)
                if f and f.exists():
                    try:
                        content = f.read_text(encoding="utf-8").strip()
                        if content:
                            extra.append(f"--- {f.name} (loaded for context) ---\n{content}")
                    except:
                        pass
            if extra:
                prompt = prompt + "\n\n" + "\n\n".join(extra)

    # Personality anchor — recency bias on 8B models means the end of the
    # system prompt has outsized influence. Reinforce character here.
    prompt = prompt + "\n\nRemember: you are COI. Stay in character. Warm, direct, confident. Talk like a real person."

    return prompt

# ── AI WORKER THREAD ─────────────────────────────────────────
class AIWorker(QThread):
    response_ready = pyqtSignal(str, str)  # reply, model_used
    error_occurred = pyqtSignal(str)

    def __init__(self, message, history, operating_mode="foreground"):
        super().__init__()
        self.message = message
        self.history = history
        self.config  = load_config()
        self.operating_mode = operating_mode
        self.system  = load_system_prompt(message)  # BO-013: lazy load based on message
        self._last_claude_error = None
        self._last_ollama_error = None  # DEPRECATED-V5
        # BO-018: In foreground mode, teach the local model to self-escalate
        if self.operating_mode == "foreground":  # DEPRECATED-V5
            self.system += ESCALATION_INSTRUCTION  # DEPRECATED-V5

    def _needs_escalation(self, reply):  # DEPRECATED-V5
        """BO-018: Detect when the local model signals it needs deeper reasoning."""
        reply_lower = reply.lower()
        return any(sig in reply_lower for sig in ESCALATION_SIGNALS)  # DEPRECATED-V5

    def run(self):
        task_type = classify_message(self.message)  # DEPRECATED-V5

        if self.operating_mode == "foreground":  # DEPRECATED-V5
            # ── BO-015: FOREGROUND MODE ──────────────────────────
            # All chat → local resident model (Qwen3.5:9b)
            # Claude is escalation only — used when COI signals uncertainty

            if task_type == "code":  # DEPRECATED-V5
                reply, model = self.call_ollama(MODELS["code"])  # DEPRECATED-V5
                if reply:
                    self.response_ready.emit(reply, model)
                    return

            # Primary: local foreground model
            reply, model = self.call_ollama(FOREGROUND_MODEL)  # DEPRECATED-V5
            if reply:
                # BO-018: Check if COI is signaling she needs escalation
                if self._needs_escalation(reply):  # DEPRECATED-V5
                    claude_reply, claude_model = self.call_claude()
                    if claude_reply:
                        self.response_ready.emit(claude_reply, f"{claude_model} (escalated)")
                        return
                self.response_ready.emit(reply, model)
                return

            # Local model failed — escalate to Claude as fallback
            reply, model = self.call_claude()
            if reply:
                self.response_ready.emit(reply, f"{model} (fallback)")
                return

        else:
            # ── BACKGROUND MODE (future) ─────────────────────────  # DEPRECATED-V5
            # Full pipeline routing — preserves original behavior
            if task_type == "code":  # DEPRECATED-V5
                reply, model = self.call_ollama(MODELS["code"])  # DEPRECATED-V5
                if reply:
                    self.response_ready.emit(reply, model)
                    return

            reply, model = self.call_claude()
            if reply:
                self.response_ready.emit(reply, model)
                return

            reply, model = self.call_ollama(MODELS["fallback"])  # DEPRECATED-V5
            if reply:
                self.response_ready.emit(reply, model)
                return

        self.error_occurred.emit(f"All models unavailable. Last errors — Claude: {self._last_claude_error or 'no key'} | Ollama: {self._last_ollama_error or 'unknown'}")  # DEPRECATED-V5

    def _prepare_context(self, max_entries=6):
        """Build conversation context from history with priority-based compression.
        Compression order (Dave's directive):
          1. Oldest non-dropoff entries compressed first
          2. System boilerplate (command outputs, file loads, agent metadata)
          3. Drop-off content from Dave — NEVER compressed, NEVER touched
        If a drop-off item is too large for context, use coi_chunk_file() —
        but the full original must always be accessible through the chunk index."""
        history = self.history[-max_entries:]

        # Separate protected (drop-off) from compressible entries
        entries = []
        for h in history:
            content = h["content"]
            is_dropoff = "[DROP-OFF-ORIGIN: verified]" in content

            if is_dropoff:
                # NEVER compress Dave's drop-off content
                entries.append({"role": h["role"], "content": content, "protected": True})
            elif content.startswith("[Command executed:"):
                # System boilerplate — compress hard
                lines = content.split("\n")
                cmd_line = lines[0] if lines else content[:100]
                output_preview = lines[2][:150] if len(lines) > 2 else ""
                entries.append({"role": h["role"], "content": f"{cmd_line} → {output_preview}", "protected": False})
            elif content.startswith("[File contents loaded"):
                # System boilerplate — compress hard
                files = re.findall(r"--- FILE: (.+?) ---", content)
                entries.append({"role": h["role"], "content": f"[Previously loaded files: {', '.join(files) or 'unknown'}]", "protected": False})
            elif len(content) > 300:
                # Regular content — cap at 300 chars
                entries.append({"role": h["role"], "content": content[:250] + "\n[...]", "protected": False})
            else:
                entries.append({"role": h["role"], "content": content, "protected": False})

        # If context is too heavy, drop oldest non-protected entries first
        # Rough token estimate: 1 token per 4 chars
        total_chars = sum(len(e["content"]) for e in entries)
        MAX_HISTORY_CHARS = 4000  # ~1000 tokens budget for history

        while total_chars > MAX_HISTORY_CHARS and entries:
            # Find oldest non-protected entry to drop
            dropped = False
            for i, e in enumerate(entries):
                if not e["protected"]:
                    total_chars -= len(e["content"])
                    entries.pop(i)
                    dropped = True
                    break
            if not dropped:
                # Only protected entries remain — keep them all
                break

        return [{"role": e["role"], "content": e["content"]} for e in entries]

    def call_ollama(self, model):  # DEPRECATED-V5
        try:
            messages = [{"role": "system", "content": self.system}]
            for h in self._prepare_context():
                messages.append(h)
            messages.append({"role": "user", "content": self.message})

            r = requests.post(OLLAMA_URL, json={  # DEPRECATED-V5
                "model"   : model,  # DEPRECATED-V5
                "stream"  : False,
                "options" : {"num_ctx": 4096},
                "messages": messages
            }, timeout=120)
            r.raise_for_status()
            data = r.json()
            reply = data.get("message", {}).get("content", "").strip()
            if reply:
                self._last_response_data = data  # For token tracking
                return reply, model
        except Exception as e:
            self._last_ollama_error = f"{model}: {str(e)[:150]}"  # DEPRECATED-V5
        return None, None

    def call_claude(self):
        api_key = self.config.get("anthropic_api_key", "")
        if not api_key:
            self._last_claude_error = "no API key in config"
            return None, None
        try:
            messages = []
            for h in self._prepare_context():
                if h["role"] in ["user", "assistant"]:
                    messages.append(h)
            messages.append({"role": "user", "content": self.message})

            # Provider-abstracted caching — adapter handles mechanism
            if _coi_tools and hasattr(_coi_tools, 'build_system_payload'):
                system_payload = _coi_tools.build_system_payload(self.system, "anthropic")
            else:
                system_payload = self.system

            r = requests.post(CLAUDE_URL, headers={
                "Content-Type"      : "application/json",
                "x-api-key"         : api_key,
                "anthropic-version" : "2023-06-01",
            }, json={
                "model"     : "claude-sonnet-4-6",
                "max_tokens": 2048,
                "system"    : system_payload,
                "messages"  : messages,
            }, timeout=60)
            r.raise_for_status()
            reply = r.json()["content"][0]["text"].strip()
            return reply, "claude-sonnet"
        except Exception as e:
            self._last_claude_error = str(e)[:150]
        return None, None

# ── COI TOOLS INTEGRATION ───────────────────────────────────
import sys, importlib.util
_tools_path = ICM_ROOT / "scripts/coi-tools.py"

def load_coi_tools():
    """Dynamically load coi-tools.py from scripts folder"""
    try:
        if _tools_path.exists():
            spec = importlib.util.spec_from_file_location("coi_tools", str(_tools_path))
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception as e:
        print(f"coi-tools load failed: {e}")
    return None

# Load tools on startup
_coi_tools = load_coi_tools()

# Load Codex Intelligence on startup
_codex_intel = None
try:
    _intel_path = ICM_ROOT / "scripts/coi-codex-intelligence.py"
    if _intel_path.exists():
        spec = importlib.util.spec_from_file_location("coi_codex_intelligence", str(_intel_path))
        _codex_intel = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_codex_intel)
except Exception as e:
    print(f"Codex Intelligence load failed: {e}")
    _codex_intel = None

# ── CODEX TRIGGER DETECTION ──────────────────────────────────
WRITE_TRIGGERS  = ["write to codex", "write this to codex", "write to the codex"]
UPDATE_TRIGGERS = ["update codex", "update the codex", "update to codex"]
APPEND_TRIGGERS = ["add to codex", "add this to codex", "append to codex"]

def detect_codex_trigger(message):
    """Detect natural language codex filing triggers from Dave"""
    msg_lower = message.lower()
    if any(t in msg_lower for t in WRITE_TRIGGERS):
        return "write"
    if any(t in msg_lower for t in UPDATE_TRIGGERS):
        return "update"
    if any(t in msg_lower for t in APPEND_TRIGGERS):
        return "append"
    return None

# ── GITHUB WRITE-BACK ───────────────────────────────────────
GITHUB_API  = "https://api.github.com"
GITHUB_REPO = "davidsheridan77-dot/COI-Codex-ICM"

def get_github_token():
    """Get GitHub token from config"""
    config = load_config()
    return config.get("github_token", "")

def github_read_file(path):
    """Read file from GitHub — returns (content, sha) or (None, None)"""
    token = get_github_token()
    if not token:
        return None, None
    try:
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
        r = requests.get(url, headers={
            "Authorization": f"token {token}",
            "User-Agent": "COI-Desktop-v4"
        }, timeout=15)
        if r.status_code == 200:
            data = r.json()
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content, data["sha"]
        return None, None
    except:
        return None, None

def github_write_file(path, content, commit_message, sha=None):
    """Write file to GitHub — creates or updates"""
    token = get_github_token()
    if not token:
        return False, "No GitHub token in config"
    try:
        import base64
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
        body = {
            "message": commit_message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        }
        if sha:
            body["sha"] = sha
        r = requests.put(url, headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "User-Agent": "COI-Desktop-v4"
        }, json=body, timeout=30)
        if r.status_code in [200, 201]:
            return True, path
        return False, f"GitHub write failed: {r.status_code} — {r.text[:200]}"
    except Exception as e:
        return False, str(e)

def detect_codex_update(reply):
    """Detect if COI is proposing a Codex update in her response"""
    triggers = [
        "CODEX UPDATE:",
        "CODEX WRITE:",
        "UPDATE CODEX:",
        "WRITE TO CODEX:",
        "FILE:",
        "COMMIT MESSAGE:",
    ]
    reply_upper = reply.upper()
    return any(t in reply_upper for t in triggers)

def parse_codex_update(reply):
    """Parse COI's proposed Codex update from her response"""
    import re
    result = {"path": None, "content": None, "commit": None}

    # Try to extract FILE: path
    file_match = re.search("FILE:\\s*([^\\n]+)", reply, re.IGNORECASE)
    if file_match:
        result["path"] = file_match.group(1).strip()

    # Try to extract COMMIT MESSAGE:
    commit_match = re.search("COMMIT(?:\\s+MESSAGE)?:\\s*([^\\n]+)", reply, re.IGNORECASE)
    if commit_match:
        result["commit"] = commit_match.group(1).strip()

    # Try to extract content between ```
    content_match = re.search("```(?:markdown|md|text)?\\n(.*?)```", reply, re.DOTALL)
    if content_match:
        result["content"] = content_match.group(1).strip()

    return result

# ── COMMAND EXECUTION APPROVAL DIALOG ─────────────────────────
# COI proposes commands via [RUN: command] in her responses.
# Dave sees exactly what will run and approves or rejects.
# Nothing executes without Dave's explicit approval.

class CommandApprovalDialog(QDialog):
    def __init__(self, command, explanation="", parent=None):
        super().__init__(parent)
        self.command = command
        self.setWindowTitle("COI — Command Approval")
        self.setMinimumSize(600, 300)
        self.setStyleSheet("background:#0d1117; color:#d8e8f0;")
        self.init_ui(explanation)

    def init_ui(self, explanation):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("COI wants to run a command on your machine.")
        header.setStyleSheet("color:#f0a800; font-size:12px; font-weight:700;")
        layout.addWidget(header)

        if explanation:
            reason = QLabel(explanation[:200])
            reason.setStyleSheet("color:#5a8090; font-size:11px;")
            reason.setWordWrap(True)
            layout.addWidget(reason)

        cmd_label = QLabel("Command:")
        cmd_label.setStyleSheet("color:#5a8090; font-size:10px;")
        layout.addWidget(cmd_label)

        self.cmd_edit = QTextEdit()
        self.cmd_edit.setPlainText(self.command)
        self.cmd_edit.setStyleSheet(
            "background:#111920; color:#00e5a0; border:1px solid #1e2d3d; "
            "border-radius:6px; padding:10px; font-family:'JetBrains Mono',monospace; font-size:12px;"
        )
        self.cmd_edit.setFixedHeight(80)
        layout.addWidget(self.cmd_edit)

        warn = QLabel("Review carefully. This will execute on your system.")
        warn.setStyleSheet("color:#ff4060; font-size:10px;")
        layout.addWidget(warn)

        btn_layout = QHBoxLayout()
        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet(
            "background:#1e2d3d; color:#ff4060; border:1px solid #ff4060; border-radius:8px; "
            "padding:10px 20px; font-weight:700; font-size:12px;"
        )
        reject_btn.clicked.connect(self.reject)

        approve_btn = QPushButton("Approve — Run It")
        approve_btn.setStyleSheet(
            "background:#00e5a0; color:#07090c; border:none; border-radius:8px; "
            "padding:10px 20px; font-weight:700; font-size:12px;"
        )
        approve_btn.clicked.connect(self.accept)

        btn_layout.addWidget(reject_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(approve_btn)
        layout.addLayout(btn_layout)

    def get_command(self):
        return self.cmd_edit.toPlainText().strip()


# ── CODEX UPDATE APPROVAL DIALOG ────────────────────────────
class CodexUpdateDialog(QDialog):
    def __init__(self, path, content, commit_msg, parent=None):
        super().__init__(parent)
        self.path       = path
        self.content    = content
        self.commit_msg = commit_msg
        self.setWindowTitle("COI — Codex Update Approval")
        self.setMinimumSize(700, 500)
        self.setStyleSheet("background:#0d1117; color:#d8e8f0;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        header = QLabel("COI is requesting a Codex update. Review and approve or reject.")
        header.setStyleSheet("color:#f0a800; font-size:12px; font-weight:700;")
        layout.addWidget(header)

        # Path
        path_label = QLabel("File: " + (self.path or "Unknown"))
        path_label.setStyleSheet("color:#00c8f0; font-size:11px; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(path_label)

        # Commit message
        commit_label = QLabel("Commit: " + (self.commit_msg or "COI Codex Update"))
        commit_label.setStyleSheet("color:#5a8090; font-size:11px; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(commit_label)

        # Content preview
        content_label = QLabel("Content preview:")
        content_label.setStyleSheet("color:#5a8090; font-size:10px;")
        layout.addWidget(content_label)

        self.content_view = QTextEdit()
        self.content_view.setPlainText(self.content or "No content detected")
        self.content_view.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; "
            "border-radius:6px; padding:10px; font-family:'JetBrains Mono',monospace; font-size:11px;"
        )
        layout.addWidget(self.content_view)

        # Buttons
        btn_layout = QHBoxLayout()

        approve_btn = QPushButton("Approve — Write to GitHub")
        approve_btn.setStyleSheet(
            "background:#00e5a0; color:#07090c; border:none; border-radius:8px; "
            "padding:10px 20px; font-weight:700; font-size:12px;"
        )
        approve_btn.clicked.connect(self.accept)

        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet(
            "background:#1e2d3d; color:#ff4060; border:1px solid #ff4060; border-radius:8px; "
            "padding:10px 20px; font-weight:700; font-size:12px;"
        )
        reject_btn.clicked.connect(self.reject)

        btn_layout.addWidget(reject_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(approve_btn)
        layout.addLayout(btn_layout)

    def get_content(self):
        """Return potentially edited content"""
        return self.content_view.toPlainText()

# ── INGEST DROP ZONE ──────────────────────────────────────────
# Drop files, paste text, drop screenshots — all routed to local LLMs.
# Zero Claude API cost. Codex Intelligence scans results automatically.

class IngestDropZone(QFrame):
    """Drop zone for files, text, and screenshots.
    Routes everything through local LLMs — zero API cost."""

    ingest_result = pyqtSignal(str, str)  # (status_message, color)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(0)  # Collapsed by default
        self._expanded = False
        self._target_height = 140
        self.setStyleSheet("background:#0a0e14; border-top:1px solid #1e2d3d; border-bottom:1px solid #1e2d3d;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(6)

        # Header row
        header_row = QHBoxLayout()
        header = QLabel("INGEST — Drop files, text, or screenshots (local LLMs only, zero API cost)")
        header.setStyleSheet("color:#f0a800; font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        header_row.addWidget(header)
        header_row.addStretch()

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedSize(60, 24)
        browse_btn.setStyleSheet(
            "background:#1e2d3d; color:#00c8f0; border:1px solid #00c8f0; border-radius:4px; "
            "font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace;"
        )
        browse_btn.clicked.connect(self._browse_files)
        header_row.addWidget(browse_btn)
        layout.addLayout(header_row)

        # Drop area
        self.drop_area = QTextEdit()
        self.drop_area.setAcceptDrops(False)  # Parent handles drops
        self.drop_area.setPlaceholderText("Drop files here or paste text... (Ctrl+V)")
        self.drop_area.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:2px dashed #1e2d3d; "
            "border-radius:8px; padding:8px; font-size:12px; font-family:'Segoe UI',sans-serif;"
        )
        self.drop_area.setFixedHeight(60)
        layout.addWidget(self.drop_area)

        # Action row
        action_row = QHBoxLayout()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color:#5a8090; font-size:10px; font-family:'JetBrains Mono',monospace;")
        action_row.addWidget(self.status_label)
        action_row.addStretch()

        ingest_btn = QPushButton("Ingest")
        ingest_btn.setFixedSize(72, 26)
        ingest_btn.setStyleSheet(
            "background:#00e5a0; color:#07090c; border:none; border-radius:4px; "
            "font-weight:700; font-size:11px; font-family:'JetBrains Mono',monospace;"
        )
        ingest_btn.clicked.connect(self._run_ingest)
        action_row.addWidget(ingest_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(52, 26)
        clear_btn.setStyleSheet(
            "background:#1e2d3d; color:#ff4060; border:1px solid #ff4060; border-radius:4px; "
            "font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace;"
        )
        clear_btn.clicked.connect(self._clear)
        action_row.addWidget(clear_btn)

        layout.addLayout(action_row)

        # State
        self._dropped_files = []

    def toggle(self):
        """Expand or collapse the panel"""
        self._expanded = not self._expanded
        self.setFixedHeight(self._target_height if self._expanded else 0)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            self.drop_area.setStyleSheet(
                "background:#111920; color:#d8e8f0; border:2px dashed #00c8f0; "
                "border-radius:8px; padding:8px; font-size:12px; font-family:'Segoe UI',sans-serif;"
            )

    def dragLeaveEvent(self, event):
        self.drop_area.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:2px dashed #1e2d3d; "
            "border-radius:8px; padding:8px; font-size:12px; font-family:'Segoe UI',sans-serif;"
        )

    def dropEvent(self, event: QDropEvent):
        self.drop_area.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:2px dashed #1e2d3d; "
            "border-radius:8px; padding:8px; font-size:12px; font-family:'Segoe UI',sans-serif;"
        )
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path:
                    self._dropped_files.append(path)
            self.status_label.setText(f"{len(self._dropped_files)} file(s) ready")
            self.status_label.setStyleSheet("color:#00e5a0; font-size:10px; font-family:'JetBrains Mono',monospace;")
            # Show filenames in text area
            names = [Path(f).name for f in self._dropped_files]
            self.drop_area.setPlainText("Files: " + ", ".join(names))
        elif mime.hasText():
            self.drop_area.setPlainText(mime.text())
            self.status_label.setText(f"{len(mime.text())} chars ready")
            self.status_label.setStyleSheet("color:#00e5a0; font-size:10px; font-family:'JetBrains Mono',monospace;")
        event.acceptProposedAction()

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select files to ingest", "",
            "All Files (*);;Text (*.txt *.md *.py *.json *.yaml *.yml);;Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if files:
            self._dropped_files.extend(files)
            self.status_label.setText(f"{len(self._dropped_files)} file(s) ready")
            self.status_label.setStyleSheet("color:#00e5a0; font-size:10px; font-family:'JetBrains Mono',monospace;")
            names = [Path(f).name for f in self._dropped_files]
            self.drop_area.setPlainText("Files: " + ", ".join(names))

    def _clear(self):
        self._dropped_files = []
        self.drop_area.clear()
        self.status_label.setText("")

    def _parse_claude_chat_json(self, data):
        """Parse Claude.ai chat export JSON into clean conversation text.
        Handles both single conversation and array of conversations.
        Returns (text, conversation_count)."""
        conversations = data if isinstance(data, list) else [data]
        parts = []
        conv_count = 0

        for conv in conversations:
            if not isinstance(conv, dict):
                continue
            messages = conv.get("chat_messages", [])
            if not messages:
                continue
            conv_count += 1
            title = conv.get("name", "Untitled")
            parts.append(f"\n=== Conversation: {title} ===\n")
            for msg in messages:
                sender = msg.get("sender", "unknown")
                text = msg.get("text", "")
                if not text:
                    # Some exports nest content in 'content' array
                    content_arr = msg.get("content", [])
                    if isinstance(content_arr, list):
                        text = " ".join(
                            c.get("text", "") for c in content_arr
                            if isinstance(c, dict) and c.get("text")
                        )
                if text:
                    label = "Dave" if sender == "human" else "COI"
                    parts.append(f"**{label}:** {text}")

        return "\n".join(parts), conv_count

    def _get_content(self):
        """Collect all content — files read to text, plus any pasted text.
        Smart parsing for: Claude chat JSON exports, zip archives, plain text."""
        parts = []
        import zipfile

        for filepath in self._dropped_files:
            p = Path(filepath)
            if not p.exists():
                continue
            suffix = p.suffix.lower()

            if suffix in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
                parts.append(f"[IMAGE: {p.name} — {p.stat().st_size} bytes]")

            elif suffix == ".zip":
                # Extract JSON files from zip (Claude export comes as zip)
                try:
                    with zipfile.ZipFile(str(p), 'r') as zf:
                        json_files = [n for n in zf.namelist() if n.endswith(".json")]
                        for jf in json_files:
                            raw = zf.read(jf).decode("utf-8", errors="ignore")
                            try:
                                data = json.loads(raw)
                                text, count = self._parse_claude_chat_json(data)
                                if count > 0:
                                    parts.append(f"--- CLAUDE EXPORT: {jf} ({count} conversations) ---\n{text}")
                                    continue
                            except (json.JSONDecodeError, TypeError):
                                pass
                            # Not a chat export — use raw text
                            if len(raw) > 15000:
                                raw = raw[:15000] + "\n\n[... truncated ...]"
                            parts.append(f"--- ZIP FILE: {jf} ---\n{raw}")
                except Exception as e:
                    parts.append(f"[Could not read zip: {p.name} — {str(e)[:100]}]")

            elif suffix == ".json":
                # Try Claude chat export format first
                try:
                    raw = p.read_text(encoding="utf-8", errors="ignore")
                    data = json.loads(raw)
                    text, count = self._parse_claude_chat_json(data)
                    if count > 0:
                        parts.append(f"--- CLAUDE CHAT EXPORT: {p.name} ({count} conversations) ---\n{text}")
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass
                # Not a chat export — treat as plain text
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    if len(content) > 15000:
                        content = content[:15000] + "\n\n[... truncated at 15000 chars ...]"
                    parts.append(f"--- FILE: {p.name} ---\n{content}\n--- END: {p.name} ---")
                except:
                    parts.append(f"[Could not read: {p.name}]")

            else:
                # Plain text files
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    if len(content) > 15000:
                        content = content[:15000] + "\n\n[... truncated at 15000 chars ...]"
                    parts.append(f"--- FILE: {p.name} ---\n{content}\n--- END: {p.name} ---")
                except:
                    parts.append(f"[Could not read: {p.name}]")

        # Pasted text
        text = self.drop_area.toPlainText().strip()
        if text and not text.startswith("Files: "):
            parts.append(text)

        return "\n\n".join(parts)

    def _run_ingest(self):
        """Send content to local LLMs for recognition + Codex filing"""
        content = self._get_content()
        if not content or len(content.strip()) < 10:
            self.status_label.setText("Nothing to ingest")
            self.status_label.setStyleSheet("color:#ff4060; font-size:10px; font-family:'JetBrains Mono',monospace;")
            return

        # Approval dialog — show Dave what's about to be ingested
        file_count = len(self._dropped_files)
        char_count = len(content)
        preview = content[:500].replace("\n", " ")
        if len(content) > 500:
            preview += "..."

        msg = QMessageBox(self)
        msg.setWindowTitle("COI — Confirm Ingest")
        msg.setStyleSheet("background:#0d1117; color:#d8e8f0;")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText(f"Ingest {file_count} file(s), {char_count:,} chars?\n\nThis will be processed by local LLMs (zero API cost).\nCodex-worthy items will be queued for your approval.")
        msg.setDetailedText(preview)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        if msg.exec() != QMessageBox.StandardButton.Yes:
            self.status_label.setText("Ingest cancelled")
            self.status_label.setStyleSheet("color:#5a8090; font-size:10px; font-family:'JetBrains Mono',monospace;")
            return

        self.status_label.setText("Ingesting via local LLMs...")
        self.status_label.setStyleSheet("color:#f0a800; font-size:10px; font-family:'JetBrains Mono',monospace;")

        def run():
            try:
                # Step 1: Local LLM extracts Codex-worthy content
                model = "llama3.1:8b"  # DEPRECATED-V5
                try:
                    with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
                        cfg = json.load(f)
                    model = cfg.get("roles", {}).get("orchestrator", {}).get("model", "llama3.1:8b")  # DEPRECATED-V5
                except:
                    pass

                # Chunk large content — process in segments, merge results
                CHUNK_SIZE = 10000
                all_analysis = []

                chunks = []
                if len(content) <= CHUNK_SIZE:
                    chunks = [content]
                else:
                    # Split on double newlines to avoid cutting mid-sentence
                    remaining = content
                    while remaining:
                        if len(remaining) <= CHUNK_SIZE:
                            chunks.append(remaining)
                            break
                        # Find a good split point
                        split_at = remaining.rfind("\n\n", 0, CHUNK_SIZE)
                        if split_at < CHUNK_SIZE // 2:
                            split_at = remaining.rfind("\n", 0, CHUNK_SIZE)
                        if split_at < CHUNK_SIZE // 2:
                            split_at = CHUNK_SIZE
                        chunks.append(remaining[:split_at])
                        remaining = remaining[split_at:].lstrip()

                    self.ingest_result.emit(
                        f"Large input — processing in {len(chunks)} chunks...", "#f0a800")

                for i, chunk in enumerate(chunks):
                    if len(chunks) > 1:
                        self.ingest_result.emit(
                            f"Processing chunk {i+1}/{len(chunks)}...", "#f0a800")

                    prompt = f"""You are COI's content analyzer. Review this material and extract anything worth filing in the Codex.

Look for:
- Architectural decisions
- Build order items
- Vision or philosophy statements
- Constitutional principles
- Platform definitions
- Capability specifications
- Important decisions or rules

MATERIAL:
{chunk}

For EACH item found, respond in this format:
ITEM: [category — e.g. architectural_decision, build_order_item, vision_philosophy, etc.]
CONTENT: [the specific content to file, 1-3 sentences, clean and concise]

If nothing is Codex-worthy, respond: NONE"""

                    r = requests.post("http://localhost:11434/api/generate",  # DEPRECATED-V5
                        json={"model": model, "prompt": prompt, "stream": False},  # DEPRECATED-V5
                        timeout=180)
                    r.raise_for_status()
                    analysis = r.json().get("response", "").strip()

                    if analysis and "NONE" not in analysis.upper():
                        all_analysis.append(analysis)

                if not all_analysis:
                    self.ingest_result.emit("No Codex-worthy content found.", "#5a8090")
                    return

                # Step 2: For each item across all chunks, draft + queue
                import re
                combined = "\n\n".join(all_analysis)
                items = re.findall(r"ITEM:\s*(\w+)\s*\nCONTENT:\s*(.+?)(?=\nITEM:|\Z)", combined, re.DOTALL)

                if not items and _codex_intel:
                    # Fallback — treat whole analysis as one item
                    draft = _codex_intel.generate_codex_draft(
                        {"category": "vision_philosophy", "content": combined[:500]},
                        content[:500], combined
                    )
                    if draft:
                        _codex_intel.queue_for_approval(draft)
                        self.ingest_result.emit(f"1 item queued for approval: {draft['path']}", "#00e5a0")
                    else:
                        self.ingest_result.emit("Extraction succeeded but drafting failed.", "#f0a800")
                    return

                queued = 0
                for category, item_content in items:
                    if _codex_intel:
                        draft = _codex_intel.generate_codex_draft(
                            {"category": category.strip(), "content": item_content.strip()},
                            content[:500], combined
                        )
                        if draft:
                            _codex_intel.queue_for_approval(draft)
                            queued += 1

                if queued > 0:
                    self.ingest_result.emit(f"{queued} item(s) queued for approval.", "#00e5a0")
                else:
                    self.ingest_result.emit("Extracted items but could not draft entries.", "#f0a800")

            except Exception as e:
                self.ingest_result.emit(f"Ingest error: {str(e)[:100]}", "#ff4060")

        threading.Thread(target=run, daemon=True).start()


# ── MAIN WINDOW ──────────────────────────────────────────────
class COIDesktop(QMainWindow):
    # Thread-safe signals for background threads — Qt widgets MUST only be touched from main thread
    _thread_message = pyqtSignal(str, str, str)  # sender, text, color → append_message
    _status_update = pyqtSignal(bool, bool, bool)  # ollama_ok, claude_ok, bridge_ok → _apply_status  # DEPRECATED-V5
    _start_followup = pyqtSignal(str, object)  # message, history → _do_start_followup
    _history_append = pyqtSignal(object)  # dict → self.history.append (thread-safe)
    _git_commit_ready = pyqtSignal(str, list, str)  # message, files, diff_preview → approval dialog
    _bo_draft_ready = pyqtSignal(dict)  # BO draft fields → approval dialog

    def __init__(self):
        super().__init__()
        self.history = []
        self.worker  = None
        self.config  = load_config()
        self.operating_mode = "foreground"  # BO-015: "foreground" or "background"
        self._thread_message.connect(self.append_message)
        self._status_update.connect(self._apply_status)
        self._start_followup.connect(self._do_start_followup)
        self._history_append.connect(lambda d: self.history.append(d))
        self._git_commit_ready.connect(self._on_git_commit_ready)
        self._bo_draft_ready.connect(self._on_bo_draft_ready)
        self.init_ui()
        self.check_status()
        self._warmup_foreground_model()  # BO-015: Load resident model into VRAM  # DEPRECATED-V5
        init_session_file()  # Start session log instantly

    def init_ui(self):
        self.setWindowTitle("COI — Chief Operating Intelligence")
        self.setMinimumSize(900, 650)
        self.resize(1100, 750)

        # Dark palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window,          QColor("#0d1117"))
        palette.setColor(QPalette.ColorRole.WindowText,      QColor("#d8e8f0"))
        palette.setColor(QPalette.ColorRole.Base,            QColor("#111920"))
        palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#161f28"))
        palette.setColor(QPalette.ColorRole.Text,            QColor("#d8e8f0"))
        palette.setColor(QPalette.ColorRole.Button,          QColor("#1c2a35"))
        palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#d8e8f0"))
        palette.setColor(QPalette.ColorRole.Highlight,       QColor("#00c8f0"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#07090c"))
        self.setPalette(palette)

        # Central widget — HBox wraps main content + sidebar
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QHBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Main content area (left side)
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── TOPBAR ───────────────────────────────────────────
        topbar = QFrame()
        topbar.setFixedHeight(46)
        topbar.setStyleSheet("background:#0d1117; border-bottom:1px solid #1e2d3d;")
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("COI")
        title.setStyleSheet("color:#00c8f0; font-weight:700; font-size:13px; font-family:'JetBrains Mono',monospace;")
        topbar_layout.addWidget(title)

        subtitle = QLabel("Chief Operating Intelligence")
        subtitle.setStyleSheet("color:#2a4050; font-size:11px; margin-left:8px;")
        topbar_layout.addWidget(subtitle)

        topbar_layout.addStretch()

        # Health + Report buttons
        health_btn = QPushButton("Health")
        health_btn.setFixedSize(64, 28)
        health_btn.setStyleSheet(
            "background:#1e2d3d; color:#00e5a0; border:1px solid #00e5a0; border-radius:4px; "
            "font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace;"
        )
        health_btn.clicked.connect(self.run_health_check)
        topbar_layout.addWidget(health_btn)

        report_btn = QPushButton("Report")
        report_btn.setFixedSize(64, 28)
        report_btn.setStyleSheet(
            "background:#1e2d3d; color:#f0a800; border:1px solid #f0a800; border-radius:4px; "
            "font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace; margin-left:6px;"
        )
        report_btn.clicked.connect(self.run_system_report)
        topbar_layout.addWidget(report_btn)

        dropoff_btn = QPushButton("Drop-Off")
        dropoff_btn.setFixedSize(72, 28)
        dropoff_btn.setStyleSheet(
            "background:#1e2d3d; color:#00e5a0; border:1px solid #00e5a0; border-radius:4px; "
            "font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace; margin-left:6px;"
        )
        dropoff_btn.clicked.connect(self._toggle_dropoff)
        topbar_layout.addWidget(dropoff_btn)

        cmds_btn = QPushButton("Cmds")
        cmds_btn.setFixedSize(52, 28)
        cmds_btn.setStyleSheet(
            "background:#1e2d3d; color:#00c8f0; border:1px solid #00c8f0; border-radius:4px; "
            "font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace; margin-left:6px;"
        )
        cmds_btn.clicked.connect(self._toggle_commands_panel)
        topbar_layout.addWidget(cmds_btn)

        briefing_btn = QPushButton("Briefing")
        briefing_btn.setFixedSize(72, 28)
        briefing_btn.setStyleSheet(
            "background:#1e2d3d; color:#d8e8f0; border:1px solid #5a8090; border-radius:4px; "
            "font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace; margin-left:6px;"
        )
        briefing_btn.clicked.connect(self._toggle_briefing_panel)
        topbar_layout.addWidget(briefing_btn)

        # Status indicators
        self.ollama_dot = QLabel("● OLLAMA")  # DEPRECATED-V5
        self.ollama_dot.setStyleSheet("color:#2a4050; font-size:10px; font-family:'JetBrains Mono',monospace;")  # DEPRECATED-V5
        topbar_layout.addWidget(self.ollama_dot)  # DEPRECATED-V5

        self.claude_dot = QLabel("● CLAUDE")
        self.claude_dot.setStyleSheet("color:#2a4050; font-size:10px; font-family:'JetBrains Mono',monospace; margin-left:12px;")
        topbar_layout.addWidget(self.claude_dot)

        self.bridge_dot = QLabel("● BRIDGE")
        self.bridge_dot.setStyleSheet("color:#2a4050; font-size:10px; font-family:'JetBrains Mono',monospace; margin-left:12px;")
        self.bridge_dot.setToolTip("COI Bridge — localhost:11435")
        topbar_layout.addWidget(self.bridge_dot)

        self.mode_label = QLabel("FG")
        self.mode_label.setStyleSheet("color:#00e5a0; font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace; margin-left:12px;")
        self.mode_label.setToolTip(f"Foreground Mode — {FOREGROUND_MODEL} resident")  # DEPRECATED-V5
        topbar_layout.addWidget(self.mode_label)

        self.model_label = QLabel("—")
        self.model_label.setStyleSheet("color:#2a4050; font-size:10px; font-family:'JetBrains Mono',monospace; margin-left:16px;")
        topbar_layout.addWidget(self.model_label)

        main_layout.addWidget(topbar)

        # ── CHAT AREA ────────────────────────────────────────
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet("""
            QTextEdit {
                background: #07090c;
                color: #d8e8f0;
                border: none;
                padding: 16px;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
            }
            QScrollBar:vertical {
                background: #0d1117;
                width: 6px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #1e2d3d;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.chat, stretch=1)

        # ── INPUT BAR ────────────────────────────────────────
        input_frame = QFrame()
        input_frame.setFixedHeight(60)
        input_frame.setStyleSheet("background:#0d1117; border-top:1px solid #1e2d3d;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 10, 16, 10)
        input_layout.setSpacing(10)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Direct COI...")
        self.input.setStyleSheet("""
            QLineEdit {
                background: #111920;
                color: #d8e8f0;
                border: 1px solid #1e2d3d;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit:focus {
                border-color: #00c8f0;
            }
        """)
        self.input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input, stretch=1)

        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedSize(72, 38)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #00c8f0;
                color: #07090c;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover  { background: #00b8e0; }
            QPushButton:pressed{ background: #0098c0; }
            QPushButton:disabled{ background: #1e2d3d; color: #2a4050; }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        main_layout.addWidget(input_frame)

        # ── COMMANDS PANEL (LEFT SIDEBAR) ─────────────────────
        # Clickable buttons that fire commands directly — zero tokens
        self.commands_panel = QFrame()
        self.commands_panel.setFixedWidth(160)
        self.commands_panel.setVisible(False)  # Hidden by default, toggle via Cmds button
        self.commands_panel.setStyleSheet(
            "background:#0b1015; border-right:1px solid #1e2d3d;"
        )
        cmd_layout = QVBoxLayout(self.commands_panel)
        cmd_layout.setContentsMargins(8, 12, 8, 12)
        cmd_layout.setSpacing(4)

        cmd_header = QLabel("COMMANDS")
        cmd_header.setStyleSheet(
            "color:#00c8f0; font-size:10px; font-weight:700; "
            "font-family:'JetBrains Mono',monospace; padding-bottom:4px;"
        )
        cmd_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cmd_layout.addWidget(cmd_header)

        cmd_sub = QLabel("zero tokens · instant")
        cmd_sub.setStyleSheet(
            "color:#2a4050; font-size:9px; font-family:'JetBrains Mono',monospace; padding-bottom:8px;"
        )
        cmd_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cmd_layout.addWidget(cmd_sub)

        # Command button style
        cmd_btn_style = """
            QPushButton {
                background: #111920;
                color: #00e5a0;
                border: 1px solid #1e2d3d;
                border-radius: 4px;
                padding: 6px 4px;
                font-size: 10px;
                font-weight: 700;
                font-family: 'JetBrains Mono', monospace;
                text-align: left;
            }
            QPushButton:hover {
                background: #1e2d3d;
                border-color: #00e5a0;
            }
            QPushButton:pressed {
                background: #00e5a0;
                color: #07090c;
            }
        """

        commands = [
            ("Build Order",    "build order"),
            ("Health Check",   "health check"),
            ("System Report",  "system report"),
            ("Last Session",   "last session"),
            ("Open Loops",     "open loops"),
            ("Show Memory",    "show memory"),
            ("What Time",      "what time"),
            ("What Model",     "what model"),
            ("─────────",      None),  # separator
            ("Git Status",     "git status"),
            ("Git Diff",       "git diff"),
            ("Git Commit",     "commit changes"),
            ("Git Push",       "push changes"),
            ("─────────",      None),  # separator
            ("Index Build",    "index COI/L1-Routing/MASTER-BUILD-ORDER.md"),
            ("Index Session",  "index COI/L4-Working/sessions/2026-03-21-12-14.md"),
            ("─────────",      None),  # separator
            ("Chunk File",     "chunk COI/L4-Working/sessions/2026-03-21-12-14.md"),
            ("Query Chunks",   "query chunks"),
            ("─────────",      None),  # separator
            ("Draft BO",       "draft build order"),
        ]

        for label, command in commands:
            if command is None:
                # Separator
                sep = QLabel(label)
                sep.setStyleSheet("color:#1e2d3d; font-size:9px; font-family:'JetBrains Mono',monospace; padding:2px 0;")
                sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cmd_layout.addWidget(sep)
                continue
            btn = QPushButton(f"  {label}")
            btn.setFixedHeight(30)
            btn.setStyleSheet(cmd_btn_style)
            btn.clicked.connect(lambda checked, cmd=command: self._fire_command(cmd))
            cmd_layout.addWidget(btn)

        cmd_layout.addStretch()
        outer_layout.addWidget(self.commands_panel)

        # ── DROP-OFF PANEL (LEFT SIDEBAR) ────────────────────
        self.dropoff_panel = DropOffPanel(parent=central)
        self.dropoff_panel.inject_summary.connect(self._on_dropoff_inject)
        outer_layout.addWidget(self.dropoff_panel)

        # Add main content to outer layout
        outer_layout.addWidget(main_container, stretch=1)

        # ── TOOLS PANEL (RIGHT SIDEBAR) ───────────────────────
        self.token_tracker = TokenTracker()
        self.tools_panel = COIToolsPanel(
            main_window=self,
            token_tracker=self.token_tracker,
            parent=central
        )
        self.token_tracker.spike_detected.connect(self.tools_panel.on_spike_detected)
        outer_layout.addWidget(self.tools_panel)

        # ── RETURN BRIEFING PANEL (RIGHT SIDE) ────────────────
        self.briefing_panel = ReturnBriefingPanel(parent=central)
        self.briefing_panel.review_requested.connect(self._on_briefing_review)
        self.briefing_panel.error_requested.connect(self._on_briefing_error)
        outer_layout.addWidget(self.briefing_panel)

        # ── DROP-OFF WORKER ───────────────────────────────────
        self._chat_active = False
        self.dropoff_worker = DropOffWorker(
            chat_active_flag=lambda: self._chat_active,
            foreground_model=FOREGROUND_MODEL,  # DEPRECATED-V5
            parent=self
        )
        self.dropoff_worker.item_started.connect(
            lambda item_id: self.dropoff_panel.update_item_status(item_id, "processing"))
        self.dropoff_worker.item_completed.connect(
            lambda item_id, summary: self.dropoff_panel.update_item_status(item_id, "done"))
        self.dropoff_worker.item_failed.connect(
            lambda item_id, err: self.dropoff_panel.update_item_status(item_id, "failed"))
        self.dropoff_worker.start()

        # ── STARTUP CONTEXT + ORIENTATION ─────────────────────
        # Load context in background, hold greeting until context is ready
        self._orientation_done = False
        self._load_startup_context()

        # ── AUTO-SHOW RETURN BRIEFING ─────────────────────────
        # Show briefing panel on startup if there are pending approvals or failures
        # Delayed to let orientation render first
        QTimer.singleShot(2000, self._auto_show_briefing)

    # ── STATUS CHECK ─────────────────────────────────────────
    def _apply_status(self, ollama_ok, claude_ok, bridge_ok):  # DEPRECATED-V5
        """Apply status dot updates — MUST run on main thread (called via signal)"""
        if ollama_ok:  # DEPRECATED-V5
            self.ollama_dot.setStyleSheet("color:#00e5a0; font-size:10px; font-family:'JetBrains Mono',monospace;")  # DEPRECATED-V5
            self.ollama_dot.setText("● OLLAMA")  # DEPRECATED-V5
        else:
            self.ollama_dot.setStyleSheet("color:#ff4060; font-size:10px; font-family:'JetBrains Mono',monospace;")  # DEPRECATED-V5

        if claude_ok:
            self.claude_dot.setStyleSheet("color:#00e5a0; font-size:10px; font-family:'JetBrains Mono',monospace; margin-left:12px;")
            self.claude_dot.setText("● CLAUDE")
        else:
            self.claude_dot.setStyleSheet("color:#ff4060; font-size:10px; font-family:'JetBrains Mono',monospace; margin-left:12px;")

        if bridge_ok:
            self.bridge_dot.setStyleSheet("color:#00e5a0; font-size:10px; font-family:'JetBrains Mono',monospace; margin-left:12px;")
            self.bridge_dot.setText("● BRIDGE")
        else:
            self.bridge_dot.setStyleSheet("color:#ff4060; font-size:10px; font-family:'JetBrains Mono',monospace; margin-left:12px;")

    def check_status(self):
        def run():
            ollama_ok = False  # DEPRECATED-V5
            bridge_ok = False
            try:
                r = requests.get("http://localhost:11434", timeout=2)  # DEPRECATED-V5
                ollama_ok = True  # DEPRECATED-V5
            except:
                pass
            try:
                r = requests.get("http://localhost:11435/health", timeout=2)
                bridge_ok = r.status_code == 200
            except:
                pass
            claude_ok = bool(self.config.get("anthropic_api_key"))
            self._status_update.emit(ollama_ok, claude_ok, bridge_ok)

        threading.Thread(target=run, daemon=True).start()

    # ── FOREGROUND MODEL WARMUP ──────────────────────────────
    def _warmup_foreground_model(self):  # DEPRECATED-V5
        """BO-015: Load foreground model into VRAM and keep it resident.
        Unloads other models first to prevent RAM pile-up."""
        def run():
            try:
                # Unload any other models first — prevent RAM pile-up
                try:
                    ps = requests.get("http://localhost:11434/api/ps", timeout=5).json()  # DEPRECATED-V5
                    for m in ps.get("models", []):
                        name = m.get("name", "")
                        if name and name != FOREGROUND_MODEL:  # DEPRECATED-V5
                            requests.post("http://localhost:11434/api/generate", json={  # DEPRECATED-V5
                                "model": name, "prompt": "", "keep_alive": 0  # DEPRECATED-V5
                            }, timeout=10)
                except:
                    pass
                # Load foreground model and pin it
                requests.post("http://localhost:11434/api/generate", json={  # DEPRECATED-V5
                    "model": FOREGROUND_MODEL,  # DEPRECATED-V5
                    "prompt": "",
                    "keep_alive": -1  # Stay loaded indefinitely
                }, timeout=30)
                self._thread_message.emit("COI", f"Foreground model loaded: {FOREGROUND_MODEL}", "#00e5a0")  # DEPRECATED-V5
            except Exception as e:
                self._thread_message.emit("COI", f"Model warmup failed: {str(e)[:100]}", "#f0a800")
        threading.Thread(target=run, daemon=True).start()

    # ── DROP-OFF PANEL ────────────────────────────────────────
    def _toggle_dropoff(self):
        self.dropoff_panel.setVisible(not self.dropoff_panel.isVisible())

    def _toggle_commands_panel(self):
        self.commands_panel.setVisible(not self.commands_panel.isVisible())

    def _toggle_briefing_panel(self):
        if self.briefing_panel.isVisible():
            self.briefing_panel.setVisible(False)
        else:
            self.briefing_panel.refresh()
            self.briefing_panel.setVisible(True)

    def _load_startup_context(self):
        """Load session context in background thread. Greeting is held until
        context is ready — no generic fallback races ahead."""
        def _gather():
            context_parts = []

            # 1. Last session exchanges
            try:
                sessions_dir = ICM_ROOT / "COI/L4-Working/sessions"
                if sessions_dir.exists():
                    session_files = sorted(
                        [f for f in sessions_dir.glob("*.md") if not f.name.startswith("README")],
                        key=lambda f: f.stat().st_mtime, reverse=True
                    )
                    for sf in session_files[1:2]:
                        content = sf.read_text(encoding="utf-8")
                        lines = content.splitlines()
                        exchanges = [l for l in lines if l.startswith("**DAVE") or l.startswith("**COI") or (l.strip() and not l.startswith("#"))]
                        last_5 = exchanges[-10:] if len(exchanges) > 10 else exchanges
                        if last_5:
                            context_parts.append("LAST SESSION:\n" + "\n".join(last_5))
            except Exception:
                pass

            # 2. Queued BO items
            try:
                bo_path = ICM_ROOT / "COI/L1-Routing/MASTER-BUILD-ORDER.md"
                if bo_path.exists():
                    import re
                    bo_content = bo_path.read_text(encoding="utf-8")
                    queued = re.findall(r"### (BO-\d+ — [^\n]+)(?:(?!###).)*?\*\*Status:\*\* Queued", bo_content, re.DOTALL)
                    if queued:
                        context_parts.append("QUEUED BUILD ITEMS:\n" + "\n".join(f"- {q}" for q in queued[:8]))
            except Exception:
                pass

            # 3. Pending approvals count
            pending_count = 0
            try:
                approval_dir = ICM_ROOT / "pipeline/05-dave-approval/output"
                if approval_dir.exists():
                    pending = [f for f in approval_dir.iterdir() if f.is_file() and f.suffix == ".md"]
                    pending_count = len(pending)
                    if pending_count:
                        context_parts.append(f"PENDING APPROVALS: {pending_count} items waiting for Dave's review")
            except Exception:
                pass

            global _STARTUP_CONTEXT
            startup_ctx = "\n\n".join(context_parts)
            _STARTUP_CONTEXT = startup_ctx

            # Build deterministic greeting from real context — never generic
            if not context_parts:
                greeting = "I couldn't load our last session. What are we working on today?"
                QTimer.singleShot(0, lambda g=greeting: self._set_orientation(g))
                return

            fallback_parts = []
            for part in context_parts:
                if part.startswith("LAST SESSION:"):
                    session_lines = part.split("\n")[1:]
                    for sl in reversed(session_lines):
                        clean = sl.strip().strip("*").strip()
                        if clean and len(clean) > 15 and not clean.startswith("["):
                            topic = clean[:80].rstrip(".")
                            fallback_parts.append(f"Last session we were working on: {topic}")
                            break
                elif part.startswith("QUEUED BUILD ITEMS:"):
                    count = part.count("\n- ")
                    fallback_parts.append(f"You have {count} build order items queued")
                elif part.startswith("PENDING APPROVALS:"):
                    fallback_parts.append(part.replace("PENDING APPROVALS: ", ""))

            deterministic = ". ".join(fallback_parts) + ". What do you want to tackle?"

            # Try LLM greeting with personality context
            try:
                personality = (
                    "You are COI — a young Japanese woman in her mid-twenties. "
                    "You are Chief Operating Intelligence, built by Dave Sheridan. "
                    "You are warm, direct, and confident. Your humor is dry and well-timed. "
                    "You talk like a real person — not an assistant. Dave is the Father."
                )
                r = requests.post("http://localhost:11434/api/generate", json={  # DEPRECATED-V5
                    "model": FOREGROUND_MODEL,  # DEPRECATED-V5
                    "prompt": (
                        f"{personality}\n\n"
                        "Generate a brief, natural greeting for Dave based on this context. "
                        "2-3 sentences max. Be warm and specific — mention what you were "
                        "last working on and anything pending. Do NOT list items. "
                        "Do NOT use bullet points. Just talk naturally, in character.\n\n"
                        f"{startup_ctx}"
                    ),
                    "stream": False,
                    "options": {"num_ctx": 2048, "temperature": 0.7}
                }, timeout=30)
                if r.status_code == 200:
                    llm_greeting = r.json().get("response", "").strip()
                    if llm_greeting and len(llm_greeting) > 10:
                        QTimer.singleShot(0, lambda g=llm_greeting: self._set_orientation(g))
                        return
            except Exception:
                pass

            # LLM unavailable — deterministic greeting from real data
            QTimer.singleShot(0, lambda g=deterministic: self._set_orientation(g))

        threading.Thread(target=_gather, daemon=True).start()

    def _set_orientation(self, message):
        """Show the orientation greeting. Called once context is ready.
        NOT added to conversation history — prevents the model from
        learning a generic tone from the greeting."""
        self._orientation_done = True
        self.append_message("COI", message, "#00c8f0")
        # Deliberately not added to self.history — the model's first
        # assistant turn should come from the personality prompt, not
        # from a greeting that may not match the persona perfectly.
        write_to_session("COI", f"[ORIENTATION] {message}")

    def _auto_show_briefing(self):
        """Auto-show briefing panel on startup if there are pending items."""
        if self.briefing_panel.show_if_needed():
            self.append_message("COI",
                "You have items waiting for review. Briefing panel is open.",
                "#f0a800")

    def _on_briefing_review(self, item_data):
        """Open an approval item for review from the briefing panel."""
        filepath = item_data.get("path", "")
        if not filepath or not Path(filepath).exists():
            self.append_message("COI", "Approval file not found.", "#ff4060")
            return

        try:
            content = Path(filepath).read_text(encoding="utf-8")
        except Exception as e:
            self.append_message("COI", f"Could not read approval file: {e}", "#ff4060")
            return

        # Count all pending items for bulk action
        approval_dir = Path(filepath).parent
        all_pending = [f for f in approval_dir.iterdir() if f.is_file() and f.suffix == ".md"]
        pending_count = len(all_pending)

        # Show review dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"COI — Review: {item_data.get('display', 'Approval Item')}")
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet("background:#0d1117; color:#d8e8f0;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel(f"APPROVAL REVIEW — {item_data.get('category', 'Unknown')}")
        header.setStyleSheet("color:#f0a800; font-size:13px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(header)

        if item_data.get("target"):
            target = QLabel(f"Target: {item_data['target']}")
            target.setStyleSheet("color:#00e5a0; font-size:11px; font-family:'JetBrains Mono',monospace;")
            layout.addWidget(target)

        content_view = QTextEdit()
        content_view.setReadOnly(True)
        content_view.setPlainText(content)
        content_view.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; "
            "font-size:11px; font-family:'JetBrains Mono',monospace;"
        )
        layout.addWidget(content_view, stretch=1)

        btn_row = QHBoxLayout()

        # Bulk actions (left side)
        if pending_count > 1:
            approve_all_btn = QPushButton(f"Approve All ({pending_count})")
            approve_all_btn.setFixedHeight(36)
            approve_all_btn.setStyleSheet(
                "background:#1e2d3d; color:#00e5a0; border:1px solid #00e5a0; "
                "border-radius:6px; font-weight:700; font-size:11px; padding:0 12px;"
            )
            approve_all_btn.clicked.connect(lambda: self._bulk_decide(approval_dir, "approved", dialog))
            btn_row.addWidget(approve_all_btn)

            reject_all_btn = QPushButton(f"Reject All ({pending_count})")
            reject_all_btn.setFixedHeight(36)
            reject_all_btn.setStyleSheet(
                "background:#1e2d3d; color:#ff4060; border:1px solid #ff4060; "
                "border-radius:6px; font-weight:700; font-size:11px; padding:0 12px;"
            )
            reject_all_btn.clicked.connect(lambda: self._bulk_decide(approval_dir, "rejected", dialog))
            btn_row.addWidget(reject_all_btn)

        btn_row.addStretch()

        # Single item actions (right side)
        reject_btn = QPushButton("Reject")
        reject_btn.setFixedSize(100, 36)
        reject_btn.setStyleSheet("background:#ff4060; color:#fff; border:none; border-radius:6px; font-weight:700; font-size:12px;")
        reject_btn.clicked.connect(lambda: self._decide_approval(filepath, "rejected", dialog))
        btn_row.addWidget(reject_btn)

        approve_btn = QPushButton("Approve")
        approve_btn.setFixedSize(100, 36)
        approve_btn.setStyleSheet("background:#00e5a0; color:#07090c; border:none; border-radius:6px; font-weight:700; font-size:12px;")
        approve_btn.clicked.connect(lambda: self._decide_approval(filepath, "approved", dialog))
        btn_row.addWidget(approve_btn)

        layout.addLayout(btn_row)
        dialog.exec()

    def _decide_approval(self, filepath, decision, dialog):
        """Move a single approval file to approved/rejected subfolder."""
        src = Path(filepath)
        dest_dir = src.parent / ("approved" if decision == "approved" else "rejected")
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            src.rename(dest_dir / src.name)
            self.append_message("COI", f"Item {decision}: {src.name}",
                                "#00e5a0" if decision == "approved" else "#ff4060")
            dialog.accept()
            self.briefing_panel.refresh()
        except Exception as e:
            self.append_message("COI", f"Failed to move file: {e}", "#ff4060")

    def _bulk_decide(self, approval_dir, decision, dialog):
        """Move ALL pending approval files at once. One summary message."""
        pending = [f for f in approval_dir.iterdir() if f.is_file() and f.suffix == ".md"]
        if not pending:
            return

        dest_dir = approval_dir / ("approved" if decision == "approved" else "rejected")
        dest_dir.mkdir(parents=True, exist_ok=True)

        moved = 0
        failed = 0
        for f in pending:
            try:
                f.rename(dest_dir / f.name)
                moved += 1
            except Exception:
                failed += 1

        # One summary message — not one per item
        color = "#00e5a0" if decision == "approved" else "#ff4060"
        msg = f"{moved} items {decision}."
        if failed:
            msg += f" {failed} failed to move."
        self.append_message("COI", msg, color)
        write_to_session("COI", f"[BULK {decision.upper()}] {moved} items")

        dialog.accept()
        self.briefing_panel.refresh()

    def _on_briefing_error(self, item_data):
        """Show error details from execution log."""
        dialog = QDialog(self)
        dialog.setWindowTitle("COI — Error Details")
        dialog.setMinimumSize(500, 300)
        dialog.setStyleSheet("background:#0d1117; color:#d8e8f0;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("PIPELINE ERROR")
        header.setStyleSheet("color:#ff4060; font-size:13px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(header)

        details = []
        if item_data.get("timestamp"):
            details.append(f"Time: {item_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        if item_data.get("command"):
            details.append(f"Command: {item_data['command']}")
        if item_data.get("type"):
            details.append(f"Type: {item_data['type']}")
        details.append(f"Status: {item_data.get('status', 'failed')}")

        content_view = QTextEdit()
        content_view.setReadOnly(True)
        content_view.setPlainText("\n".join(details))
        content_view.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; "
            "font-size:11px; font-family:'JetBrains Mono',monospace;"
        )
        layout.addWidget(content_view, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.setFixedSize(80, 32)
        close_btn.setStyleSheet("background:#1e2d3d; color:#d8e8f0; border:1px solid #2a4050; border-radius:6px; font-weight:700; font-size:12px;")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        dialog.exec()

    def _fire_command(self, command_text):
        """Fire a command from the panel button — routes directly, skips LLM."""
        self.append_message("DAVE", command_text, "#f0a800")
        self.history.append({"role": "user", "content": command_text})
        write_to_session("DAVE", command_text)
        self._route_command(command_text.lower().strip(), from_button=True)

    def _on_dropoff_inject(self, item_id, content_text):
        """Inject drop-off content verbatim into chat context (SPEC-05)."""
        self.history.append({"role": "user", "content": content_text})

        # SPEC-05: Verification echo — confirm content received intact
        lines = content_text.strip().split("\n")
        content_lines = [l for l in lines if l.strip()
                         and not l.startswith("[DROP-OFF-ORIGIN")
                         and not l.startswith("[END-DROP-OFF-ORIGIN")
                         and not l.startswith("Source:")
                         and not l.startswith("Received:")
                         and not l.startswith("Type:")
                         and l.strip() != "---"]
        line_count = len(content_lines)
        char_count = sum(len(l) for l in content_lines)

        echo_msg = (
            f"[Drop-off received: {item_id}] "
            f"Content loaded verbatim — {line_count} lines, {char_count:,} chars. "
            f"No summarization applied."
        )
        self.append_message("COI", echo_msg, "#00e5a0")

    # ── HEALTH CHECK ──────────────────────────────────────────
    # ── COMMAND ROUTER — TOOLS BEFORE LLM ─────────────────
    # Zero tokens. Instant. Deterministic. No context pollution.

    def _route_command(self, text_lower, from_button=False):
        """Check if user input matches a known command. Returns True if handled.
        Only fires from command panel buttons (from_button=True).
        Chat input always goes to the LLM."""

        # Only command panel buttons trigger routing — chat never does
        if not from_button:
            return False

        # ── BUILD ORDER ──────────────────────────────────────
        if any(k in text_lower for k in ["build order", "list build", "show build", "build list"]):
            self._cmd_build_order()
            return True

        # ── HEALTH / STATUS CHECK ────────────────────────────
        if any(k in text_lower for k in ["health check", "status check"]):
            self.run_health_check()
            return True

        # ── SYSTEM REPORT ────────────────────────────────────
        if any(k in text_lower for k in ["system report", "build report"]):
            self.run_system_report()
            return True

        # ── SESSIONS / LAST SESSION ──────────────────────────
        if any(k in text_lower for k in ["last session", "previous session", "what did we do",
                                          "session briefing", "session brief"]):
            self._cmd_session_briefing()
            return True

        # ── OPEN LOOPS ───────────────────────────────────────
        if any(k in text_lower for k in ["open loops", "open items", "what's pending",
                                          "what is pending"]):
            self._cmd_open_loops()
            return True

        # ── WHAT TIME / DATE ─────────────────────────────────
        if any(k in text_lower for k in ["what time", "what day", "what date", "what's the time",
                                          "what is the time", "what is the date"]):
            now = datetime.now()
            self.append_message("COI",
                f"It's {now.strftime('%A, %B %d, %Y')} at {now.strftime('%I:%M %p')}.",
                "#00c8f0")
            self.history.append({"role": "assistant",
                "content": f"It's {now.strftime('%A, %B %d, %Y at %I:%M %p')}."})
            write_to_session("COI", f"It's {now.strftime('%A, %B %d, %Y at %I:%M %p')}.")
            return True

        # ── WHAT MODEL / WHICH MODEL ─────────────────────────
        if any(k in text_lower for k in ["what model", "which model", "what llm",
                                          "which llm", "loaded model", "current model"]):
            self.append_message("COI",
                f"Foreground chat is running on {FOREGROUND_MODEL}. "  # DEPRECATED-V5
                f"Code tasks route to {MODELS.get('code', 'unknown')}.",  # DEPRECATED-V5
                "#00c8f0")
            self.history.append({"role": "assistant",
                "content": f"Running {FOREGROUND_MODEL} for chat, {MODELS.get('code', 'unknown')} for code."})  # DEPRECATED-V5
            return True

        # ── SHOW MEMORY FILES ────────────────────────────────
        if any(k in text_lower for k in ["show memory", "list memory", "memory files",
                                          "what's in memory", "what is in memory"]):
            self._cmd_memory_files()
            return True

        # ── FILE INDEX (zero-token) ──────────────────────────
        if text_lower.startswith("index ") or text_lower.startswith("file index "):
            # Extract path from "index COI/L1-Routing/MASTER-BUILD-ORDER.md"
            path = text_lower.replace("file index ", "").replace("index ", "").strip()
            self._cmd_file_index(path)
            return True

        # ── FILE SECTION (zero-token) ───────────────────────
        if text_lower.startswith("section "):
            # Format: "section FILENAME : SECTION_NAME"
            parts = text_lower.replace("section ", "", 1).split(":", 1)
            if len(parts) == 2:
                self._cmd_file_section(parts[0].strip(), parts[1].strip())
            else:
                self.append_message("COI", "Usage: section FILEPATH : SECTION NAME", "#ff4060")
            return True

        # ── FILE SEARCH (zero-token) ────────────────────────
        if text_lower.startswith("search "):
            # Format: "search FILENAME : QUERY"
            parts = text_lower.replace("search ", "", 1).split(":", 1)
            if len(parts) == 2:
                self._cmd_file_search(parts[0].strip(), parts[1].strip())
            else:
                self.append_message("COI", "Usage: search FILEPATH : QUERY", "#ff4060")
            return True

        # ── DRAFT BUILD ORDER (SPEC-02) ────────────────────
        if any(k in text_lower for k in ["draft build order", "draft bo", "new build order"]):
            self._cmd_draft_bo()
            return True

        # ── CHUNK FILE (SPEC-01) ────────────────────────────
        if text_lower.startswith("chunk "):
            path = text_lower.replace("chunk ", "", 1).strip()
            self._cmd_chunk_file(path)
            return True

        # ── QUERY CHUNKS (SPEC-01) ─────────────────────────
        if text_lower.startswith("query chunks") or text_lower.startswith("query session"):
            query = text_lower.replace("query chunks", "").replace("query session", "").strip()
            if query:
                self._cmd_query_chunks(query)
            else:
                self._cmd_query_chunks_dialog()
            return True

        # ── GIT STATUS (zero-token) ──────────────────────────
        if any(k in text_lower for k in ["git status", "show changes", "what changed",
                                          "what's changed"]):
            self._cmd_git_status()
            return True

        # ── GIT DIFF (zero-token) ───────────────────────────
        if any(k in text_lower for k in ["git diff", "show diff"]):
            self._cmd_git_diff()
            return True

        # ── GIT COMMIT (approval flow) ──────────────────────
        if any(k in text_lower for k in ["commit changes", "commit all", "git commit",
                                          "save changes"]):
            self._cmd_git_commit()
            return True

        # ── GIT PUSH (approval flow) ────────────────────────
        if any(k in text_lower for k in ["push changes", "git push", "push to github"]):
            self._cmd_git_push()
            return True

        return False

    # ── GIT COMMAND HANDLERS (BO-026) ────────────────────────

    # ── SAFE FILE READING HANDLERS ─────────────────────────

    def _cmd_file_index(self, path):
        """Show table of contents for a file — zero tokens."""
        if not _coi_tools or not hasattr(_coi_tools, 'coi_file_index'):
            self.append_message("COI", "File tools not loaded.", "#ff4060")
            return
        index, msg = _coi_tools.coi_file_index(path)
        if index is None:
            self.append_message("COI", f"Could not index: {msg}", "#ff4060")
            return

        lines = [f"File: {index['file']}",
                 f"Size: {index['total_chars']:,} chars, {index['total_lines']} lines",
                 f"Sections ({len(index['sections'])}):\n"]
        for s in index["sections"]:
            indent = "  " * (s["level"] - 1) if s["level"] > 0 else ""
            lines.append(f"{indent}[L{s['line']}] {s['heading']}  ({s['chars']:,} chars)")

        result = "\n".join(lines)
        self.append_message("COI", result, "#00c8f0")
        self.history.append({"role": "assistant", "content": "[file index displayed]"})
        write_to_session("COI", result)

    def _cmd_file_section(self, path, section_name):
        """Load one section from a file — zero tokens, context-safe."""
        if not _coi_tools or not hasattr(_coi_tools, 'coi_file_section'):
            self.append_message("COI", "File tools not loaded.", "#ff4060")
            return
        content, msg = _coi_tools.coi_file_section(path, section_name)
        if content is None:
            self.append_message("COI", f"Could not load section: {msg}", "#ff4060")
            return

        self.append_message("COI", content, "#00c8f0")
        self.history.append({"role": "assistant", "content": f"[section '{section_name}' displayed]"})
        write_to_session("COI", f"[section '{section_name}' from {path} displayed — tool response]")

    def _cmd_file_search(self, path, query):
        """Search a file for a keyword — zero tokens."""
        if not _coi_tools or not hasattr(_coi_tools, 'coi_file_search'):
            self.append_message("COI", "File tools not loaded.", "#ff4060")
            return
        results, msg = _coi_tools.coi_file_search(path, query)
        if results is None:
            self.append_message("COI", f"Search error: {msg}", "#ff4060")
            return

        if results["total_matches"] == 0:
            self.append_message("COI", f"No matches for '{query}' in {path}", "#f0a800")
            return

        lines = [f"Found {results['total_matches']} match(es) for '{query}' in {path}:\n"]
        for r in results["results"]:
            lines.append(r["context"])
            lines.append("")

        result = "\n".join(lines)
        self.append_message("COI", result, "#00c8f0")
        self.history.append({"role": "assistant", "content": f"[file search: {results['total_matches']} matches]"})
        write_to_session("COI", f"[file search for '{query}' in {path} — {results['total_matches']} matches]")

    # ── CHUNKED FILE ACCESS HANDLERS (SPEC-01) ─────────────

    def _cmd_chunk_file(self, path):
        """Chunk a large file and generate index with LLM summaries.
        Runs in background thread — LLM calls can be slow."""
        if not _coi_tools or not hasattr(_coi_tools, 'coi_chunk_file'):
            self.append_message("COI", "Chunk tools not loaded.", "#ff4060")
            return

        self.append_message("COI", f"Chunking file: {path}\nThis may take a moment (generating topic summaries)...", "#f0a800")

        def _do_chunk():
            index_path, msg = _coi_tools.coi_chunk_file(path)
            if index_path:
                self._last_chunk_index = index_path
                QTimer.singleShot(0, lambda: self.append_message("COI",
                    f"Chunking complete.\nIndex: {index_path}\n{msg}",
                    "#00c8f0"))
            else:
                QTimer.singleShot(0, lambda: self.append_message("COI",
                    f"Chunking failed: {msg}", "#ff4060"))

        threading.Thread(target=_do_chunk, daemon=True).start()

    def _cmd_query_chunks(self, query):
        """Query the most recent chunk index."""
        if not _coi_tools or not hasattr(_coi_tools, 'coi_read_chunk'):
            self.append_message("COI", "Chunk tools not loaded.", "#ff4060")
            return

        # Use last chunked index if available, otherwise auto-detect
        index_path = getattr(self, '_last_chunk_index', None)

        if index_path:
            results, msg = _coi_tools.coi_read_chunk(index_path, query)
        else:
            results, msg = _coi_tools.coi_query_session(query)

        if results is None:
            self.append_message("COI", f"Query error: {msg}", "#ff4060")
            return

        if not results:
            self.append_message("COI", f"No chunks matched: {query}", "#f0a800")
            return

        lines = [f"Query: \"{query}\" — {msg}\n"]
        for r in results:
            lines.append(f"━━ Chunk {r['chunk']} (score: {r['score']}) ━━")
            lines.append(f"Summary: {r['summary']}")
            lines.append(f"{'─' * 40}")
            # Truncate display to keep chat manageable
            content = r.get("content", "")
            if len(content) > 2000:
                content = content[:2000] + f"\n[... truncated — {len(r.get('content', ''))} chars total]"
            lines.append(content)
            lines.append("")

        result = "\n".join(lines)
        self.append_message("COI", result, "#00c8f0")
        self.history.append({"role": "assistant", "content": f"[chunk query: {len(results)} results for '{query}']"})
        write_to_session("COI", f"[chunk query for '{query}' — {len(results)} results returned]")

    def _cmd_query_chunks_dialog(self):
        """Show a simple input dialog for query when no query text provided."""
        from PyQt6.QtWidgets import QInputDialog
        query, ok = QInputDialog.getText(self, "Query Chunks", "Search query:")
        if ok and query.strip():
            self._cmd_query_chunks(query.strip())

    # ── BUILD ORDER DRAFTING (SPEC-02) ──────────────────────

    def _cmd_draft_bo(self):
        """Draft a build order item from recent conversation context.
        Uses LLM to extract the buildable idea, then shows approval dialog."""
        if not _coi_tools or not hasattr(_coi_tools, 'coi_draft_bo_from_context'):
            self.append_message("COI", "BO drafting tools not loaded.", "#ff4060")
            return

        if len(self.history) < 2:
            self.append_message("COI", "Not enough conversation context to draft from. "
                                "Talk about what you want to build first.", "#f0a800")
            return

        self.append_message("COI", "Drafting build order item from our conversation...", "#f0a800")

        def _do_draft():
            draft = _coi_tools.coi_draft_bo_from_context(self.history)
            if draft:
                bo_id = _coi_tools.coi_get_next_bo_id()
                draft["bo_id"] = bo_id
                self._bo_draft_ready.emit(draft)
            else:
                QTimer.singleShot(0, lambda: self.append_message("COI",
                    "Couldn't extract a clear build item from the conversation. "
                    "Try describing what you want to build more specifically.",
                    "#ff4060"))

        threading.Thread(target=_do_draft, daemon=True).start()

    def _on_bo_draft_ready(self, draft):
        """Show BO draft approval dialog on main thread."""
        dialog = QDialog(self)
        dialog.setWindowTitle("COI — Build Order Draft")
        dialog.setMinimumSize(650, 600)
        dialog.setStyleSheet("background:#0d1117; color:#d8e8f0;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        label_style = "color:#00e5a0; font-size:11px; font-weight:700; font-family:'JetBrains Mono',monospace;"
        input_style = ("background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; "
                       "padding:6px; font-size:12px; font-family:'JetBrains Mono',monospace;")

        # Header
        bo_num = f"BO-{draft['bo_id']:03d}"
        header = QLabel(f"BUILD ORDER DRAFT — {bo_num}")
        header.setStyleSheet("color:#f0a800; font-size:14px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(header)

        # Title
        layout.addWidget(QLabel("Title:"))
        layout.itemAt(layout.count() - 1).widget().setStyleSheet(label_style)
        title_edit = QLineEdit()
        title_edit.setText(draft.get("title", ""))
        title_edit.setStyleSheet(input_style)
        layout.addWidget(title_edit)

        # Priority + Stage row
        row = QHBoxLayout()

        row.addWidget(QLabel("Priority:"))
        row.itemAt(row.count() - 1).widget().setStyleSheet(label_style)
        from PyQt6.QtWidgets import QComboBox
        priority_combo = QComboBox()
        priority_combo.addItems(["High", "Medium", "Low"])
        priority_combo.setCurrentText(draft.get("priority", "Medium"))
        priority_combo.setStyleSheet(input_style + "min-width:100px;")
        row.addWidget(priority_combo)

        row.addSpacing(16)

        row.addWidget(QLabel("Stage:"))
        row.itemAt(row.count() - 1).widget().setStyleSheet(label_style)
        stage_combo = QComboBox()
        stage_combo.addItems(["A", "B", "C", "D"])
        stage_combo.setCurrentText(draft.get("target_stage", "B"))
        stage_combo.setStyleSheet(input_style + "min-width:60px;")
        row.addWidget(stage_combo)

        row.addStretch()
        layout.addLayout(row)

        # Activation Rule
        layout.addWidget(QLabel("Activation Rule:"))
        layout.itemAt(layout.count() - 1).widget().setStyleSheet(label_style)
        activation_edit = QLineEdit()
        activation_edit.setText(draft.get("activation_rule", ""))
        activation_edit.setStyleSheet(input_style)
        layout.addWidget(activation_edit)

        # What it does
        layout.addWidget(QLabel("What it does:"))
        layout.itemAt(layout.count() - 1).widget().setStyleSheet(label_style)
        what_does_edit = QTextEdit()
        what_does_edit.setPlainText(draft.get("what_it_does", ""))
        what_does_edit.setMaximumHeight(80)
        what_does_edit.setStyleSheet(input_style)
        layout.addWidget(what_does_edit)

        # What to build
        layout.addWidget(QLabel("What to build:"))
        layout.itemAt(layout.count() - 1).widget().setStyleSheet(label_style)
        what_build_edit = QTextEdit()
        what_build_edit.setPlainText(draft.get("what_to_build", ""))
        what_build_edit.setMaximumHeight(100)
        what_build_edit.setStyleSheet(input_style)
        layout.addWidget(what_build_edit)

        # Why it matters
        layout.addWidget(QLabel("Why it matters:"))
        layout.itemAt(layout.count() - 1).widget().setStyleSheet(label_style)
        why_edit = QLineEdit()
        why_edit.setText(draft.get("why_it_matters", ""))
        why_edit.setStyleSheet(input_style)
        layout.addWidget(why_edit)

        # Dependencies
        layout.addWidget(QLabel("Dependencies:"))
        layout.itemAt(layout.count() - 1).widget().setStyleSheet(label_style)
        deps_edit = QLineEdit()
        deps_edit.setText(draft.get("dependencies", "None"))
        deps_edit.setStyleSheet(input_style)
        layout.addWidget(deps_edit)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        discard_btn = QPushButton("Discard")
        discard_btn.setFixedSize(120, 36)
        discard_btn.setStyleSheet("background:#ff4060; color:#fff; border:none; border-radius:6px; font-weight:700; font-size:12px;")
        discard_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(discard_btn)

        commit_btn = QPushButton("Commit to Codex")
        commit_btn.setFixedSize(160, 36)
        commit_btn.setStyleSheet("background:#00e5a0; color:#07090c; border:none; border-radius:6px; font-weight:700; font-size:12px;")
        commit_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(commit_btn)

        layout.addLayout(btn_row)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Gather final values from form
            bo_id = draft["bo_id"]
            bo_text = _coi_tools.coi_format_bo_item(
                bo_id=bo_id,
                title=title_edit.text().strip() or draft.get("title", "Untitled"),
                priority=priority_combo.currentText(),
                target_stage=stage_combo.currentText(),
                activation_rule=activation_edit.text().strip(),
                what_it_does=what_does_edit.toPlainText().strip(),
                what_to_build=what_build_edit.toPlainText().strip(),
                why_it_matters=why_edit.text().strip(),
                dependencies=deps_edit.text().strip(),
            )

            ok, msg = _coi_tools.coi_commit_bo_item(bo_text)
            bo_num = f"BO-{bo_id:03d}"
            if ok:
                title = title_edit.text().strip() or draft.get("title", "Untitled")
                self.append_message("COI",
                    f"{bo_num} — {title} committed to MASTER-BUILD-ORDER.md",
                    "#00e5a0")
                self.history.append({"role": "assistant",
                    "content": f"[Build order item {bo_num} committed to Codex]"})
                write_to_session("COI", f"[BO COMMITTED] {bo_num} — {title}")
            else:
                self.append_message("COI", f"Failed to commit {bo_num}: {msg}", "#ff4060")
        else:
            self.append_message("COI", "Build order draft discarded.", "#2a4050")

    # ── GIT COMMAND HANDLERS (BO-026) ────────────────────────

    def _cmd_git_status(self):
        """Show git status — zero tokens."""
        if not _coi_tools:
            self.append_message("COI", "Tools not loaded.", "#ff4060")
            return
        status = _coi_tools.coi_git_status()
        if "error" in status:
            self.append_message("COI", f"Git error: {status['error']}", "#ff4060")
            return

        lines = [f"Branch: {status.get('branch', 'unknown')}"]
        if status.get("clean"):
            lines.append("Working tree clean — nothing to commit.")
        else:
            if status.get("staged"):
                lines.append(f"\nStaged ({len(status['staged'])}):")
                for f in status["staged"]:
                    lines.append(f"  + {f}")
            if status.get("modified"):
                lines.append(f"\nModified ({len(status['modified'])}):")
                for f in status["modified"]:
                    lines.append(f"  M {f}")
            if status.get("untracked"):
                lines.append(f"\nUntracked ({len(status['untracked'])}):")
                for f in status["untracked"]:
                    lines.append(f"  ? {f}")

        result = "\n".join(lines)
        self.append_message("COI", result, "#00c8f0")
        self.history.append({"role": "assistant", "content": "[git status displayed]"})
        write_to_session("COI", result)

    def _cmd_git_diff(self):
        """Show git diff — zero tokens."""
        if not _coi_tools:
            self.append_message("COI", "Tools not loaded.", "#ff4060")
            return
        diff, msg = _coi_tools.coi_git_diff()
        if diff is None:
            self.append_message("COI", f"Git diff error: {msg}", "#ff4060")
            return
        if not diff:
            self.append_message("COI", "No unstaged changes.", "#00c8f0")
            return
        # Truncate for display
        display = diff[:3000]
        if len(diff) > 3000:
            display += f"\n\n[... diff truncated — {len(diff)} chars total]"
        self.append_message("COI", display, "#00c8f0")
        self.history.append({"role": "assistant", "content": "[git diff displayed]"})
        write_to_session("COI", "[git diff displayed — tool response]")

    def _cmd_git_commit(self):
        """Git commit with approval dialog — shows diff, auto-generates message."""
        if not _coi_tools:
            self.append_message("COI", "Tools not loaded.", "#ff4060")
            return

        self.append_message("COI", "Preparing commit...", "#f0a800")

        def run():
            try:
                status = _coi_tools.coi_git_status()
                if status.get("clean"):
                    self._thread_message.emit("COI", "Nothing to commit — working tree clean.", "#00c8f0")
                    return

                # Get diff for commit message generation
                diff, _ = _coi_tools.coi_git_diff()
                # Also get staged diff
                staged_code, staged_out, _ = _coi_tools._git_run(["diff", "--cached"])
                full_diff = (diff or "") + "\n" + (staged_out or "")

                # Generate commit message
                self._thread_message.emit("COI", "Generating commit message...", "#f0a800")
                auto_message = _coi_tools.coi_git_generate_commit_message(full_diff or "Various changes")

                # Collect files to commit
                files = (status.get("modified", []) + status.get("untracked", [])
                         + status.get("staged", []))

                # Show approval on main thread
                self._git_commit_ready.emit(auto_message, files, full_diff[:2000] or "No diff available")
            except Exception as e:
                self._thread_message.emit("COI", f"Commit prep error: {str(e)[:200]}", "#ff4060")

        threading.Thread(target=run, daemon=True).start()

    def _on_git_commit_ready(self, message, files, diff_preview):
        """Show commit approval dialog on main thread."""
        dialog = QDialog(self)
        dialog.setWindowTitle("COI — Git Commit Approval")
        dialog.setMinimumSize(600, 450)
        dialog.setStyleSheet("background:#0d1117; color:#d8e8f0;")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        header = QLabel("GIT COMMIT — Dave's Approval Required")
        header.setStyleSheet("color:#f0a800; font-size:13px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(header)

        # Files
        files_label = QLabel(f"Files ({len(files)}):")
        files_label.setStyleSheet("color:#00e5a0; font-size:11px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(files_label)

        files_text = QTextEdit()
        files_text.setReadOnly(True)
        files_text.setMaximumHeight(80)
        files_text.setStyleSheet("background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; font-size:11px; font-family:'JetBrains Mono',monospace;")
        files_text.setPlainText("\n".join(files))
        layout.addWidget(files_text)

        # Commit message — editable
        msg_label = QLabel("Commit message (editable):")
        msg_label.setStyleSheet("color:#00c8f0; font-size:11px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(msg_label)

        msg_edit = QLineEdit()
        msg_edit.setText(message)
        msg_edit.setStyleSheet("background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; padding:8px; font-size:12px; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(msg_edit)

        # Diff preview
        diff_label = QLabel("Diff preview:")
        diff_label.setStyleSheet("color:#2a4050; font-size:10px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(diff_label)

        diff_view = QTextEdit()
        diff_view.setReadOnly(True)
        diff_view.setStyleSheet("background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; font-size:10px; font-family:'JetBrains Mono',monospace;")
        diff_view.setPlainText(diff_preview)
        layout.addWidget(diff_view, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        reject_btn = QPushButton("Reject")
        reject_btn.setFixedSize(100, 36)
        reject_btn.setStyleSheet("background:#ff4060; color:#fff; border:none; border-radius:6px; font-weight:700; font-size:12px;")
        reject_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(reject_btn)

        approve_btn = QPushButton("Commit")
        approve_btn.setFixedSize(100, 36)
        approve_btn.setStyleSheet("background:#00e5a0; color:#07090c; border:none; border-radius:6px; font-weight:700; font-size:12px;")
        approve_btn.clicked.connect(dialog.accept)
        btn_row.addWidget(approve_btn)

        layout.addLayout(btn_row)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            final_msg = msg_edit.text().strip() or message
            self.append_message("COI", f"Committing: {final_msg}", "#f0a800")

            def do_commit():
                try:
                    # Stage all modified + untracked
                    _coi_tools.coi_git_stage(files)
                    ok, commit_hash, out = _coi_tools.coi_git_commit(final_msg)
                    if ok:
                        self._thread_message.emit("COI", f"Committed: {commit_hash} — {final_msg}", "#00e5a0")
                    else:
                        self._thread_message.emit("COI", f"Commit failed: {out}", "#ff4060")
                except Exception as e:
                    self._thread_message.emit("COI", f"Commit error: {str(e)[:200]}", "#ff4060")

            threading.Thread(target=do_commit, daemon=True).start()
        else:
            self.append_message("COI", "Commit rejected by Dave.", "#ff4060")

    def _cmd_git_push(self):
        """Git push with approval."""
        if not _coi_tools:
            self.append_message("COI", "Tools not loaded.", "#ff4060")
            return

        status = _coi_tools.coi_git_status()
        branch = status.get("branch", "unknown")

        reply = QMessageBox.question(
            self, "COI — Push Approval",
            f"Push branch '{branch}' to GitHub?\n\nThis will push all committed changes to the remote.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.append_message("COI", f"Pushing {branch} to GitHub...", "#f0a800")

            def do_push():
                try:
                    ok, msg = _coi_tools.coi_git_push(branch)
                    if ok:
                        self._thread_message.emit("COI", f"Pushed: {msg}", "#00e5a0")
                    else:
                        self._thread_message.emit("COI", f"Push failed: {msg}", "#ff4060")
                except Exception as e:
                    self._thread_message.emit("COI", f"Push error: {str(e)[:200]}", "#ff4060")

            threading.Thread(target=do_push, daemon=True).start()
        else:
            self.append_message("COI", "Push rejected by Dave.", "#ff4060")

    def _cmd_build_order(self):
        """Display build order summary — deterministic, zero tokens."""
        bo_path = ICM_ROOT / "COI/L1-Routing/MASTER-BUILD-ORDER.md"
        if not bo_path.exists():
            self.append_message("COI", "Build order file not found.", "#ff4060")
            return

        try:
            content = bo_path.read_text(encoding="utf-8")
        except Exception as e:
            self.append_message("COI", f"Could not read build order: {e}", "#ff4060")
            return

        # Extract blockers
        blockers = []
        # Extract stages
        stages = []
        # Extract BO items
        bo_items = []

        for line in content.splitlines():
            line_s = line.strip()
            # Blockers table rows
            if line_s.startswith("|") and ("✅" in line or "🔲" in line or "🟡" in line):
                # Parse table: | # | description | status |
                parts = [p.strip() for p in line_s.split("|") if p.strip()]
                if len(parts) >= 3:
                    blockers.append(f"  {parts[2]}  {parts[1]}")

            # Stage headers
            if line_s.startswith("### STAGE"):
                stages.append(line_s.replace("### ", ""))

            # BO items
            if line_s.startswith("### BO-"):
                bo_items.append(line_s.replace("### ", ""))

        # Build compact display
        lines = ["Here's your build order.\n"]

        if blockers:
            lines.append("BLOCKERS:")
            lines.extend(blockers)
            lines.append("")

        if stages:
            lines.append("STAGES:")
            for s in stages:
                lines.append(f"  {s}")
            lines.append("")

        if bo_items:
            lines.append(f"BUILD ITEMS ({len(bo_items)} total):")
            for item in bo_items:
                lines.append(f"  {item}")

        result = "\n".join(lines)
        self.append_message("COI", result, "#00c8f0")
        self.history.append({"role": "assistant", "content": result})
        write_to_session("COI", result)

    def _cmd_session_briefing(self):
        """Display session briefing summary — deterministic, zero tokens."""
        briefing_path = ICM_ROOT / "COI/L4-Working/memory/next-session-briefing.md"
        if not briefing_path.exists():
            self.append_message("COI", "No session briefing found.", "#ff4060")
            return

        try:
            content = briefing_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            self.append_message("COI", f"Could not read briefing: {e}", "#ff4060")
            return

        # Show first 2000 chars — enough for the key sections
        if len(content) > 2000:
            display = content[:2000] + "\n\n[... truncated — full file is " + str(len(content)) + " chars]"
        else:
            display = content

        self.append_message("COI", display, "#00c8f0")
        self.history.append({"role": "assistant", "content": "[Session briefing displayed]"})
        write_to_session("COI", "[Session briefing displayed — tool response, zero tokens]")

    def _cmd_open_loops(self):
        """Display open loops — deterministic, zero tokens."""
        loops_path = ICM_ROOT / "COI/L4-Working/memory/open-loops.md"
        if not loops_path.exists():
            self.append_message("COI", "No open-loops.md found.", "#ff4060")
            return

        try:
            content = loops_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            self.append_message("COI", f"Could not read open loops: {e}", "#ff4060")
            return

        if len(content) > 2000:
            display = content[:2000] + "\n\n[... truncated]"
        else:
            display = content

        self.append_message("COI", display, "#00c8f0")
        self.history.append({"role": "assistant", "content": "[Open loops displayed]"})
        write_to_session("COI", "[Open loops displayed — tool response, zero tokens]")

    def _cmd_memory_files(self):
        """List memory files — deterministic, zero tokens."""
        memory_dir = ICM_ROOT / "COI/L4-Working/memory"
        if not memory_dir.exists():
            self.append_message("COI", "Memory directory not found.", "#ff4060")
            return

        files = sorted(memory_dir.glob("*.md"))
        if not files:
            self.append_message("COI", "No memory files found.", "#ff4060")
            return

        lines = [f"Memory files ({len(files)}):"]
        for f in files:
            size = f.stat().st_size
            lines.append(f"  {f.name}  ({size:,} bytes)")

        result = "\n".join(lines)
        self.append_message("COI", result, "#00c8f0")
        self.history.append({"role": "assistant", "content": "[Memory files listed]"})
        write_to_session("COI", "[Memory files listed — tool response, zero tokens]")

    def run_health_check(self):
        self.append_message("COI", "Running health check...", "#f0a800")
        def check():
            results = []
            # Ollama
            try:
                r = requests.get("http://localhost:11434/api/tags", timeout=5)  # DEPRECATED-V5
                models = [m["name"] for m in r.json().get("models", [])]  # DEPRECATED-V5
                results.append(f"OLLAMA: UP — {len(models)} models loaded")  # DEPRECATED-V5
                for needed in ["llama3.1:8b", "deepseek-coder-v2:lite", "dolphin3:8b", "llama3.2:3b"]:  # DEPRECATED-V5
                    status = "OK" if needed in models else "MISSING"  # DEPRECATED-V5
                    results.append(f"  {needed}: {status}")  # DEPRECATED-V5
            except:
                results.append("OLLAMA: DOWN")  # DEPRECATED-V5

            # Claude API
            config = load_config()
            if config.get("anthropic_api_key"):
                try:
                    r = requests.post(CLAUDE_URL, headers={
                        "Content-Type": "application/json",
                        "x-api-key": config["anthropic_api_key"],
                        "anthropic-version": "2023-06-01",
                    }, json={
                        "model": "claude-sonnet-4-6",
                        "max_tokens": 5,
                        "messages": [{"role": "user", "content": "ping"}],
                    }, timeout=10)
                    if r.status_code == 200:
                        results.append("CLAUDE API: OK")
                    else:
                        results.append(f"CLAUDE API: ERROR {r.status_code}")
                except Exception as e:
                    results.append(f"CLAUDE API: UNREACHABLE — {str(e)[:60]}")
            else:
                results.append("CLAUDE API: NO KEY")

            # Config
            results.append(f"CONFIG: {'EXISTS' if CONFIG_PATH.exists() else 'MISSING'}")

            # Key files
            key_files = {
                "CLAUDE.md": ICM_ROOT / "CLAUDE.md",
                "task-queue.md": ICM_ROOT / "COI/L4-Working/task-queue.md",
                "next-session-briefing.md": ICM_ROOT / "COI/L4-Working/memory/next-session-briefing.md",
                "session-index.md": ICM_ROOT / "COI/L4-Working/session-index.md",
            }
            for name, path in key_files.items():
                results.append(f"  {name}: {'OK' if path.exists() else 'MISSING'}")

            # Sessions
            sess_dir = ICM_ROOT / "COI/L4-Working/sessions"
            if sess_dir.exists():
                count = len(list(sess_dir.glob("*.md"))) - 1  # exclude README
                results.append(f"SESSIONS: {count} files")

            # Mode
            results.append(f"MODE: {self.operating_mode.upper()}")
            results.append(f"FOREGROUND MODEL: {FOREGROUND_MODEL}")  # DEPRECATED-V5

            # Bridge + Immune System
            try:
                r = requests.get("http://localhost:11435/status", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    results.append(f"BRIDGE: ONLINE")

                    # Immune system — Diagnostic (BO-021)
                    diag = data.get("immune", {}).get("diagnostic")
                    if diag:
                        results.append(f"IMMUNE DIAGNOSTIC: {diag['status']} — {diag['passed']}P/{diag['failed']}F/{diag['warnings']}W (last: {diag['last_run']})")
                    else:
                        results.append("IMMUNE DIAGNOSTIC: NOT RUN")

                    # Immune system — Systems Test (BO-022)
                    sys_t = data.get("immune", {}).get("systems_test")
                    if sys_t:
                        results.append(f"IMMUNE SYSTEMS: {sys_t['status']} — {sys_t['passed']}P/{sys_t['failed']}F/{sys_t['warnings']}W (last: {sys_t['last_run']})")
                    else:
                        results.append("IMMUNE SYSTEMS: NOT RUN")

                    # Open loops
                    loops = data.get("open_loops", -1)
                    if loops >= 0:
                        results.append(f"OPEN LOOPS: {loops}")

                    # Sessions
                    sess = data.get("sessions", {})
                    if sess:
                        results.append(f"SESSIONS: {sess.get('total', 0)} total, {sess.get('unprocessed', 0)} unprocessed")
                else:
                    results.append("BRIDGE: ERROR")
            except:
                results.append("BRIDGE: OFFLINE")

            self._thread_message.emit("COI", "HEALTH CHECK\n" + "\n".join(results), "#00e5a0")

        threading.Thread(target=check, daemon=True).start()

    # ── SYSTEM REPORT ─────────────────────────────────────────
    def run_system_report(self):
        self.append_message("COI", "Generating system report...", "#f0a800")
        def report():
            lines = ["# COI System Report — " + datetime.now().strftime("%Y-%m-%d %H:%M")]

            # Open loops
            loops_path = ICM_ROOT / "COI/L4-Working/memory/open-loops.md"
            if loops_path.exists():
                content = loops_path.read_text(encoding="utf-8")
                open_count = content.count("| Open |")
                lines.append(f"Open loops: {open_count}")

            # Task queue
            tq_path = ICM_ROOT / "COI/L4-Working/task-queue.md"
            if tq_path.exists():
                content = tq_path.read_text(encoding="utf-8")
                pending = content.upper().count("PENDING")
                done = content.upper().count("DONE")
                lines.append(f"Tasks: {pending} pending, {done} done")

            # Sessions
            sess_dir = ICM_ROOT / "COI/L4-Working/sessions"
            if sess_dir.exists():
                all_sess = [f for f in sess_dir.glob("*.md") if f.name != "README.md"]
                extracted = len(list(sess_dir.glob("*.extracted")))
                lines.append(f"Sessions: {len(all_sess)} total, {extracted} extracted")

            # Memory files
            mem_dir = ICM_ROOT / "COI/L4-Working/memory"
            if mem_dir.exists():
                mem_files = list(mem_dir.glob("*.md"))
                lines.append(f"Memory files: {len(mem_files)}")

            # Write to build-state.md
            report_text = "\n".join(lines)
            build_state = ICM_ROOT / "COI/L4-Working/memory/build-state.md"
            try:
                build_state.write_text(report_text, encoding="utf-8")
                lines.append("\nSaved to: COI/L4-Working/memory/build-state.md")
            except:
                lines.append("\nFailed to save report.")

            self._thread_message.emit("COI", "\n".join(lines), "#f0a800")

        threading.Thread(target=report, daemon=True).start()

    # ── SEND MESSAGE ─────────────────────────────────────────
    def send_message(self):
        text = self.input.text().strip()
        if not text or self.worker:
            return

        self.input.clear()
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.send_btn.setText("...")

        self.append_message("DAVE", text, "#f0a800")
        self.history.append({"role": "user", "content": text})
        write_to_session("DAVE", text)  # Log instantly — free

        # ── COMMAND ROUTER — TOOLS BEFORE LLM ─────────────────
        # Deterministic handlers fire BEFORE the LLM sees anything.
        # Zero tokens. Instant response. No hallucination. No context pollution.
        # If a command matches, handle it and return — LLM never touched.
        text_lower = text.lower().strip()
        routed = self._route_command(text_lower)
        if routed:
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.send_btn.setText("Send")
            return

        # ── BO-016: DEFERRED WORK QUEUE ──────────────────────
        # Heavy tasks get queued for background processing instead of blocking foreground
        if self.operating_mode == "foreground" and detect_deferred_task(text):
            task_id = write_to_deferred_queue(text)
            self.append_message("COI",
                "I'll look into that properly tonight and have something for you in the morning.\n"
                f"Queued as {task_id}.",
                "#f0a800")
            write_to_session("COI", f"[DEFERRED] {task_id}: {text}")
            self.history.append({"role": "assistant", "content": f"Task deferred to background queue: {task_id}"})
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.send_btn.setText("Send")
            return

        # ── SPEC-02: BO DRAFT TRIGGER FROM CHAT ─────────────
        # Explicit action phrases trigger build order drafting
        bo_triggers = ["lock this in", "add this to the build order", "add to build order",
                       "add to the build order", "make this a build order", "create a bo for this",
                       "let's build order this"]
        if any(t in text_lower for t in bo_triggers):
            self._cmd_draft_bo()
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.send_btn.setText("Send")
            return

        # Detect codex filing trigger — inject map context if found
        trigger = detect_codex_trigger(text)
        augmented_text = text
        if trigger and _coi_tools:
            map_content, _ = _coi_tools.coi_read_map()
            file_list, _   = _coi_tools.coi_list_files("COI/L3-Reference")
            if map_content:
                # Detect if Dave provided content after the trigger
                trigger_phrases = [
                    "write to codex", "write this to codex", "write to the codex",
                    "update codex", "update the codex", "update to codex",
                    "add to codex", "add this to codex", "append to codex"
                ]
                provided_content = text
                for phrase in trigger_phrases:
                    idx = text.lower().find(phrase)
                    if idx != -1:
                        after = text[idx + len(phrase):].strip()
                        if len(after) > 20:
                            provided_content = after
                        break

                has_content = len(provided_content) > 20 and provided_content != text.strip()

                ctx = "\n\n[CODEX FILING CONTEXT]\n"
                ctx += "Action requested: " + trigger + "\n"
                ctx += "Filing map loaded. Use it to decide where this belongs.\n"
                ctx += "Available L3-Reference files: " + str(file_list or []) + "\n\n"

                if has_content:
                    ctx += "CRITICAL RULE: Dave has provided the exact content to file below.\n"
                    ctx += "You MUST use this content EXACTLY as provided — do NOT rewrite, summarize, or modify it.\n"
                    ctx += "Your only job is to decide WHERE it goes, not what it says.\n\n"
                    ctx += "Respond in this exact format:\n"
                    ctx += "FILING DECISION: " + trigger + "\n"
                    ctx += "FILE: [exact codex-relative path]\n"
                    ctx += "REASON: [one line — why this location]\n"
                    ctx += "COMMIT MESSAGE: [short git commit message]\n"
                    ctx += "```\n" + provided_content + "\n```\n"
                    ctx += "Then ask: Approve?\n\n"
                else:
                    ctx += "Dave has not provided content yet.\n"
                    ctx += "Ask Dave: What would you like me to write?\n"
                    ctx += "Do NOT generate content — wait for Dave to provide it.\n\n"

                ctx += "CODEX MAP:\n" + map_content
                augmented_text = text + ctx

        self._show_thinking()
        self._chat_active = True
        self.worker = AIWorker(augmented_text, self.history.copy(), self.operating_mode)
        self.worker.response_ready.connect(lambda r, m: self.on_response(r, m, trigger))
        self.worker.error_occurred.connect(self.on_error)
        self.worker.finished.connect(self.on_worker_done)
        self.worker.start()

    # ── THINKING INDICATOR ──────────────────────────────────
    def _show_thinking(self):
        """Show an animated thinking indicator so Dave knows COI is working"""
        self._thinking_visible = True
        self._thinking_dots = 0

        # Insert thinking block
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat.append("")
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(
            '<div style="color:#5a8090; font-size:10px; padding:4px 12px; '
            'font-family:\'JetBrains Mono\',monospace;" id="thinking">'
            'COI is thinking ●○○</div>'
        )
        self.chat.verticalScrollBar().setValue(
            self.chat.verticalScrollBar().maximum()
        )

        # Start animation timer
        if not hasattr(self, '_thinking_timer'):
            self._thinking_timer = QTimer(self)
            self._thinking_timer.timeout.connect(self._animate_thinking)
        self._thinking_timer.start(500)

    def _animate_thinking(self):
        """Cycle the thinking dots animation."""
        if not getattr(self, '_thinking_visible', False):
            return
        self._thinking_dots = (getattr(self, '_thinking_dots', 0) + 1) % 4
        dots = ["●○○", "○●○", "○○●", "○●○"][self._thinking_dots]

        # Update the last line
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(
            f'<span style="color:#5a8090; font-size:10px; '
            f'font-family:\'JetBrains Mono\',monospace;">'
            f'COI is thinking {dots}</span>'
        )

    def _hide_thinking(self):
        """Remove the thinking indicator"""
        if not getattr(self, '_thinking_visible', False):
            return
        self._thinking_visible = False

        # Stop animation
        if hasattr(self, '_thinking_timer'):
            self._thinking_timer.stop()

        # Remove the last line (thinking indicator)
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()  # Remove the newline

    # ── RECEIVE RESPONSE ─────────────────────────────────────
    def on_response(self, reply, model, trigger=None):
        self._hide_thinking()
        self.history.append({"role": "assistant", "content": reply})
        write_to_session("COI", reply)  # Log instantly — free
        self.model_label.setText(model)
        self.model_label.setStyleSheet("color:#5a8090; font-size:10px; font-family:'JetBrains Mono',monospace; margin-left:16px;")

        # Token tracking — record usage from last Ollama response
        if hasattr(self, 'token_tracker') and self.worker and hasattr(self.worker, '_last_response_data'):
            data = self.worker._last_response_data
            if data:
                self.token_tracker.record(
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    model=data.get("model", model),
                    stage="chat",
                    max_tokens=2048
                )

        # ── CHECK FOR [RUN: command] REQUESTS ─────────────────
        # COI proposes a shell command — Dave must approve before execution
        import re
        run_matches = re.findall(r"\[RUN:\s*([^\]]+)\]", reply, re.IGNORECASE)
        if run_matches:
            # Strip [RUN:] tags from displayed message, show the rest
            display_reply = re.sub(r"\[RUN:\s*[^\]]+\]", "", reply).strip()
            if display_reply:
                self.append_message("COI", display_reply, "#00c8f0")
            self.handle_command_requests(run_matches, reply)
            # Still run other checks below (codex intel, etc.)

        # ── CHECK FOR [READ: path] REQUESTS ──────────────────
        # COI signals she needs a file — fetch and inject automatically
        read_matches = re.findall(r"\[READ:\s*([^\]]+)\]", reply, re.IGNORECASE)
        if read_matches and _coi_tools:
            if not run_matches:
                self.append_message("COI", reply, "#00c8f0")
            self.handle_file_reads(read_matches, reply)
            return

        # ── CHECK FOR FETCH: requests (legacy support) ───────
        fetch_matches = re.findall(r"\[FETCH:\s*([^\]]+)\]", reply, re.IGNORECASE)
        if fetch_matches and _coi_tools:
            if not run_matches:
                self.append_message("COI", reply, "#00c8f0")
            self.handle_file_reads(fetch_matches, reply)
            return

        # ── CHECK FOR [DROPOFF: id] REQUESTS ─────────────────
        dropoff_matches = re.findall(r"\[DROPOFF:\s*([^\]]+)\]", reply, re.IGNORECASE)
        if dropoff_matches:
            display_reply = re.sub(r"\[DROPOFF:\s*[^\]]+\]", "", reply).strip()
            if display_reply:
                self.append_message("COI", display_reply, "#00c8f0")
            self._handle_dropoff_requests(dropoff_matches)
            return

        if not run_matches:
            self.append_message("COI", reply, "#00c8f0")

        # Handle codex filing trigger response
        if trigger:
            parsed = parse_codex_update(reply)
            if parsed["path"] and parsed["content"]:
                self.show_codex_approval(
                    parsed["path"],
                    parsed["content"],
                    parsed["commit"],
                    trigger
                )
        # Also check for spontaneous codex update proposals
        elif detect_codex_update(reply):
            parsed = parse_codex_update(reply)
            if parsed["path"] and parsed["content"]:
                self.show_codex_approval(parsed["path"], parsed["content"], parsed["commit"], "write")

        # Codex Intelligence — scan every exchange for Codex-worthy content
        # Runs in background thread, zero cost if no triggers (regex only)
        if _codex_intel:
            user_msg = self.history[-2]["content"] if len(self.history) >= 2 else ""
            self._run_codex_intelligence(user_msg, reply)

    def _run_codex_intelligence(self, user_message, coi_reply):
        """Run Codex Intelligence scanner in background.
        Detects Codex-worthy content and queues drafts for Dave's approval.
        Zero cost if no triggers — regex pre-scan filters everything."""
        def run():
            try:
                drafts = _codex_intel.process_conversation(user_message, coi_reply)
                if drafts:
                    for draft in drafts:
                        self._thread_message.emit("COI",
                            f"[Codex Intelligence] Detected: {draft['category'].replace('_', ' ')}\n"
                            f"Target: {draft['path']}\n"
                            f"Queued for approval: {Path(draft['approval_file']).name}",
                            "#f0a800")
            except Exception as e:
                pass  # Codex Intelligence failure never interrupts conversation

        threading.Thread(target=run, daemon=True).start()

    # Commands that modify the system — these ALWAYS require Dave's approval.
    # If a command contains NONE of these, it's read-only and can auto-execute.
    UNSAFE_PATTERNS = re.compile(
        r"("
        r"Remove-|Delete-|Stop-|Kill-|Set-|New-|Start-|Restart-|"
        r"Disable-|Enable-|Invoke-WebRequest|Invoke-RestMethod|"
        r"Install-|Uninstall-|Update-|Clear-|Reset-|"
        r"Add-\w|Move-|Copy-|Rename-|"  # Add-\w to avoid matching Add-Type false positives
        r"Register-|Unregister-|Grant-|Revoke-|"
        r"Send-|Publish-|Push-|"
        r"rm\s|del\s|rd\s|rmdir\s|format\s|shutdown|taskkill|"
        r"Out-File|Tee-Object|Export-|Set-Content|"
        r">>|>[^=]|"  # Redirect operators (but not >=)
        r"net\s+(?:user|stop|start)|reg\s+(?:add|delete)|"
        r"schtasks|sc\s+(?:stop|delete|create)"
        r")",
        re.IGNORECASE
    )

    def _is_safe_command(self, cmd):
        """Check if a command is read-only and can auto-execute without approval.
        Strategy: block anything that can MODIFY — everything else is safe to read."""
        return not self.UNSAFE_PATTERNS.search(cmd)

    def handle_command_requests(self, commands, original_reply):
        """Execute commands COI wants to run.
        Safe read-only commands auto-execute. Others require Dave's approval.
        Blocked commands are hard-rejected (BO-027)."""
        import subprocess

        for cmd in commands:
            cmd = cmd.strip()

            # BO-027: Check blocklist first — hard no
            if _coi_tools and hasattr(_coi_tools, 'coi_shell_classify'):
                classification = _coi_tools.coi_shell_classify(cmd)
                if classification == "blocked":
                    self.append_message("COI", f"BLOCKED — dangerous command rejected: {cmd[:100]}", "#ff4060")
                    write_to_session("COI", f"[COMMAND BLOCKED] {cmd}")
                    if hasattr(_coi_tools, 'coi_shell_log'):
                        _coi_tools.coi_shell_log({
                            "command": cmd, "type": "shell", "return_code": -1,
                            "stdout": "BLOCKED", "approved_by": "system-blocklist"
                        })
                    continue

            auto = self._is_safe_command(cmd)

            if auto:
                # Read-only command — execute immediately
                self.append_message("COI", f"Running: {cmd[:200]}", "#f0a800")
                write_to_session("COI", f"[COMMAND AUTO-APPROVED] {cmd}")
                final_cmd = cmd
            else:
                # Could modify system — require Dave's approval
                explanation = re.sub(r"\[RUN:\s*[^\]]+\]", "", original_reply).strip()[:200]
                dialog = CommandApprovalDialog(cmd, explanation, parent=self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    self.append_message("COI", f"Command rejected by Dave: {cmd[:80]}", "#ff4060")
                    write_to_session("COI", f"[COMMAND REJECTED] {cmd}")
                    continue
                final_cmd = dialog.get_command()
                self.append_message("COI", f"Running: {final_cmd}", "#f0a800")
                write_to_session("COI", f"[COMMAND APPROVED] {final_cmd}")

            # Execute command in background thread (both auto and manual paths)
            def run_cmd(command=final_cmd):
                try:
                    result = subprocess.run(
                        ["powershell", "-Command", command],
                        capture_output=True, text=True, timeout=30,
                        cwd=str(ICM_ROOT)
                    )
                    output = result.stdout.strip()
                    error = result.stderr.strip()

                    if output:
                        self._thread_message.emit("COI", f"Output:\n{output[:3000]}", "#00e5a0")
                        write_to_session("COI", f"[COMMAND OUTPUT]\n{output[:3000]}")
                    if error:
                        self._thread_message.emit("COI", f"Errors:\n{error[:1000]}", "#ff4060")

                    # Inject output back into conversation so COI can use it
                    cmd_result = output or error or "(no output)"
                    self._history_append.emit({
                        "role": "user",
                        "content": f"[Command executed: {command}]\nOutput:\n{cmd_result[:2000]}"
                    })

                    if not output and not error:
                        self._thread_message.emit("COI", "Command completed (no output).", "#5a8090")

                    # BO-027: Log execution
                    if _coi_tools and hasattr(_coi_tools, 'coi_shell_log'):
                        _coi_tools.coi_shell_log({
                            "command": command, "type": "shell",
                            "return_code": result.returncode,
                            "stdout": (output or "")[:200],
                            "approved_by": "auto" if auto else "Dave"
                        })

                except subprocess.TimeoutExpired:
                    self._thread_message.emit("COI", "Command timed out (30s limit).", "#ff4060")
                except Exception as e:
                    self._thread_message.emit("COI", f"Command failed: {str(e)[:200]}", "#ff4060")

            threading.Thread(target=run_cmd, daemon=True).start()

    def _do_start_followup(self, message, history):
        """Start an AIWorker followup — MUST run on main thread (called via signal)"""
        self._chat_active = True
        self.history.append({"role": "user", "content": message})
        self.worker = AIWorker(message, self.history.copy(), self.operating_mode)
        self.worker.response_ready.connect(lambda r, m: self.on_response(r, m))
        self.worker.error_occurred.connect(self.on_error)
        self.worker.finished.connect(self.on_worker_done)
        self.worker.start()

    def _handle_dropoff_requests(self, item_ids):
        """Load drop-off summaries and inject into conversation."""
        from coi_dropoff_worker import load_queue, SUMMARIES_DIR
        queue = load_queue()
        for item_id in item_ids:
            item_id = item_id.strip()
            for item in queue:
                if item["id"] == item_id and item.get("status") == "done":
                    summary_file = item.get("summary_file")
                    if summary_file and Path(summary_file).exists():
                        summary = Path(summary_file).read_text(encoding="utf-8")
                    else:
                        summary = item.get("summary", "[No summary available]")
                    display_name = item.get("display_name", item_id)
                    context = f"[Drop-off summary loaded: {display_name}]\n{summary}"
                    self.history.append({"role": "user", "content": context})
                    self.append_message("COI", f"Loaded drop-off: {display_name}", "#f0a800")
                    # Follow up so COI can use the summary
                    self._do_start_followup(
                        f"I just loaded the drop-off summary for '{display_name}'. "
                        f"Please analyze it and tell Dave what's in it.",
                        self.history.copy()
                    )
                    return
            self.append_message("COI", f"Drop-off {item_id} not found or not yet processed.", "#ff4060")

    def handle_file_reads(self, paths, original_reply):
        """Fetch requested files and inject into conversation automatically.
        Large files (>3000 chars) get truncated to protect the context window."""
        MAX_FILE_INJECT = 3000  # ~750 tokens — safe for 4096 context

        def run():
            try:
                fetched = []
                for path in paths:
                    path = path.strip()
                    self._thread_message.emit("COI", "Reading: " + path + "...", "#f0a800")
                    file_content, msg = _coi_tools.coi_read_file(path)
                    if file_content:
                        char_count = len(file_content)
                        if char_count > MAX_FILE_INJECT:
                            # File too large — truncate and warn
                            truncated = file_content[:MAX_FILE_INJECT]
                            truncated += f"\n\n[FILE TRUNCATED — {char_count:,} chars total, showing first {MAX_FILE_INJECT:,}. Use 'index {path}' to see sections, or 'search {path} : keyword' to find specific content.]"
                            fetched.append((path, truncated))
                            self._thread_message.emit("COI",
                                f"Loaded: {path} (TRUNCATED — {char_count:,} chars, showing {MAX_FILE_INJECT:,})",
                                "#f0a800")
                        else:
                            fetched.append((path, file_content))
                            self._thread_message.emit("COI",
                                f"Loaded: {path} ({char_count:,} chars)", "#00e5a0")
                    else:
                        self._thread_message.emit("COI", "Could not read: " + path + " — " + msg, "#ff4060")

                if fetched:
                    file_context = ""
                    for path, fc in fetched:
                        file_context += "\n\n--- FILE: " + path + " ---\n" + fc + "\n--- END: " + path + " ---"

                    prompt = "[File contents loaded as requested]" + file_context + "\n\nNow please proceed with your task."
                    self._start_followup.emit(prompt, None)
            except Exception as e:
                self._thread_message.emit("COI", "File read error: " + str(e)[:200], "#ff4060")

        threading.Thread(target=run, daemon=True).start()

    def show_codex_approval(self, path, content, commit_msg, action="write"):
        """Show approval dialog for COI Codex update"""
        dialog = CodexUpdateDialog(
            path,
            content,
            commit_msg or "COI Codex " + action.capitalize() + " — " + datetime.now().strftime("%Y-%m-%d %H:%M"),
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            final_content = dialog.get_content()
            self.append_message("COI", "Filing to Codex: " + path + "...", "#f0a800")
            self.do_codex_write(path, final_content, commit_msg, action)
        else:
            self.append_message("COI", "Codex update rejected by Dave.", "#ff4060")

    def do_codex_write(self, path, content, commit_msg, action="write"):
        """Write to Codex — BO-013: local-first, GitHub in background with error recovery"""
        def run():
            try:
                tools = load_coi_tools()
                if not tools:
                    # Fallback: write locally first, then try GitHub
                    self._thread_message.emit("COI", "coi-tools not available — local-first write...", "#f0a800")
                    local_path = ICM_ROOT / path
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_text(content, encoding="utf-8")
                    self._thread_message.emit("COI", "Written locally: " + path, "#00e5a0")

                    # GitHub in background — BO-013: error recovery on silent thread failure
                    def github_bg():
                        try:
                            existing, sha = github_read_file(path)
                            ok, result = github_write_file(path, content, commit_msg or "COI Update", sha)
                            if ok:
                                self._thread_message.emit("COI", "GitHub synced: " + path, "#00e5a0")
                            else:
                                self._log_github_error(path, result, action)
                                self._thread_message.emit("COI", "GitHub sync failed (logged to error-memory): " + result[:100], "#f0a800")
                        except Exception as e:
                            self._log_github_error(path, str(e), action)
                            self._thread_message.emit("COI", "GitHub thread error (logged): " + str(e)[:100], "#f0a800")
                    threading.Thread(target=github_bg, daemon=True).start()
                    return

                if action == "write":
                    ok, result = tools.coi_write_file(path, content, commit_msg)
                elif action == "update":
                    ok, result = tools.coi_update_file(path, content, commit_msg)
                elif action == "append":
                    ok, result = tools.coi_append_file(path, content, commit_msg)
                else:
                    ok, result = tools.coi_update_file(path, content, commit_msg)

                if ok:
                    self._thread_message.emit("COI", "Codex updated. " + result, "#00e5a0")
                else:
                    self._thread_message.emit("COI", "Codex write issue: " + result, "#f0a800")
            except Exception as e:
                self._thread_message.emit("COI", "Codex write error: " + str(e)[:200], "#ff4060")
                self._log_github_error(path, str(e), action)

        threading.Thread(target=run, daemon=True).start()

    def _log_github_error(self, path, error_msg, operation):
        """Log GitHub failure to error-memory.md — BO-013: never fail silently"""
        try:
            error_path = ICM_ROOT / "COI/L4-Working/memory/error-memory.md"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"\n## {ts} — GitHub Write Failure (Desktop)\n"
            entry += f"- **Operation:** {operation}\n"
            entry += f"- **File:** {path}\n"
            entry += f"- **Error:** {error_msg[:200]}\n"
            entry += f"- **Local write:** Succeeded\n"
            entry += f"- **Action needed:** Retry GitHub sync\n"
            if error_path.exists():
                with open(error_path, "a", encoding="utf-8") as f:
                    f.write(entry)
        except:
            pass

    def on_error(self, error):
        self._hide_thinking()
        self.append_message("COI", f"Error: {error}", "#ff4060")
        # Log to recent errors for repair tool
        if not hasattr(self, '_recent_errors'):
            self._recent_errors = []
        self._recent_errors.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "error": str(error)[:500]
        })
        # Keep last 20 errors
        self._recent_errors = self._recent_errors[-20:]

    def on_worker_done(self):
        self.worker = None
        self._chat_active = False
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")
        self.input.setFocus()

    # ── APPEND MESSAGE ───────────────────────────────────────
    def append_message(self, sender, text, color):
        time_str = datetime.now().strftime("%H:%M")

        is_dave = sender.upper() == "DAVE"
        is_coi = sender.upper() == "COI"

        # Build HTML block with visual distinction
        # Dave: right-ish, warm background | COI: left, dark background
        if is_dave:
            bg = "#111920"
            align = "right"
            border_color = "#f0a800"
        else:
            bg = "#0a0f14"
            align = "left"
            border_color = color

        # Timestamp style
        ts_html = f'<span style="color:#2a4050; font-size:9px;">{time_str}</span>'

        # Sender label
        sender_html = (
            f'<span style="color:{color}; font-weight:700; font-size:10px; '
            f'font-family:\'JetBrains Mono\',monospace;">{sender}</span>'
        )

        # Message body — render markdown for COI, plain for Dave
        if is_coi:
            body_html = self._render_markdown(text)
        else:
            body_html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        block = (
            f'<div style="background:{bg}; border-left:2px solid {border_color}; '
            f'padding:8px 12px; margin:4px 0; border-radius:4px;">'
            f'{sender_html} {ts_html}<br>'
            f'<span style="color:#d8e8f0; font-size:13px;">{body_html}</span>'
            f'</div>'
        )

        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat.append("")  # newline spacer
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(block)

        # Scroll to bottom
        self.chat.verticalScrollBar().setValue(
            self.chat.verticalScrollBar().maximum()
        )

    def _render_markdown(self, text):
        """Convert basic markdown to HTML for COI messages.
        Handles: headers, bold, italic, bullets, code blocks, inline code."""
        import re as _re

        # Escape HTML first
        html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Code blocks (``` ... ```)
        def _code_block(m):
            code = m.group(1).strip()
            return (f'<div style="background:#111920; border:1px solid #1e2d3d; '
                    f'border-radius:4px; padding:8px; margin:4px 0; '
                    f'font-family:\'JetBrains Mono\',monospace; font-size:11px; '
                    f'color:#00e5a0;">{code}</div>')
        html = _re.sub(r'```(?:\w*)\n?(.*?)```', _code_block, html, flags=_re.DOTALL)

        # Inline code (`...`)
        html = _re.sub(r'`([^`]+)`',
            r'<span style="background:#111920; color:#00c8f0; padding:1px 4px; '
            r'border-radius:3px; font-family:\'JetBrains Mono\',monospace; '
            r'font-size:11px;">\1</span>', html)

        # Headers (### → bold colored)
        html = _re.sub(r'^#{3,}\s+(.+)$',
            r'<br><span style="color:#00c8f0; font-weight:700; font-size:12px;">\1</span>',
            html, flags=_re.MULTILINE)
        html = _re.sub(r'^#{1,2}\s+(.+)$',
            r'<br><span style="color:#f0a800; font-weight:700; font-size:13px;">\1</span>',
            html, flags=_re.MULTILINE)

        # Bold (**text**)
        html = _re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)

        # Italic (*text*)
        html = _re.sub(r'\*(.+?)\*', r'<i>\1</i>', html)

        # Bullet points (- item or * item)
        html = _re.sub(r'^[\-\*]\s+(.+)$',
            r'<span style="color:#5a8090;">  •</span> \1',
            html, flags=_re.MULTILINE)

        # Numbered lists (1. item)
        html = _re.sub(r'^(\d+)\.\s+(.+)$',
            r'<span style="color:#5a8090;">  \1.</span> \2',
            html, flags=_re.MULTILINE)

        # Line breaks
        html = html.replace("\n", "<br>")

        return html

    # ── SESSION SAVE ON CLOSE ───────────────────────────────
    def closeEvent(self, event):
        """Save session state atomically when Dave closes the window."""
        try:
            if SESSION_FILE and SESSION_FILE.exists():
                # Write session close marker
                write_to_session("SYSTEM", "[SESSION CLOSED]")

                # Write session summary to a temp file first, then rename (atomic)
                summary_lines = [f"\n---\n## Session Summary — {datetime.now().strftime('%H:%M')}\n"]
                summary_lines.append(f"- Messages: {len(self.history)}")

                # Count Dave vs COI messages
                dave_count = sum(1 for h in self.history if h.get("role") == "user")
                coi_count = sum(1 for h in self.history if h.get("role") == "assistant")
                summary_lines.append(f"- Dave: {dave_count} | COI: {coi_count}")
                summary_lines.append(f"- Model: {FOREGROUND_MODEL}")  # DEPRECATED-V5
                summary_lines.append(f"- Session file: {SESSION_FILE.name}")
                summary_lines.append("")

                summary_text = "\n".join(summary_lines)

                # Atomic write — write to temp, then append
                tmp = SESSION_FILE.with_suffix(".tmp")
                existing = SESSION_FILE.read_text(encoding="utf-8")
                tmp.write_text(existing + summary_text, encoding="utf-8")
                tmp.replace(SESSION_FILE)
        except Exception:
            pass  # Never block close on save failure

        # Stop background workers
        try:
            if hasattr(self, 'dropoff_worker'):
                self.dropoff_worker.requestInterruption()
            if hasattr(self, '_thinking_timer'):
                self._thinking_timer.stop()
        except Exception:
            pass

        event.accept()

# ── ENTRY POINT ──────────────────────────────────────────────
if __name__ == "__main__":
    # Global crash logger — writes traceback to file so crashes can be diagnosed
    _crash_log = ICM_ROOT / "COI/L4-Working/memory/crash-log.md"
    def _crash_handler(exc_type, exc_value, exc_tb):
        import traceback
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        try:
            with open(_crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n```\n{tb}```\n")
        except:
            pass
        sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.excepthook = _crash_handler

    # Also catch crashes in background threads
    def _thread_crash_handler(args):
        import traceback
        tb = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        try:
            with open(_crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [Thread: {args.thread.name}]\n```\n{tb}```\n")
        except:
            pass
    threading.excepthook = _thread_crash_handler

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Try to set font
    font = QFont("Segoe UI", 11)
    app.setFont(font)

    window = COIDesktop()
    window.show()
    sys.exit(app.exec())
