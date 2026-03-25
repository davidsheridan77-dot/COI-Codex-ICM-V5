"""
coi_briefing_panel.py — Return briefing panel for COI Desktop.
Shows what the pipeline did while Dave was gone.
Reads approval queue, execution log, and build order for context.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QSizePolicy, QDialog, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ICM_ROOT = Path("K:/Coi Codex/COI-Codex-ICM")
APPROVAL_DIR = ICM_ROOT / "pipeline" / "05-dave-approval" / "output"
APPROVED_DIR = APPROVAL_DIR / "approved"
REJECTED_DIR = APPROVAL_DIR / "rejected"
HELD_DIR = APPROVAL_DIR / "held"
EXECUTION_LOG = ICM_ROOT / "COI" / "L4-Working" / "memory" / "execution-log.md"
PIPELINE_LOG = ICM_ROOT / "COI" / "L4-Working" / "memory" / "pipeline-log.md"
BUILD_ORDER = ICM_ROOT / "COI" / "L1-Routing" / "MASTER-BUILD-ORDER.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _human_timestamp(dt):
    """Convert datetime to human-readable relative string."""
    now = datetime.now()
    diff = now - dt

    if diff.total_seconds() < 60:
        return "just now"
    if diff.total_seconds() < 3600:
        mins = int(diff.total_seconds() / 60)
        return f"{mins}m ago"
    if dt.date() == now.date():
        return f"today {dt.strftime('%I:%M%p').lower().lstrip('0')}"
    if dt.date() == (now - timedelta(days=1)).date():
        return f"yesterday {dt.strftime('%I:%M%p').lower().lstrip('0')}"
    return dt.strftime('%b %d %I:%M%p').lower()


def _parse_approval_file(path):
    """Extract category and target info from an approval queue file."""
    try:
        content = path.read_text(encoding="utf-8")
        info = {"filename": path.name, "path": str(path), "timestamp": None,
                "category": "", "target": "", "summary": ""}

        for line in content.splitlines():
            line_s = line.strip()
            if line_s and not line_s.startswith("#") and info["timestamp"] is None:
                # First non-header line is usually the timestamp
                try:
                    info["timestamp"] = datetime.strptime(line_s[:19], "%Y-%m-%d-%H-%M-%S")
                except (ValueError, IndexError):
                    try:
                        info["timestamp"] = datetime.strptime(line_s[:16], "%Y-%m-%d %H:%M")
                    except (ValueError, IndexError):
                        pass
            if line_s.startswith("## Category"):
                # Next non-empty line is the category
                idx = content.find(line_s) + len(line_s)
                rest = content[idx:].strip()
                info["category"] = rest.split("\n")[0].strip()
            if "**File:**" in line_s:
                info["target"] = line_s.split("**File:**")[-1].strip().strip("`")
            if "**Reason:**" in line_s or "**Action:**" in line_s:
                info["summary"] = line_s.split(":**")[-1].strip()

        # Fall back to timestamp from filename
        if info["timestamp"] is None:
            try:
                ts_str = path.stem[:19]
                info["timestamp"] = datetime.strptime(ts_str, "%Y-%m-%d-%H-%M-%S")
            except (ValueError, IndexError):
                info["timestamp"] = datetime.fromtimestamp(path.stat().st_mtime)

        # Build display name
        cat = info["category"] or "Unknown"
        info["display"] = f"{cat}: {info['summary'][:50]}" if info["summary"] else cat

        return info
    except Exception:
        return None


def _get_log_entries(log_path, since_hours=24):
    """Parse a log file (execution-log.md or pipeline-log.md) for recent entries."""
    entries = []
    if not log_path or not log_path.exists():
        return entries

    try:
        content = log_path.read_text(encoding="utf-8")
    except Exception:
        return entries

    cutoff = datetime.now() - timedelta(hours=since_hours)
    current = None

    for line in content.splitlines():
        if line.startswith("## ") and " — " in line:
            if current:
                entries.append(current)
            # Parse: ## 2026-03-21 15:30:22 — Git
            parts = line[3:].split(" — ", 1)
            ts_str = parts[0].strip()
            cmd_type = parts[1].strip() if len(parts) > 1 else "unknown"
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts = None
            current = {"timestamp": ts, "type": cmd_type, "command": "", "status": "ok"}
        elif current:
            if "**Command:**" in line:
                current["command"] = line.split("**Command:**")[-1].strip().strip("`")
            if "**Return code:**" in line:
                rc = line.split("**Return code:**")[-1].strip()
                if rc != "0":
                    current["status"] = "failed"

    if current:
        entries.append(current)

    # Filter to recent
    return [e for e in entries if e.get("timestamp") and e["timestamp"] > cutoff]


def scan_briefing_data():
    """Scan all data sources and return structured briefing data.
    Returns dict with keys: pending, approved, failed, last_run, idle."""

    data = {
        "pending": [],
        "approved": [],
        "failed": [],
        "last_run": None,
        "idle": True,
    }

    # Pending approval items
    if APPROVAL_DIR.exists():
        for f in sorted(APPROVAL_DIR.iterdir()):
            if f.is_file() and f.suffix == ".md":
                info = _parse_approval_file(f)
                if info:
                    data["pending"].append(info)
                    data["idle"] = False

    # Recently approved (archived)
    for subdir, status in [(APPROVED_DIR, "approved"), (REJECTED_DIR, "rejected")]:
        if subdir.exists():
            for f in sorted(subdir.iterdir(), reverse=True):
                if f.is_file() and f.suffix == ".md":
                    info = _parse_approval_file(f)
                    if info:
                        info["decision"] = status
                        data["approved"].append(info)
                        data["idle"] = False

    # Execution log + pipeline log for failures and last run timestamp
    for log_path in [EXECUTION_LOG, PIPELINE_LOG]:
        log_entries = _get_log_entries(log_path, since_hours=48)
        for entry in log_entries:
            if entry["status"] == "failed":
                data["failed"].append(entry)
                data["idle"] = False
            if entry.get("timestamp"):
                if data["last_run"] is None or entry["timestamp"] > data["last_run"]:
                    data["last_run"] = entry["timestamp"]

    # Use most recent approval/pending timestamp as last_run fallback
    if data["last_run"] is None:
        all_items = data["pending"] + data["approved"]
        if all_items:
            timestamps = [item["timestamp"] for item in all_items if item.get("timestamp")]
            if timestamps:
                data["last_run"] = max(timestamps)

    # If we found any pending items, not idle
    if data["pending"]:
        data["idle"] = False

    return data


# ---------------------------------------------------------------------------
# BriefingItemWidget — one row in the briefing list
# ---------------------------------------------------------------------------
class BriefingItemWidget(QFrame):
    """Single briefing item row with status and action button."""

    action_clicked = pyqtSignal(str, dict)  # action_type, item_data

    def __init__(self, label, status_text, status_color, action_type=None, item_data=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setStyleSheet("background:#111920; border-radius:4px; margin:1px 0;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        # Arrow
        arrow = QLabel("→")
        arrow.setFixedWidth(12)
        arrow.setStyleSheet("color:#2a4050; font-size:10px; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(arrow)

        # Label
        if len(label) > 35:
            label = label[:33] + "…"
        name_label = QLabel(label)
        name_label.setStyleSheet("color:#d8e8f0; font-size:9px; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(name_label, stretch=1)

        # Action button
        if action_type and action_type != "done":
            btn_text = {"review": "[review]", "error": "[view error]"}.get(action_type, f"[{action_type}]")
            btn_colors = {
                "review": ("color:#f0a800; background:transparent; border:none; "
                           "font-size:9px; font-weight:700; font-family:'JetBrains Mono',monospace;"),
                "error": ("color:#ff4060; background:transparent; border:none; "
                          "font-size:9px; font-weight:700; font-family:'JetBrains Mono',monospace;"),
            }
            btn = QPushButton(btn_text)
            btn.setFixedHeight(22)
            btn.setStyleSheet(btn_colors.get(action_type,
                "color:#5a8090; background:transparent; border:none; "
                "font-size:9px; font-family:'JetBrains Mono',monospace;"))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda: self.action_clicked.emit(action_type, item_data or {}))
            layout.addWidget(btn)
        else:
            status_label = QLabel(f"[{status_text}]")
            status_label.setStyleSheet(
                f"color:{status_color}; font-size:9px; font-weight:700; "
                f"font-family:'JetBrains Mono',monospace;"
            )
            layout.addWidget(status_label)


# ---------------------------------------------------------------------------
# ReturnBriefingPanel — right overlay / side panel
# ---------------------------------------------------------------------------
class ReturnBriefingPanel(QWidget):
    """
    Return briefing panel. Shows pipeline activity since Dave was last present.
    Emits signals when Dave wants to review an item or view an error.
    """

    review_requested = pyqtSignal(dict)   # item_data for approval review
    error_requested = pyqtSignal(dict)    # item_data for error viewing

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setStyleSheet("background:#0a0f14; border-left:1px solid #1e2d3d;")
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel("SINCE YOU WERE GONE")
        header.setStyleSheet(
            "color:#f0a800; font-size:13px; font-weight:700; "
            "font-family:'JetBrains Mono',monospace;"
        )
        layout.addWidget(header)

        # Divider
        div = QLabel("─" * 32)
        div.setStyleSheet("color:#1e2d3d; font-size:9px; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(div)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background:#0a0f14; width:6px; }"
            "QScrollBar::handle:vertical { background:#1e2d3d; border-radius:3px; }"
        )

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(4)
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll, stretch=1)

        # Footer — last run timestamp
        self.footer = QLabel("")
        self.footer.setStyleSheet(
            "color:#2a4050; font-size:9px; font-family:'JetBrains Mono',monospace;"
        )
        layout.addWidget(self.footer)

        # Bottom divider
        div2 = QLabel("─" * 32)
        div2.setStyleSheet("color:#1e2d3d; font-size:9px; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(div2)

        # Refresh + Dismiss buttons
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedSize(72, 26)
        refresh_btn.setStyleSheet(
            "background:#1e2d3d; color:#00c8f0; border:1px solid #00c8f0; "
            "border-radius:4px; font-size:9px; font-weight:700; "
            "font-family:'JetBrains Mono',monospace;"
        )
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)

        dismiss_btn = QPushButton("Dismiss")
        dismiss_btn.setFixedSize(72, 26)
        dismiss_btn.setStyleSheet(
            "background:#1e2d3d; color:#5a8090; border:1px solid #2a4050; "
            "border-radius:4px; font-size:9px; font-weight:700; "
            "font-family:'JetBrains Mono',monospace;"
        )
        dismiss_btn.clicked.connect(lambda: self.setVisible(False))
        btn_row.addWidget(dismiss_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        """Scan data sources and rebuild the panel content."""
        # Clear existing items
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        data = scan_briefing_data()

        if data["idle"] and not data["pending"] and not data["approved"] and not data["failed"]:
            idle_label = QLabel("Pipeline idle. Ready to plan.")
            idle_label.setStyleSheet(
                "color:#5a8090; font-size:10px; font-family:'JetBrains Mono',monospace; "
                "padding:20px 0;"
            )
            idle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.content_layout.addWidget(idle_label)
            self.footer.setText("No pipeline activity recorded.")
            return

        # Section: Pending approval
        if data["pending"]:
            self._add_section_header(
                f"Built & queued for approval     [{len(data['pending'])} items]",
                "#f0a800"
            )
            for item in data["pending"]:
                ts = _human_timestamp(item["timestamp"]) if item.get("timestamp") else ""
                label = item.get("display", item["filename"])
                widget = BriefingItemWidget(
                    label=label,
                    status_text="review",
                    status_color="#f0a800",
                    action_type="review",
                    item_data=item
                )
                widget.action_clicked.connect(self._on_action)
                self.content_layout.addWidget(widget)

        # Section: Completed / approved
        if data["approved"]:
            self._add_section_header(
                f"Completed & decided             [{len(data['approved'])} items]",
                "#00e5a0"
            )
            for item in data["approved"][:10]:  # Cap display
                label = item.get("display", item["filename"])
                decision = item.get("decision", "approved")
                color = "#00e5a0" if decision == "approved" else "#ff4060"
                widget = BriefingItemWidget(
                    label=label,
                    status_text=decision,
                    status_color=color,
                    action_type="done"
                )
                self.content_layout.addWidget(widget)

        # Section: Failures
        if data["failed"]:
            self._add_section_header(
                f"Failed / needs attention         [{len(data['failed'])} items]",
                "#ff4060"
            )
            for entry in data["failed"]:
                label = entry.get("command", "unknown command")[:40]
                widget = BriefingItemWidget(
                    label=label,
                    status_text="failed",
                    status_color="#ff4060",
                    action_type="error",
                    item_data=entry
                )
                widget.action_clicked.connect(self._on_action)
                self.content_layout.addWidget(widget)

        self.content_layout.addStretch()

        # Footer
        if data["last_run"]:
            self.footer.setText(f"Last pipeline run: {_human_timestamp(data['last_run'])}")
        else:
            self.footer.setText("No pipeline runs recorded yet.")

    def _add_section_header(self, text, color):
        """Add a section header label."""
        label = QLabel(text)
        label.setStyleSheet(
            f"color:{color}; font-size:10px; font-weight:700; "
            f"font-family:'JetBrains Mono',monospace; padding-top:8px;"
        )
        self.content_layout.addWidget(label)

    def _on_action(self, action_type, item_data):
        """Route action button clicks."""
        if action_type == "review":
            self.review_requested.emit(item_data)
        elif action_type == "error":
            self.error_requested.emit(item_data)

    def show_if_needed(self):
        """Show panel automatically if there are pending approvals or failures."""
        data = scan_briefing_data()
        if data["pending"] or data["failed"]:
            self.refresh()
            self.setVisible(True)
            return True
        return False

    def has_items(self):
        """Quick check if there's anything to show."""
        data = scan_briefing_data()
        return bool(data["pending"] or data["approved"] or data["failed"])
