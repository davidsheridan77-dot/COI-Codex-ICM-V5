"""
coi_tools_worker.py — QThread-based async workers for COI Desktop.
Keeps the UI responsive by offloading blocking operations to background threads.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
OLLAMA_BASE = "http://localhost:11434"  # DEPRECATED-V5
LOG_DIR = Path("K:/Coi Codex/COI-Codex-ICM/logs")
MODEL_LOAD_TIMES_FILE = LOG_DIR / "model_load_times.json"
DEFAULT_TIMEOUT = 120  # seconds


# ---------------------------------------------------------------------------
# OllamaQueryWorker — generic POST to Ollama API
# ---------------------------------------------------------------------------
class OllamaQueryWorker(QThread):  # DEPRECATED-V5
    """Send a POST request to an Ollama endpoint and return the response."""  # DEPRECATED-V5

    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url: str, payload: dict, parent=None):
        super().__init__(parent)
        self.url = url  # DEPRECATED-V5
        self.payload = payload

    def run(self):  # DEPRECATED-V5
        try:
            resp = requests.post(self.url, json=self.payload, timeout=DEFAULT_TIMEOUT)  # DEPRECATED-V5
            resp.raise_for_status()
            self.result_ready.emit(resp.text)
        except requests.Timeout:
            self.error_occurred.emit(f"Timeout reaching {self.url}")
        except Exception as e:
            self.error_occurred.emit(f"OllamaQueryWorker error: {e}")  # DEPRECATED-V5


# ---------------------------------------------------------------------------
# OllamaGetWorker — generic GET from Ollama API
# ---------------------------------------------------------------------------
class OllamaGetWorker(QThread):  # DEPRECATED-V5
    """Send a GET request to an Ollama endpoint and return the response."""  # DEPRECATED-V5

    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url  # DEPRECATED-V5

    def run(self):  # DEPRECATED-V5
        try:
            resp = requests.get(self.url, timeout=DEFAULT_TIMEOUT)  # DEPRECATED-V5
            resp.raise_for_status()
            self.result_ready.emit(resp.text)
        except requests.Timeout:
            self.error_occurred.emit(f"Timeout reaching {self.url}")
        except Exception as e:
            self.error_occurred.emit(f"OllamaGetWorker error: {e}")  # DEPRECATED-V5


# ---------------------------------------------------------------------------
# SubprocessWorker — run a shell command and capture output
# ---------------------------------------------------------------------------
class SubprocessWorker(QThread):
    """Run a subprocess command list and emit its stdout/stderr."""

    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, cmd_list: list, parent=None):
        super().__init__(parent)
        self.cmd_list = cmd_list

    def run(self):
        try:
            result = subprocess.run(
                self.cmd_list,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            self.result_ready.emit(output)
        except subprocess.TimeoutExpired:
            self.error_occurred.emit(f"Subprocess timed out: {' '.join(self.cmd_list)}")
        except Exception as e:
            self.error_occurred.emit(f"SubprocessWorker error: {e}")


# ---------------------------------------------------------------------------
# FileWalkerWorker — walk a directory tree matching a glob pattern
# ---------------------------------------------------------------------------
class FileWalkerWorker(QThread):
    """Walk a directory and return files matching the given glob pattern."""

    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, path: str, pattern: str = "*", parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.pattern = pattern

    def run(self):
        try:
            if not self.path.exists():
                self.error_occurred.emit(f"Path does not exist: {self.path}")
                return

            matches = sorted(self.path.rglob(self.pattern))
            lines = [str(p) for p in matches]
            self.result_ready.emit(
                f"Found {len(lines)} file(s) matching '{self.pattern}':\n"
                + "\n".join(lines)
            )
        except Exception as e:
            self.error_occurred.emit(f"FileWalkerWorker error: {e}")


# ---------------------------------------------------------------------------
# LLMToolWorker — full unload / load / run cycle for a tool model
# ---------------------------------------------------------------------------
class LLMToolWorker(QThread):  # DEPRECATED-V5
    """
    Manages the complete model lifecycle for a tool invocation:
      1. Query running models via /api/ps
      2. Evict each loaded model (keep_alive=0)
      3. Run the requested model + prompt via /api/chat
      4. Record load timing to logs/model_load_times.json
    """  # DEPRECATED-V5

    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, model: str, prompt: str, parent=None):
        super().__init__(parent)
        self.model = model  # DEPRECATED-V5
        self.prompt = prompt

    # -- internal helpers --------------------------------------------------

    def _get_loaded_models(self) -> list[str]:  # DEPRECATED-V5
        """Return list of model names currently loaded in Ollama."""  # DEPRECATED-V5
        resp = requests.get(f"{OLLAMA_BASE}/api/ps", timeout=30)  # DEPRECATED-V5
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    def _evict_model(self, name: str):  # DEPRECATED-V5
        """Unload a single model from VRAM."""  # DEPRECATED-V5
        requests.post(  # DEPRECATED-V5
            f"{OLLAMA_BASE}/api/generate",  # DEPRECATED-V5
            json={"model": name, "keep_alive": 0},  # DEPRECATED-V5
            timeout=30,
        )

    def _record_load_time(self, model: str, seconds: float):
        """Append a load-time entry to the JSON log file."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        entries = []
        if MODEL_LOAD_TIMES_FILE.exists():
            try:
                entries = json.loads(MODEL_LOAD_TIMES_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                entries = []

        entries.append({
            "model": model,
            "load_seconds": round(seconds, 3),
            "timestamp": datetime.now().isoformat(),
        })

        MODEL_LOAD_TIMES_FILE.write_text(
            json.dumps(entries, indent=2), encoding="utf-8"
        )

    # -- main thread entry -------------------------------------------------

    def run(self):  # DEPRECATED-V5
        try:
            # Step 1: find currently loaded models
            loaded = self._get_loaded_models()  # DEPRECATED-V5

            # Step 2: evict every loaded model to free VRAM
            for name in loaded:
                self._evict_model(name)  # DEPRECATED-V5

            # Step 3: run the requested model + prompt
            load_start = time.time()
            resp = requests.post(  # DEPRECATED-V5
                f"{OLLAMA_BASE}/api/chat",  # DEPRECATED-V5
                json={
                    "model": self.model,  # DEPRECATED-V5
                    "messages": [{"role": "user", "content": self.prompt}],
                    "stream": False,
                    "options": {"num_ctx": 4096},
                },
                timeout=300,
            )
            resp.raise_for_status()
            load_elapsed = time.time() - load_start

            # Step 4: emit the response text
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            self.result_ready.emit(content)

            # Step 6: record model load time
            self._record_load_time(self.model, load_elapsed)

        except requests.Timeout:
            self.error_occurred.emit(f"LLMToolWorker timeout for model {self.model}")  # DEPRECATED-V5
        except Exception as e:
            self.error_occurred.emit(f"LLMToolWorker error: {e}")  # DEPRECATED-V5
