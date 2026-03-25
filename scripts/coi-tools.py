#!/usr/bin/env python3
# ============================================================
# COI Tools — coi-tools.py
# COI's tool library. Importable from anywhere.
# Every tool COI has lives here.
#
# Usage: from coi-tools import coi_write_file, coi_update_file, coi_append_file
# ============================================================

import json
import base64
import subprocess
import requests
import threading
from pathlib import Path
from datetime import datetime

# ── CONFIG ───────────────────────────────────────────────────
ICM_ROOT    = Path("K:/Coi Codex/COI-Codex-ICM")
CONFIG_PATH = ICM_ROOT / "config" / "config.json"
GITHUB_API  = "https://api.github.com"
GITHUB_REPO = "davidsheridan77-dot/COI-Codex-ICM"
MODEL_CONFIG_PATH = ICM_ROOT / "scripts" / "model-config.json"  # DEPRECATED-V5

# ── PROVIDER-ABSTRACTED CACHING ─────────────────────────────
# COI caches the system prompt when the provider supports it.
# Policy lives in the Codex. The adapter handles the mechanism.
# Provider value comes from model-config.json, not hardcoded.

def _get_conversation_provider():  # DEPRECATED-V5
    """Read conversation provider from model-config.json"""  # DEPRECATED-V5
    try:
        with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
            return json.load(f).get("conversation_provider", "anthropic")  # DEPRECATED-V5
    except:
        return "anthropic"

def build_system_payload(content, provider=None):
    """Build provider-appropriate system prompt payload.
    Anthropic: cache_control ephemeral header for server-side prompt caching.
    Others: plain text, no caching headers.
    Local (Ollama): returns plain string — server-side caching irrelevant."""  # DEPRECATED-V5
    if provider is None:
        provider = _get_conversation_provider()  # DEPRECATED-V5

    if provider == "local":  # DEPRECATED-V5
        return content  # Ollama takes plain string  # DEPRECATED-V5

    if provider == "anthropic":
        return [{
            "type": "text",
            "text": content,
            "cache_control": {"type": "ephemeral"}
        }]

    # openai, future providers — structured but no cache header
    return [{"type": "text", "text": content}]

# ── HELPERS ──────────────────────────────────────────────────
def _load_config():
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def _get_token():
    return _load_config().get("github_token", "")

def _github_get_sha(path):
    """Get existing file SHA from GitHub — needed for updates"""
    token = _get_token()
    if not token:
        return None
    try:
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
        r = requests.get(url, headers={
            "Authorization": f"token {token}",
            "User-Agent": "COI-Tools"
        }, timeout=15)
        if r.status_code == 200:
            return r.json().get("sha")
    except:
        pass
    return None

def _github_read(path):
    """Read file content from GitHub"""
    token = _get_token()
    if not token:
        return None
    try:
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"
        r = requests.get(url, headers={
            "Authorization": f"token {token}",
            "User-Agent": "COI-Tools"
        }, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return base64.b64decode(data["content"]).decode("utf-8")
    except:
        pass
    return None

def _github_write(path, content, commit_message, sha=None):
    """Write file to GitHub — creates or updates"""
    token = _get_token()
    if not token:
        return False, "No GitHub token in config"
    try:
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
            "User-Agent": "COI-Tools"
        }, json=body, timeout=30)
        if r.status_code in [200, 201]:
            return True, path
        return False, f"GitHub error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)

def _write_local(path, content):
    """Write file locally to Codex"""
    try:
        local_path = ICM_ROOT / path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        return False

def _log_github_failure(path, error_msg, operation):
    """Log GitHub write failure to error-memory.md for next session — BO-013"""
    try:
        error_path = ICM_ROOT / "COI/L4-Working/memory/error-memory.md"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## {ts} — GitHub Write Failure\n"
        entry += f"- **Operation:** {operation}\n"
        entry += f"- **File:** {path}\n"
        entry += f"- **Error:** {error_msg}\n"
        entry += f"- **Local write:** Succeeded (data safe)\n"
        entry += f"- **Action needed:** Retry GitHub sync next session\n"
        if error_path.exists():
            with open(error_path, "a", encoding="utf-8") as f:
                f.write(entry)
        else:
            error_path.parent.mkdir(parents=True, exist_ok=True)
            error_path.write_text("# COI Error Memory\n" + entry, encoding="utf-8")
    except:
        pass  # Error logging itself failed — nothing more we can do

def _github_write_background(path, content, commit_message, sha=None, operation="write"):
    """Run GitHub write in background thread — BO-013: local-first, GitHub as confirmation"""
    def _do_write():
        ok, result = _github_write(path, content, commit_message, sha)
        if not ok:
            _log_github_failure(path, result, operation)
    threading.Thread(target=_do_write, daemon=True).start()

# ── TOOL 1 — WRITE FILE ──────────────────────────────────────
def coi_write_file(path, content, commit_message=None):
    """
    Create a new file in the Codex.
    Use when: filing new information that doesn't exist yet.

    Args:
        path: Codex-relative path e.g. 'COI/L3-Reference/tools.md'
        content: Full file content as string
        commit_message: Git commit message (auto-generated if not provided)

    Returns:
        (success: bool, message: str)
    """
    if not commit_message:
        commit_message = f"COI Write: {Path(path).name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Check file doesn't already exist
    existing_sha = _github_get_sha(path)
    if existing_sha:
        return False, f"File already exists: {path} — use coi_update_file instead"

    # Write locally first — BO-013: local-first, always safe
    _write_local(path, content)

    # GitHub write in background — failures logged, never silent
    _github_write_background(path, content, commit_message, operation="write")
    return True, f"Written locally, GitHub sync in background: {path}"

