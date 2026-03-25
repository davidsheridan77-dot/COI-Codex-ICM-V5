"""
coi_dropoff_worker.py — Background queue processor for the Drop-Off Panel.
Processes queued items through local LLMs, producing summaries.
Coordinates VRAM with the foreground chat model.
"""

import json
import time
from datetime import datetime
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ICM_ROOT = Path("K:/Coi Codex/COI-Codex-ICM")
QUEUE_PATH = ICM_ROOT / "inbox" / "dropoff-queue.json"
SUMMARIES_DIR = ICM_ROOT / "inbox" / "summaries"
ORIGINALS_DIR = ICM_ROOT / "inbox" / "originals"
MODEL_CONFIG_PATH = ICM_ROOT / "scripts" / "model-config.json"  # DEPRECATED-V5

# ---------------------------------------------------------------------------
# Drop-Off Protection Tags (SPEC-05 — Constitutional Integrity)
# Chunking via coi_chunk_file() is permitted for large files — chunking is
# not content modification. All chunks must preserve original content fully.
# What is prohibited: summarizing, trimming, or reinterpreting content in
# place of delivering it in full.
# ---------------------------------------------------------------------------
DROPOFF_OPEN_TAG = "[DROP-OFF-ORIGIN: verified]"
DROPOFF_CLOSE_TAG = "[END-DROP-OFF-ORIGIN]"
OLLAMA_BASE = "http://localhost:11434"  # DEPRECATED-V5

# ---------------------------------------------------------------------------
# Queue I/O
# ---------------------------------------------------------------------------

def load_queue():
    """Load the drop-off queue from disk."""
    if QUEUE_PATH.exists():
        try:
            return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_queue(queue):
    """Persist the drop-off queue to disk."""
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(queue, indent=2), encoding="utf-8")


def get_orchestrator_model():  # DEPRECATED-V5
    """Read the orchestrator model from model-config.json."""  # DEPRECATED-V5
    try:
        with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
            cfg = json.load(f)
        return cfg.get("roles", {}).get("orchestrator", {}).get("model", "llama3.1:8b")  # DEPRECATED-V5
    except Exception:
        return "llama3.1:8b"  # DEPRECATED-V5


