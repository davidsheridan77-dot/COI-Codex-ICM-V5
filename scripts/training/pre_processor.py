"""
pre_processor.py
COI LLM Optimization Program — Stage 2: Compress
Sits between Dave's input and the Ollama API call.
Returns compressed text for the model, logs the pair via ChatLogger.
"""

import re
import json
from pathlib import Path

RULES_PATH = Path(r"K:\Coi Codex\COI-Codex-ICM-V5\COI\L4-Working\training\rules\compression-rules.json")
AUDIT_PATH = Path(r"K:\Coi Codex\COI-Codex-ICM-V5\COI\L4-Working\training\scores\compression-audit.jsonl")

# Token threshold — only compress if input is over this many chars
# Short inputs compress poorly and can lose meaning
COMPRESS_THRESHOLD = 80


class PreProcessor:
    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> list:
        if not RULES_PATH.exists():
            return []
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [r for r in data.get("rules", []) if r.get("status") in ("active", "trial")]

    def reload_rules(self):
        """Call this after audit updates rules file."""
        self.rules = self._load_rules()

    def _apply_rules(self, text: str) -> tuple[str, list]:
        applied = []
        result = text
        for rule in self.rules:
            if rule["pattern"].lower() in result.lower():
                # Case-insensitive replace
                pattern = re.compile(re.escape(rule["pattern"]), re.IGNORECASE)
                result = pattern.sub(rule["replacement"], result)
                applied.append(rule["pattern"])
        return result, applied

    def _strip_filler(self, text: str) -> str:
        fillers = [
            r"\bcould you\b",
            r"\bwould you\b",
            r"\bi was wondering\b",
            r"\bjust\b",
            r"\bkind of\b",
            r"\bsort of\b",
            r"\bbasically\b",
            r"\bactually\b",
            r"\bcan you\b",
            r"\bplease\b",
        ]
        result = text
        for f in fillers:
            result = re.sub(f, "", result, flags=re.IGNORECASE)
        return result

    def _clean(self, text: str) -> str:
        # Collapse whitespace, strip edges
        return re.sub(r"\s+", " ", text).strip()

    def process(self, raw_input: str) -> dict:
        """
        Main entry point. Call this before sending input to Ollama.

        Returns dict with:
          - compressed: text to send to the model
          - raw: original input
          - ratio: compression ratio (lower = more compressed)
          - rules_applied: which rules fired
          - was_compressed: bool
        """
        # Skip compression for short inputs
        if len(raw_input) < COMPRESS_THRESHOLD:
            return {
                "compressed": raw_input,
                "raw": raw_input,
                "ratio": 1.0,
                "rules_applied": [],
                "was_compressed": False
            }

        text = raw_input
        text, rules_applied = self._apply_rules(text)
        text = self._strip_filler(text)
        text = self._clean(text)

        ratio = round(len(text) / max(len(raw_input), 1), 3)

        return {
            "compressed": text,
            "raw": raw_input,
            "ratio": ratio,
            "rules_applied": rules_applied,
            "was_compressed": True
        }

    def flag_for_audit(self, entry_id: str, issue: str, rule_pattern: str = ""):
        """
        Call this when a compression is suspected to have hurt response quality.
        Writes to compression-audit.jsonl for review.
        """
        import time
        from datetime import datetime
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "entry_id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "issue": issue,
            "rule_pattern": rule_pattern,
            "action": "pending_review"
        }
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


# --- Standalone test ---
if __name__ == "__main__":
    pp = PreProcessor()

    tests = [
        "can you please check the forge queue and tell me what build order tasks are pending",
        "would you look at the claude code output and summarize the errors",
        "check status",  # short — should not compress
        "i was wondering if you could basically just look at the build order and kind of tell me what is next on the list for the COI Forge pipeline",
    ]

    print("PreProcessor test:\n")
    for t in tests:
        result = pp.process(t)
        print(f"Raw:        {result['raw']}")
        print(f"Compressed: {result['compressed']}")
        print(f"Ratio:      {result['ratio']}  |  Rules: {result['rules_applied']}")
        print(f"Compressed: {result['was_compressed']}")
        print()