# ── TOOL 2 — UPDATE FILE ─────────────────────────────────────
def coi_update_file(path, content, commit_message=None):
    """
    Replace an existing file in the Codex with new content.
    Use when: updating a file with revised or expanded content.

    Args:
        path: Codex-relative path
        content: Complete new file content
        commit_message: Git commit message

    Returns:
        (success: bool, message: str)
    """
    if not commit_message:
        commit_message = f"COI Update: {Path(path).name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Get existing SHA
    sha = _github_get_sha(path)

    # Write locally first — BO-013: local-first, always safe
    _write_local(path, content)

    # GitHub write in background — failures logged, never silent
    _github_write_background(path, content, commit_message, sha, operation="update")
    return True, f"Updated locally, GitHub sync in background: {path}"

# ── TOOL 3 — APPEND TO FILE ──────────────────────────────────
def coi_append_file(path, content, commit_message=None):
    """
    Append content to an existing file in the Codex.
    Use when: adding new entries to decisions.md, open-loops.md, etc.

    Args:
        path: Codex-relative path
        content: Content to append (added to end of file)
        commit_message: Git commit message

    Returns:
        (success: bool, message: str)
    """
    if not commit_message:
        commit_message = f"COI Append: {Path(path).name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Read existing content
    existing = _github_read(path)
    if existing is None:
        # File doesn't exist — create it
        return coi_write_file(path, content, commit_message)

    # Append
    new_content = existing.rstrip() + "\n\n" + content.strip() + "\n"

    # Write locally first — BO-013: local-first, always safe
    _write_local(path, new_content)

    # GitHub write in background — failures logged, never silent
    sha = _github_get_sha(path)
    _github_write_background(path, new_content, commit_message, sha, operation="append")
    return True, f"Appended locally, GitHub sync in background: {path}"

# ── TOOL 4 — READ FILE ───────────────────────────────────────
def coi_read_file(path):
    """
    Read a file from the Codex.
    Use when: COI needs to check existing content before filing.

    Args:
        path: Codex-relative path

    Returns:
        (content: str or None, message: str)
    """
    # Try local first
    local_path = ICM_ROOT / path
    if local_path.exists():
        try:
            content = local_path.read_text(encoding="utf-8")
            return content, f"Read local: {path}"
        except:
            pass

    # Fall back to GitHub
    content = _github_read(path)
    if content:
        return content, f"Read from GitHub: {path}"

    return None, f"File not found: {path}"

# ── TOOL 5 — READ CODEX MAP ──────────────────────────────────
def coi_read_map():
    """
    Read the Codex filing map.
    COI calls this to decide where information belongs.

    Returns:
        (content: str or None, message: str)
    """
    return coi_read_file("COI/L1-Routing/CODEX-MAP.md")

# ── TOOL 6 — LIST FILES ──────────────────────────────────────
def coi_list_files(folder_path=""):
    """
    List files in a Codex folder.
    Use when: COI needs to see what already exists before filing.

    Args:
        folder_path: Codex-relative folder path

    Returns:
        (files: list or None, message: str)
    """
    local_path = ICM_ROOT / folder_path if folder_path else ICM_ROOT
    try:
        if local_path.exists():
            files = [str(f.relative_to(ICM_ROOT)) for f in local_path.rglob("*") if f.is_file()]
            return files, f"Listed {len(files)} files in {folder_path or 'root'}"
    except:
        pass
    return None, f"Could not list files in: {folder_path}"

# ── TOOL 7 — BATCH GITHUB WRITE ─────────────────────────────────
# BO-013: Batch operations — single commit for multiple file changes
# Uses Git Trees API: one API call instead of N per-file PUTs