# ---------------------------------------------------------------------------
# DropOffWorker — persistent background processor
# ---------------------------------------------------------------------------
class DropOffWorker(QThread):
    """
    Background worker that processes the drop-off queue.
    Runs continuously, polling every 5 seconds for queued items.
    Coordinates VRAM: evicts foreground model, processes, reloads.
    """

    item_started = pyqtSignal(str)        # item id
    item_completed = pyqtSignal(str, str)  # item id, summary
    item_failed = pyqtSignal(str, str)     # item id, error message
    queue_empty = pyqtSignal()

    def __init__(self, chat_active_flag=None, foreground_model="llama3.1:8b", parent=None):  # DEPRECATED-V5
        super().__init__(parent)
        self._running = True
        self._chat_active = chat_active_flag  # callable that returns bool
        self._foreground_model = foreground_model  # DEPRECATED-V5

    def stop(self):
        self._running = False

    # -- VRAM management ---------------------------------------------------

    def _evict_all_models(self):  # DEPRECATED-V5
        """Unload all models from VRAM."""  # DEPRECATED-V5
        try:
            ps = requests.get(f"{OLLAMA_BASE}/api/ps", timeout=10).json()  # DEPRECATED-V5
            for m in ps.get("models", []):
                name = m.get("name", "")
                if name:
                    requests.post(f"{OLLAMA_BASE}/api/generate",  # DEPRECATED-V5
                                  json={"model": name, "keep_alive": 0}, timeout=10)  # DEPRECATED-V5
        except Exception:
            pass

    def _reload_foreground(self):  # DEPRECATED-V5
        """Reload the foreground chat model and pin it."""  # DEPRECATED-V5
        try:
            requests.post(f"{OLLAMA_BASE}/api/generate", json={  # DEPRECATED-V5
                "model": self._foreground_model,  # DEPRECATED-V5
                "prompt": "",
                "keep_alive": -1
            }, timeout=30)
        except Exception:
            pass

    # -- Content reading ---------------------------------------------------

    def _read_content(self, item):
        """Extract text content from a queue item."""
        source_type = item.get("source_type", "text")

        if source_type == "text":
            return item.get("raw_text", "")

        if source_type in ("file", "screenshot"):
            path = item.get("source_path")
            if not path:
                return item.get("raw_text", "")
            p = Path(path)
            if not p.exists():
                return f"[File not found: {path}]"

            suffix = p.suffix.lower()
            if suffix in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
                return f"[Image: {p.name}, {p.stat().st_size:,} bytes — image analysis not yet supported, metadata only]"

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                # Limit to prevent overwhelming the LLM
                if len(content) > 15000:
                    content = content[:15000] + "\n\n[... truncated at 15,000 chars ...]"
                return content
            except Exception as e:
                return f"[Could not read {p.name}: {e}]"

        return item.get("raw_text", "")

    # -- Chunking ----------------------------------------------------------

    def _chunk_content(self, content, chunk_size=8000):
        """Split large content into chunks on paragraph boundaries."""
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        remaining = content
        while remaining:
            if len(remaining) <= chunk_size:
                chunks.append(remaining)
                break
            split_at = remaining.rfind("\n\n", 0, chunk_size)
            if split_at < chunk_size // 2:
                split_at = remaining.rfind("\n", 0, chunk_size)
            if split_at < chunk_size // 2:
                split_at = chunk_size
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip()
        return chunks

    # -- Summarization -----------------------------------------------------

    def _summarize(self, content, filename, model):  # DEPRECATED-V5
        """Send content to LLM for summarization. Returns summary string."""  # DEPRECATED-V5
        chunks = self._chunk_content(content)
        all_summaries = []

        for i, chunk in enumerate(chunks):
            prompt = f"""Summarize this content concisely. Extract:
1. A 2-3 sentence overview
2. Key points as bullet list (max 8)
3. Any decisions, action items, or important details

Source: {filename}
{f'(Chunk {i+1}/{len(chunks)})' if len(chunks) > 1 else ''}

CONTENT:
{chunk}

Respond with the summary only. Be concise."""

            try:
                r = requests.post(f"{OLLAMA_BASE}/api/generate", json={  # DEPRECATED-V5
                    "model": model,  # DEPRECATED-V5
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_ctx": 4096}
                }, timeout=180)
                r.raise_for_status()
                summary = r.json().get("response", "").strip()
                if summary:
                    all_summaries.append(summary)
            except Exception as e:
                all_summaries.append(f"[Error processing chunk {i+1}: {e}]")

        if len(all_summaries) == 1:
            return all_summaries[0]

        # Merge multiple chunk summaries
        if not all_summaries:
            return "[No summary generated]"

        merged = "\n\n---\n\n".join(all_summaries)

        # If we had multiple chunks, do a final merge pass
        if len(all_summaries) > 1:
            merge_prompt = f"""Combine these partial summaries into one cohesive summary.
Keep it concise — 2-3 sentence overview plus key bullet points.

{merged}

Respond with the merged summary only."""

            try:
                r = requests.post(f"{OLLAMA_BASE}/api/generate", json={  # DEPRECATED-V5
                    "model": model,  # DEPRECATED-V5
                    "prompt": merge_prompt,
                    "stream": False,
                    "options": {"num_ctx": 4096}
                }, timeout=120)
                r.raise_for_status()
                final = r.json().get("response", "").strip()
                if final:
                    return final
            except Exception:
                pass

        return merged

    # -- Main loop ---------------------------------------------------------

    def run(self):
        """Main processing loop. Polls queue every 5 seconds."""
        while self._running:
            queue = load_queue()
            queued_items = [item for item in queue if item.get("status") == "queued"]

            if not queued_items:
                self.queue_empty.emit()
                time.sleep(5)
                continue

            # Wait if chat is active
            if self._chat_active and self._chat_active():
                time.sleep(3)
                continue

            item = queued_items[0]
            item_id = item["id"]
            self.item_started.emit(item_id)

            # Update status in queue
            for q in queue:
                if q["id"] == item_id:
                    q["status"] = "processing"
                    break
            save_queue(queue)

            try:
                model = get_orchestrator_model()  # DEPRECATED-V5
                content = self._read_content(item)

                if not content or len(content.strip()) < 10:
                    raise ValueError("No content to process")

                filename = item.get("display_name", "unknown")

                # ── SPEC-05: Save original content verbatim ──────────
                ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
                original_file = ORIGINALS_DIR / f"{item_id}.md"
                original_file.write_text(
                    f"{DROPOFF_OPEN_TAG}\n"
                    f"Source: {filename}\n"
                    f"Received: {datetime.now().isoformat()}\n"
                    f"Type: {item.get('source_type', 'text')}\n"
                    f"---\n"
                    f"{content}\n"
                    f"{DROPOFF_CLOSE_TAG}\n",
                    encoding="utf-8"
                )

                # ── Generate summary for index preview only ──────────
                self._evict_all_models()  # DEPRECATED-V5
                summary = self._summarize(content, filename, model)  # DEPRECATED-V5

                SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
                summary_file = SUMMARIES_DIR / f"{item_id}.md"
                summary_file.write_text(
                    f"# Drop-Off Summary: {filename}\n"
                    f"Processed: {datetime.now().isoformat()}\n"
                    f"Model: {model}\n\n"
                    f"{summary}\n",
                    encoding="utf-8"
                )

                # Update queue — store both original and summary paths
                queue = load_queue()
                for q in queue:
                    if q["id"] == item_id:
                        q["status"] = "done"
                        q["processed_at"] = datetime.now().isoformat()
                        q["summary"] = summary[:300]  # Compact version for index
                        q["summary_file"] = str(summary_file)
                        q["original_file"] = str(original_file)
                        break
                save_queue(queue)

                # Reload foreground model
                self._reload_foreground()  # DEPRECATED-V5

                self.item_completed.emit(item_id, summary[:200])

            except Exception as e:
                # Mark failed
                queue = load_queue()
                for q in queue:
                    if q["id"] == item_id:
                        q["status"] = "failed"
                        q["error"] = str(e)[:200]
                        break
                save_queue(queue)

                # Try to reload foreground model even on failure
                self._reload_foreground()  # DEPRECATED-V5

                self.item_failed.emit(item_id, str(e)[:200])

            # Brief pause between items
            time.sleep(2)
