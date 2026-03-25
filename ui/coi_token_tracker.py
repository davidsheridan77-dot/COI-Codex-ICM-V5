"""
COI Token Tracker — singleton token usage tracker with spike detection.
Tracks per-request token counts, calculates rolling averages,
detects anomalous usage patterns, and logs spikes.
"""

import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import deque

from PyQt6.QtCore import QObject, pyqtSignal


CONFIG_PATH = Path("K:/Coi Codex/COI-Codex-ICM/config/token_config.json")
SPIKE_LOG_PATH = Path("K:/Coi Codex/COI-Codex-ICM/logs/token_spikes.json")

DEFAULT_CONFIG = {
    "prompt_spike_multiplier": 2.0,
    "completion_spike_multiplier": 2.0,
    "max_tokens_per_min_warning": 500,
    "session_warning_watermark": 25000,
    "session_critical_watermark": 100000,
    "completion_ceiling_flag": True,
    "context_bloat_detection": True,
    "retry_loop_detection": True,
    "ratio_flip_detection": True,
    "spike_log_max_entries": 500,
    "spike_alert_clear_time": 30,
}


class TokenTracker(QObject):
    """Singleton token tracker with spike detection for COI Desktop."""

    spike_detected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._initialized = True

        # Rolling window size
        self._window_size = 20

        # Request history for rolling averages
        self._prompt_history = deque(maxlen=self._window_size)
        self._completion_history = deque(maxlen=self._window_size)

        # Timestamps for tokens-per-minute calculation (sliding 60s window)
        self._recent_tokens = deque()  # (timestamp, total_tokens)

        # Session totals
        self._session_prompt_total = 0
        self._session_completion_total = 0
        self._session_request_count = 0
        self._session_spike_count = 0
        self._session_start = time.time()

        # Last request token counts
        self._last_prompt_tokens = 0
        self._last_completion_tokens = 0

        # Last 3 request prompt sizes for bloat trend detection
        self._last_3_prompts = deque(maxlen=3)

        # Prompt hash tracking for retry loop detection
        self._recent_hashes = deque()  # (timestamp, hash)

        # Historical completion/prompt ratio tracking
        self._ratio_history = deque(maxlen=self._window_size)

        # Spike counter for generating spike IDs
        self._spike_id_counter = 0

        # Load config
        self._config = self._load_config()

        # Load existing spike log
        self._spike_log = self._load_spike_log()

    # ------------------------------------------------------------------ config

    def _load_config(self):
        """Load config from file, falling back to defaults."""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                # Merge with defaults so new keys are always present
                merged = dict(DEFAULT_CONFIG)
                merged.update(loaded)
                return merged
            except (json.JSONDecodeError, OSError):
                return dict(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    def save_config(self):
        """Write current config (or defaults) to disk."""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    # -------------------------------------------------------------- spike log

    def _load_spike_log(self):
        """Load existing spike log from disk."""
        if SPIKE_LOG_PATH.exists():
            try:
                with open(SPIKE_LOG_PATH, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                if isinstance(entries, list):
                    max_entries = self._config.get("spike_log_max_entries", 500)
                    return entries[-max_entries:]
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _save_spike_log(self):
        """Persist spike log to disk, enforcing max entries."""
        SPIKE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        max_entries = self._config.get("spike_log_max_entries", 500)
        trimmed = self._spike_log[-max_entries:]
        with open(SPIKE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(trimmed, f, indent=2)

    # --------------------------------------------------------- rolling helpers

    def _rolling_avg_prompt(self):
        if not self._prompt_history:
            return 0.0
        return sum(self._prompt_history) / len(self._prompt_history)

    def _rolling_avg_completion(self):
        if not self._completion_history:
            return 0.0
        return sum(self._completion_history) / len(self._completion_history)

    def _historical_ratio(self):
        """Average completion/prompt ratio over the rolling window."""
        if not self._ratio_history:
            return 0.0
        return sum(self._ratio_history) / len(self._ratio_history)

    # -------------------------------------------------------- public interface

    def tokens_per_minute(self):
        """Tokens per minute based on a sliding 60-second window."""
        now = time.time()
        cutoff = now - 60.0
        # Purge old entries
        while self._recent_tokens and self._recent_tokens[0][0] < cutoff:
            self._recent_tokens.popleft()
        if not self._recent_tokens:
            return 0.0
        total = sum(t for _, t in self._recent_tokens)
        # Scale to a full minute even if window is shorter
        span = now - self._recent_tokens[0][0]
        if span < 1.0:
            return float(total)
        return total / (span / 60.0)

    def session_stats(self):
        """Return a dict summarising the current session."""
        elapsed = time.time() - self._session_start
        return {
            "total_prompt": self._session_prompt_total,
            "total_completion": self._session_completion_total,
            "total_tokens": self._session_prompt_total + self._session_completion_total,
            "request_count": self._session_request_count,
            "avg_prompt": (
                self._session_prompt_total / self._session_request_count
                if self._session_request_count
                else 0.0
            ),
            "avg_completion": (
                self._session_completion_total / self._session_request_count
                if self._session_request_count
                else 0.0
            ),
            "last_prompt": self._last_prompt_tokens,
            "last_completion": self._last_completion_tokens,
            "spike_count": self._session_spike_count,
            "tokens_per_minute": self.tokens_per_minute(),
            "session_elapsed_seconds": round(elapsed, 1),
        }

    # --------------------------------------------------------------- recorder

    def record(self, prompt_tokens, completion_tokens, model, stage, max_tokens):
        """Record a request and run spike detection.

        Args:
            prompt_tokens:     Number of prompt/input tokens used.
            completion_tokens: Number of completion/output tokens used.
            model:             Model identifier string.
            stage:             Pipeline stage label.
            max_tokens:        The max_tokens value sent in the request.
        """
        now = time.time()

        # Compute rolling averages BEFORE updating history (compare against prior)
        avg_prompt = self._rolling_avg_prompt()
        avg_completion = self._rolling_avg_completion()
        hist_ratio = self._historical_ratio()

        # --- Run spike detection ---
        trigger_flags = []

        # (a) Prompt spike
        if avg_prompt > 0 and prompt_tokens > avg_prompt * self._config["prompt_spike_multiplier"]:
            trigger_flags.append("prompt_spike")

        # (b) Completion spike
        if avg_completion > 0 and completion_tokens > avg_completion * self._config["completion_spike_multiplier"]:
            trigger_flags.append("completion_spike")

        # (c) Tokens per minute exceeded
        # Temporarily add current tokens for the check
        total_this_request = prompt_tokens + completion_tokens
        self._recent_tokens.append((now, total_this_request))
        tpm = self.tokens_per_minute()
        if tpm > self._config["max_tokens_per_min_warning"]:
            trigger_flags.append("tokens_per_minute_exceeded")

        # (d) Completion ceiling hit
        if self._config["completion_ceiling_flag"] and max_tokens and max_tokens > 0:
            if completion_tokens >= max_tokens * 0.95:
                trigger_flags.append("completion_ceiling_hit")

        # (e) Context bloat trend — prompt growing across last 3 sequential requests
        if self._config["context_bloat_detection"] and len(self._last_3_prompts) == 3:
            p = list(self._last_3_prompts)
            if p[0] < p[1] < p[2] < prompt_tokens:
                trigger_flags.append("context_bloat_trend")

        # (f) Retry loop — same prompt hash seen within 60 seconds
        if self._config["retry_loop_detection"]:
            prompt_hash = hashlib.md5(
                f"{prompt_tokens}:{model}:{stage}".encode()
            ).hexdigest()
            cutoff = now - 60.0
            # Purge old hashes
            while self._recent_hashes and self._recent_hashes[0][0] < cutoff:
                self._recent_hashes.popleft()
            for ts, h in self._recent_hashes:
                if h == prompt_hash:
                    trigger_flags.append("retry_loop_detected")
                    break
            self._recent_hashes.append((now, prompt_hash))

        # (g) Ratio flip — completion/prompt ratio > 3x historical ratio
        if self._config["ratio_flip_detection"] and prompt_tokens > 0 and hist_ratio > 0:
            current_ratio = completion_tokens / prompt_tokens
            if current_ratio > hist_ratio * 3.0:
                trigger_flags.append("ratio_flip_rambling")

        # (h) Session watermark checks
        session_total_after = (
            self._session_prompt_total
            + self._session_completion_total
            + total_this_request
        )
        if session_total_after >= self._config["session_critical_watermark"]:
            trigger_flags.append("session_critical_watermark")
        elif session_total_after >= self._config["session_warning_watermark"]:
            trigger_flags.append("session_warning_watermark")

        # --- Update history AFTER detection ---
        self._prompt_history.append(prompt_tokens)
        self._completion_history.append(completion_tokens)
        self._last_3_prompts.append(prompt_tokens)
        if prompt_tokens > 0:
            self._ratio_history.append(completion_tokens / prompt_tokens)

        # Update session totals
        self._session_prompt_total += prompt_tokens
        self._session_completion_total += completion_tokens
        self._session_request_count += 1
        self._last_prompt_tokens = prompt_tokens
        self._last_completion_tokens = completion_tokens

        # --- Handle spike if any triggers fired ---
        if trigger_flags:
            self._session_spike_count += 1
            self._spike_id_counter += 1

            # Severity
            num_triggers = len(trigger_flags)
            if num_triggers >= 4:
                severity = "SEVERE"
            elif num_triggers >= 2:
                severity = "MODERATE"
            else:
                severity = "MILD"

            # Percent above average
            if avg_prompt > 0:
                percent_above = round(
                    ((prompt_tokens - avg_prompt) / avg_prompt) * 100.0, 1
                )
            else:
                percent_above = 0.0

            spike_entry = {
                "spike_id": f"spike-{self._spike_id_counter:04d}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "pipeline_stage": stage,
                "severity": severity,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "rolling_avg_prompt": round(avg_prompt, 1),
                "rolling_avg_completion": round(avg_completion, 1),
                "trigger_flags": trigger_flags,
                "percent_above_avg": percent_above,
                "last_3_request_sizes": list(self._last_3_prompts),
                "notes": self._build_notes(trigger_flags, severity),
            }

            # Append to log and persist
            max_entries = self._config.get("spike_log_max_entries", 500)
            self._spike_log.append(spike_entry)
            if len(self._spike_log) > max_entries:
                self._spike_log = self._spike_log[-max_entries:]
            self._save_spike_log()

            # Emit signal
            self.spike_detected.emit(spike_entry)

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _build_notes(trigger_flags, severity):
        """Generate a human-readable notes string for a spike entry."""
        parts = []
        flag_descriptions = {
            "prompt_spike": "Prompt tokens exceeded rolling average threshold",
            "completion_spike": "Completion tokens exceeded rolling average threshold",
            "tokens_per_minute_exceeded": "Tokens per minute exceeded configured warning limit",
            "completion_ceiling_hit": "Completion tokens hit 95%+ of max_tokens ceiling",
            "context_bloat_trend": "Prompt size growing across consecutive requests",
            "retry_loop_detected": "Same prompt hash seen within 60 seconds — possible retry loop",
            "ratio_flip_rambling": "Completion/prompt ratio far above historical average",
            "session_warning_watermark": "Session total tokens crossed warning watermark",
            "session_critical_watermark": "Session total tokens crossed critical watermark",
        }
        for flag in trigger_flags:
            desc = flag_descriptions.get(flag, flag)
            parts.append(desc)
        return f"[{severity}] {'; '.join(parts)}."