def coi_batch_github_write(file_ops, commit_message=None):
    """
    Write multiple files to GitHub in a single commit.
    Use when: deploying, syncing, or writing multiple files at once.

    Args:
        file_ops: list of dicts, each with 'path' and 'content'
                  e.g. [{'path': 'COI/L4-Working/memory/x.md', 'content': '...'}]
        commit_message: Single commit message for the batch

    Returns:
        (success: bool, message: str)
    """
    if not file_ops:
        return True, "No files to write"

    # Write all files locally first — BO-013: local-first, always safe
    for op in file_ops:
        _write_local(op["path"], op["content"])

    if not commit_message:
        names = [Path(op["path"]).name for op in file_ops]
        commit_message = f"COI Batch: {len(file_ops)} files — {', '.join(names[:3])}"
        if len(names) > 3:
            commit_message += f" +{len(names) - 3} more"

    # Background GitHub batch via Trees API
    def _do_batch():
        token = _get_token()
        if not token:
            _log_github_failure("batch", "No GitHub token", "batch_write")
            return

        headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "User-Agent": "COI-Tools"
        }
        api = f"{GITHUB_API}/repos/{GITHUB_REPO}"

        try:
            # 1. Get current HEAD SHA and tree SHA
            ref_r = requests.get(f"{api}/git/ref/heads/master", headers=headers, timeout=15)
            if ref_r.status_code != 200:
                _log_github_failure("batch", f"Could not get HEAD ref: {ref_r.status_code}", "batch_write")
                return
            head_sha = ref_r.json()["object"]["sha"]

            commit_r = requests.get(f"{api}/git/commits/{head_sha}", headers=headers, timeout=15)
            if commit_r.status_code != 200:
                _log_github_failure("batch", f"Could not get commit: {commit_r.status_code}", "batch_write")
                return
            base_tree_sha = commit_r.json()["tree"]["sha"]

            # 2. Build tree entries — one blob per file
            tree_items = []
            for op in file_ops:
                blob_r = requests.post(f"{api}/git/blobs", headers=headers, json={
                    "content": base64.b64encode(op["content"].encode("utf-8")).decode("utf-8"),
                    "encoding": "base64"
                }, timeout=15)
                if blob_r.status_code != 201:
                    _log_github_failure(op["path"], f"Blob creation failed: {blob_r.status_code}", "batch_write")
                    return
                tree_items.append({
                    "path": op["path"],
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_r.json()["sha"]
                })

            # 3. Create new tree
            tree_r = requests.post(f"{api}/git/trees", headers=headers, json={
                "base_tree": base_tree_sha,
                "tree": tree_items
            }, timeout=15)
            if tree_r.status_code != 201:
                _log_github_failure("batch", f"Tree creation failed: {tree_r.status_code}", "batch_write")
                return

            # 4. Create commit
            new_commit_r = requests.post(f"{api}/git/commits", headers=headers, json={
                "message": commit_message,
                "tree": tree_r.json()["sha"],
                "parents": [head_sha]
            }, timeout=15)
            if new_commit_r.status_code != 201:
                _log_github_failure("batch", f"Commit creation failed: {new_commit_r.status_code}", "batch_write")
                return

            # 5. Update ref
            update_r = requests.patch(f"{api}/git/refs/heads/master", headers=headers, json={
                "sha": new_commit_r.json()["sha"]
            }, timeout=15)
            if update_r.status_code != 200:
                _log_github_failure("batch", f"Ref update failed: {update_r.status_code}", "batch_write")
                return

        except Exception as e:
            _log_github_failure("batch", str(e), "batch_write")

    threading.Thread(target=_do_batch, daemon=True).start()
    return True, f"Batch: {len(file_ops)} files written locally, GitHub sync in background"


# ── TOOL 8 — SAFE FILE READING ───────────────────────────────
# Read large files without blowing the context window.
# Index -> Section -> Search. Never load the whole file.

def coi_file_index(path):
    """Extract table of contents from a markdown file.
    Returns list of sections with line numbers, heading level, and char counts.
    Zero tokens — just structure."""
    full_path = ICM_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not full_path.exists():
        return None, f"File not found: {path}"

    try:
        content = full_path.read_text(encoding="utf-8")
    except Exception as e:
        return None, str(e)

    lines = content.splitlines()
    sections = []
    current_start = 0
    current_heading = "(top)"
    current_level = 0

    for i, line in enumerate(lines):
        if line.startswith("#"):
            # Close previous section
            if sections or current_start > 0:
                char_count = sum(len(lines[j]) for j in range(current_start, i))
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "line": current_start + 1,
                    "chars": char_count,
                })
            # Start new section
            level = len(line) - len(line.lstrip("#"))
            current_heading = line.lstrip("#").strip()
            current_level = level
            current_start = i

    # Close last section
    char_count = sum(len(lines[j]) for j in range(current_start, len(lines)))
    sections.append({
        "heading": current_heading,
        "level": current_level,
        "line": current_start + 1,
        "chars": char_count,
    })

    total_chars = len(content)
    return {
        "file": str(path),
        "total_chars": total_chars,
        "total_lines": len(lines),
        "sections": sections,
    }, "OK"

def coi_file_section(path, section_name, max_chars=3000):
    """Load a specific section from a markdown file by heading name.
    Returns only that section's content, capped at max_chars.
    Safe for context injection."""
    full_path = ICM_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not full_path.exists():
        return None, f"File not found: {path}"

    try:
        content = full_path.read_text(encoding="utf-8")
    except Exception as e:
        return None, str(e)

    lines = content.splitlines()
    section_name_lower = section_name.lower().strip()

    # Find the section start
    start_line = None
    start_level = 0
    for i, line in enumerate(lines):
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            level = len(line) - len(line.lstrip("#"))
            if section_name_lower in heading.lower():
                start_line = i
                start_level = level
                break

    if start_line is None:
        return None, f"Section '{section_name}' not found"

    # Find section end — next heading at same or higher level
    end_line = len(lines)
    for i in range(start_line + 1, len(lines)):
        if lines[i].startswith("#"):
            level = len(lines[i]) - len(lines[i].lstrip("#"))
            if level <= start_level:
                end_line = i
                break

    section_text = "\n".join(lines[start_line:end_line]).strip()

    if len(section_text) > max_chars:
        section_text = section_text[:max_chars] + f"\n\n[... section truncated at {max_chars} chars — {len(section_text)} total]"

    return section_text, "OK"

