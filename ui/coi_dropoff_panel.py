"""
coi_dropoff_panel.py — Left sidebar drop-off panel for COI Desktop.
Accepts files, text, and screenshots. Queues them for background LLM processing.
Summaries stay separate from chat context — no personality pollution.
"""

import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTextEdit, QScrollArea, QFileDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from coi_dropoff_worker import (
    load_queue, save_queue, SUMMARIES_DIR, ORIGINALS_DIR,
    DROPOFF_OPEN_TAG, DROPOFF_CLOSE_TAG
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ICM_ROOT = Path("K:/Coi Codex/COI-Codex-ICM")
QUEUE_PATH = ICM_ROOT / "inbox" / "dropoff-queue.json"


# ---------------------------------------------------------------------------
# QueueItemWidget — one row in the queue list
# ---------------------------------------------------------------------------
class QueueItemWidget(QFrame):
    """Single queue item display: name, status, inject button."""

    inject_requested = pyqtSignal(str)  # item_id

    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.item_id = item_data["id"]
        self.item_data = item_data
        self.setFixedHeight(32)
        self.setStyleSheet("background:#111920; border-radius:4px; margin:1px 0;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)

        # Status dot
        status = item_data.get("status", "queued")
        dot_colors = {
            "queued": "#f0a800",
            "processing": "#00c8f0",
            "done": "#00e5a0",
            "failed": "#ff4060",
        }
        dot = QLabel("●")
        dot.setFixedWidth(12)
        dot.setStyleSheet(f"color:{dot_colors.get(status, '#5a8090')}; font-size:10px;")
        layout.addWidget(dot)

        # Name
        name = item_data.get("display_name", "unknown")
        if len(name) > 22:
            name = name[:20] + "…"
        name_label = QLabel(name)
        name_label.setStyleSheet("color:#d8e8f0; font-size:9px; font-family:'JetBrains Mono',monospace;")
        name_label.setToolTip(item_data.get("display_name", ""))
        layout.addWidget(name_label, stretch=1)

        # Status text
        status_label = QLabel(status.upper())
        status_colors = {
            "queued": "#f0a800",
            "processing": "#00c8f0",
            "done": "#00e5a0",
            "failed": "#ff4060",
        }
        status_label.setStyleSheet(
            f"color:{status_colors.get(status, '#5a8090')}; font-size:8px; "
            f"font-family:'JetBrains Mono',monospace; font-weight:700;"
        )
        layout.addWidget(status_label)

        # Inject button (only for done items)
        if status == "done":
            inject_btn = QPushButton(">>")
            inject_btn.setFixedSize(24, 20)
            inject_btn.setStyleSheet(
                "background:#1e2d3d; color:#00e5a0; border:1px solid #00e5a0; "
                "border-radius:3px; font-size:9px; font-weight:700;"
            )
            inject_btn.setToolTip("Inject original content into chat context (verbatim)")
            inject_btn.clicked.connect(lambda: self.inject_requested.emit(self.item_id))
            layout.addWidget(inject_btn)


# ---------------------------------------------------------------------------
# DropOffPanel — left sidebar
# ---------------------------------------------------------------------------
class DropOffPanel(QWidget):
    """
    Left sidebar panel for dropping files, text, and screenshots.
    Items are queued and processed by background LLM worker.
    Summaries are stored separately from chat context.
    """

    # Signal to inject a summary into chat context
    inject_summary = pyqtSignal(str, str)  # item_id, summary_text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setAcceptDrops(True)
        self.setStyleSheet("background:#0a0e14; border-right:1px solid #1e2d3d;")
        self.setVisible(False)  # Hidden by default

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── HEADER ────────────────────────────────────────────
        header_row = QHBoxLayout()
        header = QLabel("DROP-OFF")
        header.setStyleSheet(
            "color:#00c8f0; font-size:11px; font-weight:700; "
            "font-family:'JetBrains Mono',monospace;"
        )
        header_row.addWidget(header)
        header_row.addStretch()

        close_btn = QPushButton("X")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "background:transparent; color:#5a8090; border:none; "
            "font-size:10px; font-weight:700;"
        )
        close_btn.clicked.connect(lambda: self.setVisible(False))
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        # ── DROP ZONE ─────────────────────────────────────────
        self.drop_frame = QFrame()
        self.drop_frame.setFixedHeight(80)
        self.drop_frame.setStyleSheet(
            "background:#111920; border:2px dashed #1e2d3d; border-radius:8px;"
        )
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        drop_label = QLabel("Drop files or paste text")
        drop_label.setStyleSheet(
            "color:#5a8090; font-size:10px; font-family:'JetBrains Mono',monospace; border:none;"
        )
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(drop_label)

        drop_hint = QLabel("Files, text, screenshots")
        drop_hint.setStyleSheet(
            "color:#2a4050; font-size:8px; font-family:'JetBrains Mono',monospace; border:none;"
        )
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(drop_hint)

        layout.addWidget(self.drop_frame)

        # ── ACTION BUTTONS ────────────────────────────────────
        btn_row = QHBoxLayout()

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedHeight(24)
        browse_btn.setStyleSheet(
            "background:#1e2d3d; color:#00c8f0; border:1px solid #00c8f0; "
            "border-radius:4px; font-size:9px; font-weight:700; "
            "font-family:'JetBrains Mono',monospace; padding:0 10px;"
        )
        browse_btn.clicked.connect(self._browse_files)
        btn_row.addWidget(browse_btn)

        paste_btn = QPushButton("Paste Text")
        paste_btn.setFixedHeight(24)
        paste_btn.setStyleSheet(
            "background:#1e2d3d; color:#f0a800; border:1px solid #f0a800; "
            "border-radius:4px; font-size:9px; font-weight:700; "
            "font-family:'JetBrains Mono',monospace; padding:0 10px;"
        )
        paste_btn.clicked.connect(self._paste_text)
        btn_row.addWidget(paste_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── PASTE AREA (hidden until needed) ──────────────────
        self.paste_area = QTextEdit()
        self.paste_area.setPlaceholderText("Paste text here, then click Queue...")
        self.paste_area.setFixedHeight(80)
        self.paste_area.setVisible(False)
        self.paste_area.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; "
            "border-radius:4px; font-size:11px; font-family:'Segoe UI',sans-serif; padding:6px;"
        )
        layout.addWidget(self.paste_area)

        # Queue pasted text button (hidden until paste area shown)
        self.queue_paste_btn = QPushButton("Queue Pasted Text")
        self.queue_paste_btn.setFixedHeight(24)
        self.queue_paste_btn.setVisible(False)
        self.queue_paste_btn.setStyleSheet(
            "background:#00e5a0; color:#07090c; border:none; border-radius:4px; "
            "font-size:9px; font-weight:700; font-family:'JetBrains Mono',monospace;"
        )
        self.queue_paste_btn.clicked.connect(self._queue_pasted_text)
        layout.addWidget(self.queue_paste_btn)

        # ── QUEUE HEADER ──────────────────────────────────────
        queue_header_row = QHBoxLayout()
        self.queue_header = QLabel("QUEUE (0)")
        self.queue_header.setStyleSheet(
            "color:#f0a800; font-size:9px; font-weight:700; "
            "font-family:'JetBrains Mono',monospace; margin-top:4px;"
        )
        queue_header_row.addWidget(self.queue_header)
        queue_header_row.addStretch()

        clear_done_btn = QPushButton("Clear Done")
        clear_done_btn.setFixedHeight(18)
        clear_done_btn.setStyleSheet(
            "background:transparent; color:#5a8090; border:none; "
            "font-size:8px; font-family:'JetBrains Mono',monospace;"
        )
        clear_done_btn.clicked.connect(self._clear_done_items)
        queue_header_row.addWidget(clear_done_btn)
        layout.addLayout(queue_header_row)

        # ── QUEUE LIST ────────────────────────────────────────
        queue_scroll = QScrollArea()
        queue_scroll.setWidgetResizable(True)
        queue_scroll.setStyleSheet(
            "QScrollArea { background:transparent; border:none; }"
            "QScrollBar:vertical { background:#0a0e14; width:4px; border:none; }"
            "QScrollBar::handle:vertical { background:#1e2d3d; border-radius:2px; }"
        )

        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(2)
        self.queue_layout.addStretch()

        queue_scroll.setWidget(self.queue_container)
        layout.addWidget(queue_scroll, stretch=1)

        # ── STATUS ────────────────────────────────────────────
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color:#5a8090; font-size:8px; font-family:'JetBrains Mono',monospace;"
        )
        layout.addWidget(self.status_label)

        # Load existing queue
        self._refresh_queue_display()

    # ── DRAG AND DROP ─────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            self.drop_frame.setStyleSheet(
                "background:#111920; border:2px dashed #00c8f0; border-radius:8px;"
            )

    def dragLeaveEvent(self, event):
        self.drop_frame.setStyleSheet(
            "background:#111920; border:2px dashed #1e2d3d; border-radius:8px;"
        )

    def dropEvent(self, event: QDropEvent):
        self.drop_frame.setStyleSheet(
            "background:#111920; border:2px dashed #1e2d3d; border-radius:8px;"
        )
        mime = event.mimeData()

        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path:
                    self._add_file_to_queue(path)
        elif mime.hasText():
            text = mime.text().strip()
            if text:
                self._add_text_to_queue(text)

        event.acceptProposedAction()

    # ── FILE BROWSING ─────────────────────────────────────────

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select files for drop-off", "",
            "All Files (*);;Text (*.txt *.md *.py *.json *.yaml *.yml *.csv *.log)"
            ";;Images (*.png *.jpg *.jpeg *.bmp)"
        )
        for f in files:
            self._add_file_to_queue(f)

    # ── PASTE TEXT ────────────────────────────────────────────

    def _paste_text(self):
        """Toggle the paste text area."""
        visible = not self.paste_area.isVisible()
        self.paste_area.setVisible(visible)
        self.queue_paste_btn.setVisible(visible)
        if visible:
            self.paste_area.setFocus()

    def _queue_pasted_text(self):
        """Queue whatever is in the paste area."""
        text = self.paste_area.toPlainText().strip()
        if not text:
            self.status_label.setText("Nothing to queue")
            self.status_label.setStyleSheet("color:#ff4060; font-size:8px; font-family:'JetBrains Mono',monospace;")
            return
        self._add_text_to_queue(text)
        self.paste_area.clear()
        self.paste_area.setVisible(False)
        self.queue_paste_btn.setVisible(False)

    # ── QUEUE MANAGEMENT ──────────────────────────────────────

    def _generate_id(self):
        """Generate a unique drop-off ID."""
        return f"DO-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _add_file_to_queue(self, filepath):
        """Add a file to the processing queue."""
        p = Path(filepath)
        item = {
            "id": self._generate_id(),
            "source_type": "screenshot" if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".gif") else "file",
            "source_path": str(p),
            "raw_text": None,
            "display_name": p.name,
            "status": "queued",
            "queued_at": datetime.now().isoformat(),
            "processed_at": None,
            "summary": None,
            "summary_file": None,
        }
        queue = load_queue()
        queue.append(item)
        save_queue(queue)
        self._refresh_queue_display()
        self.status_label.setText(f"Queued: {p.name}")
        self.status_label.setStyleSheet("color:#00e5a0; font-size:8px; font-family:'JetBrains Mono',monospace;")

    def _add_text_to_queue(self, text):
        """Add pasted text to the processing queue."""
        preview = text[:30].replace("\n", " ")
        if len(text) > 30:
            preview += "…"
        item = {
            "id": self._generate_id(),
            "source_type": "text",
            "source_path": None,
            "raw_text": text,
            "display_name": f"text: {preview}",
            "status": "queued",
            "queued_at": datetime.now().isoformat(),
            "processed_at": None,
            "summary": None,
            "summary_file": None,
        }
        queue = load_queue()
        queue.append(item)
        save_queue(queue)
        self._refresh_queue_display()
        self.status_label.setText(f"Queued: {len(text):,} chars")
        self.status_label.setStyleSheet("color:#00e5a0; font-size:8px; font-family:'JetBrains Mono',monospace;")

    def _clear_done_items(self):
        """Remove completed items from the queue."""
        queue = load_queue()
        queue = [item for item in queue if item.get("status") not in ("done", "failed")]
        save_queue(queue)
        self._refresh_queue_display()

    # ── DISPLAY ───────────────────────────────────────────────

    def _refresh_queue_display(self):
        """Rebuild the queue item list from disk."""
        # Clear existing widgets
        while self.queue_layout.count() > 1:  # Keep the stretch
            child = self.queue_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        queue = load_queue()
        self.queue_header.setText(f"QUEUE ({len(queue)})")

        for item in queue:
            widget = QueueItemWidget(item)
            widget.inject_requested.connect(self._on_inject_requested)
            self.queue_layout.insertWidget(self.queue_layout.count() - 1, widget)

    def update_item_status(self, item_id, new_status):
        """Called by worker signals to refresh display after processing."""
        self._refresh_queue_display()
        if new_status == "done":
            self.status_label.setText(f"Processed: {item_id}")
            self.status_label.setStyleSheet("color:#00e5a0; font-size:8px; font-family:'JetBrains Mono',monospace;")
        elif new_status == "failed":
            self.status_label.setText(f"Failed: {item_id}")
            self.status_label.setStyleSheet("color:#ff4060; font-size:8px; font-family:'JetBrains Mono',monospace;")
        elif new_status == "processing":
            self.status_label.setText(f"Processing: {item_id}")
            self.status_label.setStyleSheet("color:#00c8f0; font-size:8px; font-family:'JetBrains Mono',monospace;")

    def _on_inject_requested(self, item_id):
        """User clicked >> on a done item — load and emit ORIGINAL verbatim content (SPEC-05)."""
        queue = load_queue()
        for item in queue:
            if item["id"] == item_id:
                display_name = item.get("display_name", item_id)

                # SPEC-05: Always inject original content, never summary
                original_file = item.get("original_file")
                if original_file and Path(original_file).exists():
                    content = Path(original_file).read_text(encoding="utf-8")
                else:
                    # Fallback: reconstruct from raw_text if original file missing
                    raw = item.get("raw_text", "")
                    if raw:
                        content = (
                            f"{DROPOFF_OPEN_TAG}\n"
                            f"Source: {display_name}\n"
                            f"Type: {item.get('source_type', 'text')}\n"
                            f"---\n"
                            f"{raw}\n"
                            f"{DROPOFF_CLOSE_TAG}\n"
                        )
                    else:
                        content = f"[Original content not available for {item_id}]"

                self.inject_summary.emit(item_id, content)
                self.status_label.setText(f"Injected: {display_name}")
                self.status_label.setStyleSheet("color:#00e5a0; font-size:8px; font-family:'JetBrains Mono',monospace;")
                return


def get_dropoff_index():
    """Build a compact summary index for the system prompt.
    Returns a string listing available summaries (low token cost)."""
    queue = load_queue()
    done_items = [item for item in queue if item.get("status") == "done"]

    if not done_items:
        return ""

    lines = ["--- AVAILABLE DROP-OFF SUMMARIES ---",
             "Processed content available. Reference by ID if Dave asks about dropped content.",
             "To load full details, respond with [DROPOFF: ID]"]

    for item in done_items[-10:]:  # Last 10 only
        item_id = item["id"]
        name = item.get("display_name", "unknown")
        summary_preview = item.get("summary", "")[:80]
        lines.append(f"- {item_id}: {name} — \"{summary_preview}\"")

    return "\n".join(lines)
