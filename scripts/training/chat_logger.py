"""
chat_logger.py
COI LLM Optimization Program — Stage 1: Collect
Logs every Dave↔COI exchange to dataset/chat-log.jsonl
Drop into scripts/training/ and import into main COI chat pipeline
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

# --- Config ---
LOG_PATH = Path(r"K:\Coi Codex\COI-Codex-ICM-V5\COI\L4-Working\training\dataset\chat-log.jsonl")
RULES_PATH = Path(r"K:\Coi Codex\COI-Codex-ICM-V5\COI\L4-Working\training\rules\compression-rules.json")


class ChatLogger:
    def __init__(self):
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.rules = self._load_rules()
        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S")

    def _load_rules(self) -> list:
        if RULES_PATH.exists():
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [r for r in data.get("rules", []) if r.get("status") in ("active", "trial")]
        return []

    def compress(self, text: str) -> str:
        compressed = text
        for rule in self.rules:
            compressed = compressed.replace(rule["pattern"], rule["replacement"])
        # Strip filler words
        fillers = ["could you", "would you", "i was wondering", "just", "kind of", "sort of"]
        for f in fillers:
            compressed = compressed.replace(f, "")
        # Collapse extra whitespace
        import re
        compressed = re.sub(r"\s+", " ", compressed).strip()
        return compressed

    def _count_tokens(self, text: str) -> int:
        # Rough estimate: 1 token ≈ 4 chars
        return max(1, len(text) // 4)

    def _entry_id(self, raw_input: str, timestamp: float) -> str:
        h = hashlib.md5(f"{raw_input}{timestamp}".encode()).hexdigest()[:8]
        return f"{self.session_id}-{h}"

    def log(
        self,
        raw_input: str,
        response: str,
        model: str = "gemma3:4b",
        source: str = "dave",
        quality_score: float = -1.0,
        notes: str = ""
    ):
        """
        Call this after every COI exchange.

        raw_input     — what Dave typed (unmodified)
        response      — what COI returned
        model         — which Ollama model responded
        source        — 'dave' for real sessions, 'simulator' for synthetic
        quality_score — auto-scorer fills this in (-1 = unscored)
        notes         — optional audit flag
        """
        compressed = self.compress(raw_input)
        ts = time.time()

        entry = {
            "id":               self._entry_id(raw_input, ts),
            "session_id":       self.session_id,
            "timestamp":        datetime.fromtimestamp(ts).isoformat(),
            "source":           source,
            "model":            model,
            "raw_input":        raw_input,
            "compressed_input": compressed,
            "compression_ratio": round(len(compressed) / max(len(raw_input), 1), 3),
            "response":         response,
            "tokens_raw":       self._count_tokens(raw_input),
            "tokens_compressed":self._count_tokens(compressed),
            "tokens_response":  self._count_tokens(response),
            "quality_score":    quality_score,
            "notes":            notes
        }

        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        return entry


# --- Standalone test ---
if __name__ == "__main__":
    logger = ChatLogger()

    test_input = "can you please check the forge queue and tell me what build order tasks are pending"
    test_response = "Forge queue has 3 pending tasks: intake pipeline test, P3 mobile spec, benchmark set build."

    entry = logger.log(
        raw_input=test_input,
        response=test_response,
        model="gemma3:4b",
        source="dave"
    )

    print("Logged entry:")
    print(f"  Raw:        {entry['raw_input']}")
    print(f"  Compressed: {entry['compressed_input']}")
    print(f"  Ratio:      {entry['compression_ratio']}")
    print(f"  Tokens raw: {entry['tokens_raw']} → compressed: {entry['tokens_compressed']}")
    print(f"  ID:         {entry['id']}")
    print(f"\nWritten to: {LOG_PATH}")