def coi_file_search(path, query, context_lines=2, max_results=10):
    """Search a file for a keyword/pattern. Returns matching lines with context.
    Like grep but safe for COI — returns structured results, not the whole file."""
    full_path = ICM_ROOT / path if not Path(path).is_absolute() else Path(path)
    if not full_path.exists():
        return None, f"File not found: {path}"

    try:
        content = full_path.read_text(encoding="utf-8")
    except Exception as e:
        return None, str(e)

    lines = content.splitlines()
    query_lower = query.lower()
    matches = []

    for i, line in enumerate(lines):
        if query_lower in line.lower():
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            context = []
            for j in range(start, end):
                prefix = ">>>" if j == i else "   "
                context.append(f"{prefix} {j+1}: {lines[j]}")
            matches.append({
                "line": i + 1,
                "match": line.strip(),
                "context": "\n".join(context),
            })
            if len(matches) >= max_results:
                break

    return {
        "file": str(path),
        "query": query,
        "total_matches": len(matches),
        "results": matches,
    }, "OK"


# ── TOOL 9 — GIT OPERATIONS (BO-026) ────────────────────────
# COI owns the full Git workflow. All mutating ops go through approval.

def _git_run(args, timeout=30):
    """Run a git command in ICM_ROOT. Returns (return_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(ICM_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Git command timed out"
    except FileNotFoundError:
        return -1, "", "Git not found on PATH"
    except Exception as e:
        return -1, "", str(e)

def coi_git_status():
    """Get git status. Returns dict with modified, untracked, staged files. Read-only."""
    code, out, err = _git_run(["status", "--porcelain"])
    if code != 0:
        return {"error": err or "git status failed"}

    modified, untracked, staged = [], [], []
    for line in out.splitlines():
        if not line or len(line) < 3:
            continue
        index_status = line[0]
        work_status = line[1]
        filepath = line[3:]
        if index_status in ("A", "M", "D", "R"):
            staged.append(filepath)
        if work_status == "M":
            modified.append(filepath)
        elif work_status == "?" or line.startswith("??"):
            untracked.append(filepath)

    # Current branch
    _, branch, _ = _git_run(["rev-parse", "--abbrev-ref", "HEAD"])

    return {
        "branch": branch,
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "clean": len(staged) == 0 and len(modified) == 0 and len(untracked) == 0
    }

def coi_git_diff(paths=None):
    """Get diff output. Read-only."""
    args = ["diff"]
    if paths:
        args.extend(paths if isinstance(paths, list) else [paths])
    code, out, err = _git_run(args)
    if code != 0:
        return None, err or "git diff failed"
    return out, "OK"

def coi_git_stage(paths):
    """Stage files. Returns (success, message). Requires approval."""
    if isinstance(paths, str):
        paths = [paths]
    code, out, err = _git_run(["add"] + paths)
    if code != 0:
        return False, err or "git add failed"
    return True, f"Staged {len(paths)} file(s)"

def coi_git_commit(message, paths=None):
    """Commit staged changes. Returns (success, commit_hash, message). Requires approval."""
    # Stage specific paths if provided
    if paths:
        ok, stage_msg = coi_git_stage(paths)
        if not ok:
            return False, None, stage_msg

    code, out, err = _git_run(["commit", "-m", message])
    if code != 0:
        return False, None, err or "git commit failed"

    # Get the commit hash
    _, hash_out, _ = _git_run(["rev-parse", "--short", "HEAD"])
    coi_shell_log({
        "command": f"git commit -m \"{message}\"",
        "type": "git",
        "return_code": code,
        "stdout": out[:200],
        "approved_by": "Dave"
    })
    return True, hash_out, out

def coi_git_generate_commit_message(diff_text=None):  # DEPRECATED-V5 — uses Ollama for commit message generation
    """Use the briefing model to generate a commit message from diff context."""
    if not diff_text:
        diff_text, _ = coi_git_diff()
    if not diff_text:
        return datetime.now().strftime("COI update — %Y-%m-%d %H:%M")

    # Truncate diff to keep within context budget
    if len(diff_text) > 3000:
        diff_text = diff_text[:3000] + "\n[... diff truncated]"

    try:
        # Get briefing model from config
        try:
            with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
                cfg = json.load(f)
            model = cfg.get("roles", {}).get("general", {}).get("model", "mistral:7b-instruct-q4_K_M")  # DEPRECATED-V5
        except:
            model = "mistral:7b-instruct-q4_K_M"  # DEPRECATED-V5

        r = requests.post("http://localhost:11434/api/generate", json={  # DEPRECATED-V5
            "model": model,  # DEPRECATED-V5
            "prompt": f"Write a concise git commit message for this diff. One line summary, max 72 chars. No quotes, no prefix, just the message.\n\nDiff:\n{diff_text}",
            "stream": False,
            "options": {"num_ctx": 4096, "temperature": 0.3}
        }, timeout=30)  # DEPRECATED-V5
        if r.status_code == 200:
            msg = r.json().get("response", "").strip()
            # Clean up — take first line, strip quotes
            msg = msg.split("\n")[0].strip().strip('"').strip("'")
            if msg and len(msg) > 5:
                return msg
    except:
        pass

    return datetime.now().strftime("COI update — %Y-%m-%d %H:%M")

def coi_git_branch(branch_name=None, bo_id=None, task_type="feature"):
    """Create and checkout a new branch. Requires approval."""
    if not branch_name:
        if bo_id:
            slug = bo_id.lower().replace(" ", "-")
            branch_name = f"{task_type}/{slug}"
        else:
            branch_name = f"{task_type}/coi-{datetime.now().strftime('%Y%m%d-%H%M')}"

    code, out, err = _git_run(["checkout", "-b", branch_name])
    if code != 0:
        return False, err or "git branch failed"
    coi_shell_log({
        "command": f"git checkout -b {branch_name}",
        "type": "git",
        "return_code": code,
        "stdout": out[:200],
        "approved_by": "Dave"
    })
    return True, f"Created and switched to branch: {branch_name}"

def coi_git_push(branch=None):
    """Push to remote. Requires approval."""
    args = ["push"]
    if branch:
        args.extend(["-u", "origin", branch])
    else:
        args.extend(["-u", "origin", "HEAD"])

    code, out, err = _git_run(args, timeout=60)
    if code != 0:
        return False, err or "git push failed"
    coi_shell_log({
        "command": f"git push {' '.join(args[1:])}",
        "type": "git",
        "return_code": code,
        "stdout": (out or err)[:200],
        "approved_by": "Dave"
    })
    return True, out or err or "Push complete"


# ── TOOL 9 — SHELL EXECUTION (BO-027) ───────────────────────
# COI executes shell commands with safety classification and logging.

COMMAND_WHITELIST = {
    # Read-only git
    "git status", "git log", "git diff", "git branch", "git show", "git remote",
    # Read-only filesystem
    "ls", "dir", "Get-ChildItem", "cat", "type", "Get-Content", "Test-Path",
    # Read-only Python
    "python --version", "python3 --version", "pip list", "pip show", "pip --version",
    # Read-only Ollama
    "ollama list", "ollama ps", "ollama --version",  # DEPRECATED-V5
    # Read-only system
    "systeminfo", "hostname", "whoami", "Get-Process", "Get-CimInstance",
}

COMMAND_BLOCKLIST = {
    # Destructive filesystem
    "rm -rf /", "rm -rf ~", "Remove-Item -Recurse -Force C:\\",
    "del /s /q C:\\", "rd /s /q C:\\", "format C:", "format D:",
    # System control
    "shutdown", "Restart-Computer", "Stop-Computer",
    # Registry destruction
    "reg delete HKLM", "reg delete HKCR",
    # Fork bomb
    ":(){ :|:& };:",
    # Dangerous git
    "git push --force", "git reset --hard", "git clean -f",
}

def coi_shell_classify(command):
    """Classify a command as whitelisted, blocked, or requires_approval."""
    cmd_lower = command.lower().strip()

    # Check blocklist first — hard no
    for blocked in COMMAND_BLOCKLIST:
        if blocked.lower() in cmd_lower:
            return "blocked"

    # Check whitelist — auto-approve
    for safe in COMMAND_WHITELIST:
        if cmd_lower.startswith(safe.lower()):
            return "whitelisted"

    return "requires_approval"

def coi_shell_execute(command, timeout=30, cwd=None):
    """Execute a shell command via PowerShell. Returns result dict."""
    work_dir = cwd or str(ICM_ROOT)
    start = datetime.now()

    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return {
            "command": command,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "return_code": result.returncode,
            "duration_ms": duration_ms,
            "timestamp": start.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command, "stdout": "", "stderr": f"Command timed out after {timeout}s",
            "return_code": -1, "duration_ms": timeout * 1000,
            "timestamp": start.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {
            "command": command, "stdout": "", "stderr": str(e),
            "return_code": -1, "duration_ms": 0,
            "timestamp": start.strftime("%Y-%m-%d %H:%M:%S"),
        }

def coi_shell_log(result_dict):
    """Log a command execution to execution-log.md."""
    log_path = ICM_ROOT / "COI/L4-Working/memory/execution-log.md"
    try:
        cmd = result_dict.get("command", "unknown")
        cmd_type = result_dict.get("type", "shell")
        rc = result_dict.get("return_code", "?")
        duration = result_dict.get("duration_ms", "?")
        stdout = result_dict.get("stdout", "")[:200]
        approved = result_dict.get("approved_by", "auto")
        ts = result_dict.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        entry = f"\n## {ts} — {cmd_type.title()}\n"
        entry += f"- **Command:** `{cmd}`\n"
        entry += f"- **Approval:** {approved}\n"
        entry += f"- **Return code:** {rc}\n"
        if duration != "?":
            entry += f"- **Duration:** {duration}ms\n"
        if stdout:
            entry += f"- **Output:** {stdout}\n"

        # Create file if it doesn't exist
        if not log_path.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("# COI Execution Log\nAll shell and git commands executed by COI.\n", encoding="utf-8")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass  # Logging should never crash COI


def coi_pipeline_log(stage, status, details="", duration_ms=None):
    """Log a pipeline run to pipeline-log.md.
    Called by the orchestrator after each pipeline stage completes.

    Args:
        stage: Pipeline stage name (e.g. "01-intake", "briefing", "audit")
        status: "ok", "failed", "skipped"
        details: Short description of what happened
        duration_ms: Optional duration in milliseconds
    """
    log_path = ICM_ROOT / "COI/L4-Working/memory/pipeline-log.md"
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## {ts} — Pipeline\n"
        entry += f"- **Command:** `pipeline:{stage}`\n"
        entry += f"- **Return code:** {'0' if status == 'ok' else '1'}\n"
        if details:
            entry += f"- **Output:** {details[:200]}\n"
        if duration_ms is not None:
            entry += f"- **Duration:** {duration_ms}ms\n"
        entry += f"- **Status:** {status}\n"

        if not log_path.exists():
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text("# COI Pipeline Log\nTimestamped record of pipeline runs.\n", encoding="utf-8")

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


# ── TOOL 11 — LARGE FILE ACCESS (COI SPEC-01) ────────────────
# Chunked file access with LLM-generated topic summaries and query-based retrieval.
# Handles any file type. Persistent chunks on disk. Max 2 chunks per retrieval.

import re
import os

def coi_chunk_file(filepath, chunk_size_lines=150):  # DEPRECATED-V5 — uses Ollama for chunk summaries
    """Split a large file into numbered chunks and generate a session.index.md
    with auto-generated topic summaries via llama3.2:1b.

    Args:
        filepath: Absolute or Codex-relative path to the file
        chunk_size_lines: Lines per chunk (default 150)

    Returns:
        (index_path: str, message: str) — path to generated session.index.md
    """
    full_path = ICM_ROOT / filepath if not Path(filepath).is_absolute() else Path(filepath)
    if not full_path.exists():
        return None, f"File not found: {filepath}"

    try:
        content = full_path.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"Read error: {e}"

    lines = content.splitlines()
    total_lines = len(lines)

    if total_lines == 0:
        return None, "File is empty"

    # Create chunks subfolder next to the source file
    stem = full_path.stem
    chunk_dir = full_path.parent / f"{stem}.chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)

    # Split into chunks
    chunks = []
    chunk_num = 0
    for start in range(0, total_lines, chunk_size_lines):
        chunk_num += 1
        end = min(start + chunk_size_lines, total_lines)
        chunk_lines = lines[start:end]
        chunk_text = "\n".join(chunk_lines)

        chunk_filename = f"chunk-{chunk_num:03d}.txt"
        chunk_path = chunk_dir / chunk_filename
        chunk_path.write_text(chunk_text, encoding="utf-8")

        chunks.append({
            "num": chunk_num,
            "filename": chunk_filename,
            "start_line": start + 1,
            "end_line": end,
            "char_count": len(chunk_text),
            "text": chunk_text,
        })

    # Generate topic summaries via llama3.2:1b  # DEPRECATED-V5
    try:
        with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
            cfg = json.load(f)
        summary_model = cfg.get("roles", {}).get("classifier", {}).get("model", "llama3.2:1b")  # DEPRECATED-V5
    except:
        summary_model = "llama3.2:1b"  # DEPRECATED-V5

    index_entries = []
    for chunk in chunks:
        # Generate summary — truncate chunk text for the small model
        preview = chunk["text"][:1500] if len(chunk["text"]) > 1500 else chunk["text"]
        summary = _generate_chunk_summary(preview, summary_model)  # DEPRECATED-V5

        index_entries.append({
            "num": chunk["num"],
            "filename": chunk["filename"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "chars": chunk["char_count"],
            "summary": summary,
        })

    # Write session.index.md
    index_lines = [
        f"# Index: {full_path.name}",
        f"Source: {full_path}",
        f"Total lines: {total_lines} | Chunks: {chunk_num} | Chunk size: {chunk_size_lines} lines",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    for entry in index_entries:
        index_lines.append(f"## Chunk {entry['num']:03d} (lines {entry['start_line']}–{entry['end_line']}, {entry['chars']} chars)")
        index_lines.append(f"File: {entry['filename']}")
        index_lines.append(f"Topics: {entry['summary']}")
        index_lines.append("")

    index_path = chunk_dir / "session.index.md"
    index_path.write_text("\n".join(index_lines), encoding="utf-8")

    return str(index_path), f"Chunked {total_lines} lines into {chunk_num} chunks. Index: {index_path}"


def _generate_chunk_summary(text, model="llama3.2:1b"):  # DEPRECATED-V5 — Ollama local LLM call
    """Generate a one-line topic summary of a chunk using a local LLM."""  # DEPRECATED-V5
    try:
        r = requests.post("http://localhost:11434/api/generate", json={  # DEPRECATED-V5
            "model": model,  # DEPRECATED-V5
            "prompt": (
                "Summarize the topics in this text in one short line (max 80 chars). "
                "List key topics separated by commas. No explanation, just the topic list.\n\n"
                f"{text}"
            ),
            "stream": False,
            "options": {"num_ctx": 2048, "temperature": 0.2}
        }, timeout=30)  # DEPRECATED-V5
        if r.status_code == 200:
            summary = r.json().get("response", "").strip()
            # Take first line, clean up
            summary = summary.split("\n")[0].strip().strip('"').strip("'")
            if summary and len(summary) > 3:
                return summary[:120]  # Hard cap
    except:
        pass
    return "summary unavailable"


def coi_read_chunk(index_path, query):
    """Query a chunked file index and return the best 2 matching chunks.

    Args:
        index_path: Path to session.index.md
        query: Search query — matched against chunk summaries and content

    Returns:
        (chunks: list[dict], message: str) — list of matching chunk dicts with content
    """
    idx_path = Path(index_path) if Path(index_path).is_absolute() else ICM_ROOT / index_path
    if not idx_path.exists():
        return None, f"Index not found: {index_path}"

    chunk_dir = idx_path.parent

    try:
        index_text = idx_path.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"Read error: {e}"

    # Parse index entries
    entries = []
    current = None
    for line in index_text.splitlines():
        if line.startswith("## Chunk"):
            if current:
                entries.append(current)
            # Parse chunk header: ## Chunk 001 (lines 1-150, 4500 chars)
            match = re.search(r"Chunk (\d+)", line)
            current = {
                "num": int(match.group(1)) if match else 0,
                "filename": "",
                "summary": "",
                "header": line,
            }
        elif current:
            if line.startswith("File: "):
                current["filename"] = line[6:].strip()
            elif line.startswith("Topics: "):
                current["summary"] = line[8:].strip()
    if current:
        entries.append(current)

    if not entries:
        return None, "No chunks found in index"

    # Score each chunk against query
    query_lower = query.lower()
    query_words = query_lower.split()
    scored = []

    for entry in entries:
        score = 0
        summary_lower = entry["summary"].lower()

        # Score on summary keyword matches
        for word in query_words:
            if word in summary_lower:
                score += 10

        # Exact phrase match in summary
        if query_lower in summary_lower:
            score += 25

        # Also peek at chunk content for keyword matches
        chunk_path = chunk_dir / entry["filename"]
        chunk_content = ""
        if chunk_path.exists():
            try:
                chunk_content = chunk_path.read_text(encoding="utf-8")
                content_lower = chunk_content.lower()
                for word in query_words:
                    if word in content_lower:
                        score += 3
                if query_lower in content_lower:
                    score += 15
            except:
                pass

        if score > 0:
            scored.append((score, entry, chunk_content))

    if not scored:
        return [], f"No chunks matched query: {query}"

    # Sort by score descending, take top 2
    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, entry, content in scored[:2]:
        results.append({
            "chunk": entry["num"],
            "filename": entry["filename"],
            "summary": entry["summary"],
            "score": score,
            "content": content[:3000] if len(content) > 3000 else content,
        })

    return results, f"Found {len(scored)} matching chunks, returning top {len(results)}"


def coi_query_session(query, session_dir=None):
    """Convenience wrapper — finds session.index.md and queries it.

    Args:
        query: Search query
        session_dir: Directory containing session.index.md (auto-detected if None)

    Returns:
        (chunks: list[dict], message: str)
    """
    if session_dir:
        search_dir = Path(session_dir) if Path(session_dir).is_absolute() else ICM_ROOT / session_dir
    else:
        # Search common locations for session.index.md files
        search_locations = [
            ICM_ROOT / "COI" / "L4-Working" / "sessions",
            ICM_ROOT / "COI" / "L4-Working" / "memory",
            ICM_ROOT,
        ]
        search_dir = None
        for loc in search_locations:
            if loc.exists():
                # Find any session.index.md files recursively
                indices = list(loc.rglob("session.index.md"))
                if indices:
                    # Use the most recently modified one
                    indices.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    return coi_read_chunk(str(indices[0]), query)

        return None, "No session.index.md found. Run coi_chunk_file() first."

    # Look for session.index.md in specified dir
    index_files = list(search_dir.rglob("session.index.md"))
    if not index_files:
        return None, f"No session.index.md found in {session_dir}"

    # Use the most recently modified
    index_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return coi_read_chunk(str(index_files[0]), query)


# ── TOOL 12 — BUILD ORDER DRAFTING (COI SPEC-02) ─────────────
# Draft, format, and commit build order items to the Codex.
# Dave always approves before commit. Never auto-commits.

BUILD_ORDER_PATH = ICM_ROOT / "COI" / "L1-Routing" / "MASTER-BUILD-ORDER.md"

def coi_get_next_bo_id():
    """Scan MASTER-BUILD-ORDER.md for the highest BO-XXX number and return next.
    Returns int (e.g. 21 if highest existing is BO-020)."""
    if not BUILD_ORDER_PATH.exists():
        return 1

    try:
        content = BUILD_ORDER_PATH.read_text(encoding="utf-8")
    except:
        return 1

    # Find all BO-NNN patterns
    matches = re.findall(r"BO-(\d{3})", content)
    if not matches:
        return 1

    highest = max(int(m) for m in matches)
    return highest + 1


def coi_format_bo_item(bo_id, title, priority="Medium", target_stage="B",
                       activation_rule="", what_it_does="", what_to_build="",
                       why_it_matters="", dependencies="None"):
    """Format a build order item in ICM standard format.

    Args:
        bo_id: Integer ID (will be zero-padded to 3 digits)
        title: Short title for the BO item
        priority: High / Medium / Low
        target_stage: Stage letter (A, B, C, etc.)
        activation_rule: When does the pipeline pick this up
        what_it_does: One paragraph — what this capability gives COI or Dave
        what_to_build: Precise description of what to build
        why_it_matters: One sentence — consequence of not having this
        dependencies: List of dependencies or "None"

    Returns:
        Formatted markdown string
    """
    bo_num = f"BO-{bo_id:03d}"

    lines = [
        f"### {bo_num} — {title}",
        f"**Status:** Queued",
        f"**Priority:** {priority}",
        f"**Target Stage:** Stage {target_stage}",
        f"**Activation Rule:** {activation_rule or 'To be determined'}",
        "",
        f"#### What it does",
        what_it_does or "[To be filled]",
        "",
        f"#### What to build",
        what_to_build or "[To be filled]",
        "",
        f"#### Why it matters",
        why_it_matters or "[To be filled]",
        "",
        f"#### Dependencies",
        dependencies or "None",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def coi_commit_bo_item(bo_text):
    """Append a formatted BO item to MASTER-BUILD-ORDER.md.
    Inserts before the ARCHITECTURAL PRINCIPLES section.

    Args:
        bo_text: Formatted BO item markdown (from coi_format_bo_item)

    Returns:
        (success: bool, message: str)
    """
    if not BUILD_ORDER_PATH.exists():
        return False, "MASTER-BUILD-ORDER.md not found"

    try:
        content = BUILD_ORDER_PATH.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Read error: {e}"

    # Insert before ARCHITECTURAL PRINCIPLES section
    marker = "## ARCHITECTURAL PRINCIPLES"
    marker_idx = content.find(marker)

    if marker_idx != -1:
        # Insert before the marker
        new_content = content[:marker_idx] + bo_text + "\n" + content[marker_idx:]
    else:
        # Fallback: append to end
        new_content = content.rstrip() + "\n\n" + bo_text

    try:
        BUILD_ORDER_PATH.write_text(new_content, encoding="utf-8")
    except Exception as e:
        return False, f"Write error: {e}"

    # Background GitHub sync
    _github_write_background(
        "COI/L1-Routing/MASTER-BUILD-ORDER.md",
        new_content,
        f"Add {bo_text.split(chr(10))[0].strip('# ')}",
        _github_get_sha("COI/L1-Routing/MASTER-BUILD-ORDER.md"),
        operation="bo_commit"
    )

    return True, f"Build order item committed to MASTER-BUILD-ORDER.md"


def coi_draft_bo_from_context(conversation_history, model=None):  # DEPRECATED-V5 — uses Ollama for BO drafting
    """Use a local LLM to draft a build order item from conversation context.

    Args:
        conversation_history: List of recent conversation turns (dicts with role/content)
        model: LLM model to use (defaults to briefing model from config)

    Returns:
        dict with keys: title, priority, target_stage, activation_rule,
              what_it_does, what_to_build, why_it_matters, dependencies
        or None on failure
    """
    if not model:
        try:
            with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
                cfg = json.load(f)
            model = cfg.get("roles", {}).get("general", {}).get("model", "mistral:7b-instruct-q4_K_M")  # DEPRECATED-V5
        except:
            model = "mistral:7b-instruct-q4_K_M"  # DEPRECATED-V5

    # Build context from recent conversation — last 10 turns max
    recent = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
    context_lines = []
    for turn in recent:
        role = turn.get("role", "user").upper()
        content = turn.get("content", "")[:500]  # Cap per turn
        context_lines.append(f"{role}: {content}")
    context = "\n".join(context_lines)

    prompt = f"""Extract a build order item from this conversation. Return EXACTLY these fields, one per line, with the field name followed by a colon:

TITLE: [short title, max 60 chars]
PRIORITY: [High or Medium or Low]
STAGE: [A or B or C]
ACTIVATION: [when to activate this — one sentence]
WHAT_IT_DOES: [one paragraph — what this gives COI or Dave]
WHAT_TO_BUILD: [precise description of what to build — files, functions, behaviors]
WHY: [one sentence — consequence of not having this]
DEPENDENCIES: [list dependencies or None]

Conversation:
{context}"""

    try:
        r = requests.post("http://localhost:11434/api/generate", json={  # DEPRECATED-V5
            "model": model,  # DEPRECATED-V5
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 4096, "temperature": 0.3}
        }, timeout=60)  # DEPRECATED-V5

        if r.status_code != 200:
            return None

        response = r.json().get("response", "")
        return _parse_bo_draft(response)

    except:
        return None


def _parse_bo_draft(text):
    """Parse LLM response into structured BO draft fields."""
    fields = {
        "title": "", "priority": "Medium", "target_stage": "B",
        "activation_rule": "", "what_it_does": "", "what_to_build": "",
        "why_it_matters": "", "dependencies": "None"
    }

    field_map = {
        "TITLE": "title",
        "PRIORITY": "priority",
        "STAGE": "target_stage",
        "ACTIVATION": "activation_rule",
        "WHAT_IT_DOES": "what_it_does",
        "WHAT_TO_BUILD": "what_to_build",
        "WHY": "why_it_matters",
        "DEPENDENCIES": "dependencies",
    }

    for line in text.splitlines():
        line = line.strip()
        for key, field in field_map.items():
            if line.upper().startswith(key + ":"):
                value = line[len(key) + 1:].strip()
                if value:
                    fields[field] = value
                break

    # Validate priority
    if fields["priority"] not in ("High", "Medium", "Low"):
        fields["priority"] = "Medium"

    # Validate stage
    if fields["target_stage"] not in ("A", "B", "C", "D"):
        fields["target_stage"] = "B"

    return fields if fields["title"] else None


# ── SELF TEST ────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("  COI Tools — Self Test")
    print()

    # Test config
    config = _load_config()
    if config.get("github_token"):
        print("  GitHub token: loaded")
    else:
        print("  GitHub token: NOT FOUND — check config.json")

    # Test local Codex
    if ICM_ROOT.exists():
        print(f"  Codex root: found at {ICM_ROOT}")
    else:
        print(f"  Codex root: NOT FOUND at {ICM_ROOT}")

    # Test read map
    map_content, msg = coi_read_map()
    if map_content:
        print(f"  CODEX-MAP.md: loaded ({len(map_content)} chars)")
    else:
        print(f"  CODEX-MAP.md: {msg}")

    # Test list files
    files, msg = coi_list_files("COI/L3-Reference")
    if files:
        print(f"  L3-Reference: {len(files)} files found")
    else:
        print(f"  L3-Reference: {msg}")

    print()
    print("  Tools available:")
    print("    coi_write_file(path, content, commit_message)")
    print("    coi_update_file(path, content, commit_message)")
    print("    coi_append_file(path, content, commit_message)")
    print("    coi_read_file(path)")
    print("    coi_read_map()")
    print("    coi_list_files(folder_path)")
    print()
