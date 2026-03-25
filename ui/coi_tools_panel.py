#!/usr/bin/env python3
# ============================================================
# COI Tools Panel — Sidebar for COI Desktop v4
# Docked to the RIGHT side of the main window
# Live stats, tools dropdown, token monitor
# ============================================================

import os
import sys
import re
import json
import socket
import subprocess
import threading
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QToolButton, QMenu, QDialog, QTextEdit, QPushButton,
    QMessageBox, QFileDialog, QSpinBox, QDoubleSpinBox,
    QCheckBox, QScrollArea, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QAction

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

import requests

# ── PATHS ─────────────────────────────────────────────────────
ICM_ROOT = Path("K:/Coi Codex/COI-Codex-ICM")
LOGS_DIR = ICM_ROOT / "logs"
SNAPSHOTS_DIR = LOGS_DIR / "snapshots"
TOKEN_CONFIG_PATH = ICM_ROOT / "config" / "token_config.json"
MODEL_CONFIG_PATH = ICM_ROOT / "scripts" / "model-config.json"  # DEPRECATED-V5
OLLAMA_API = "http://localhost:11434"  # DEPRECATED-V5


# ── RESULT DIALOG ─────────────────────────────────────────────
class ResultDialog(QDialog):
    """Dark-themed scrollable result viewer with Copy button"""

    _thread_append = pyqtSignal(str)  # Thread-safe text append

    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self._thread_append.connect(self._do_append)
        self.setWindowTitle(f"COI — {title}")
        self.setMinimumSize(650, 450)
        self.setStyleSheet("background:#0a0e14; color:#d8e8f0;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel(title)
        header.setStyleSheet("color:#00c8f0; font-size:13px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        layout.addWidget(header)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlainText(content)
        self.output.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; "
            "border-radius:6px; padding:10px; font-family:'JetBrains Mono',monospace; font-size:11px;"
        )
        layout.addWidget(self.output, stretch=1)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("Copy Output")
        copy_btn.setStyleSheet(
            "background:#1e2d3d; color:#00c8f0; border:1px solid #00c8f0; border-radius:6px; "
            "padding:8px 16px; font-weight:700; font-size:11px;"
        )
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.output.toPlainText()))
        btn_row.addStretch()
        btn_row.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "background:#1e2d3d; color:#d8e8f0; border:1px solid #2a4050; border-radius:6px; "
            "padding:8px 16px; font-weight:700; font-size:11px;"
        )
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def append_text(self, text):
        """Thread-safe append — can be called from any thread."""
        self._thread_append.emit(text)

    def _do_append(self, text):
        """Actual append — runs on main thread via signal."""
        self.output.append(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())


# ── REPAIR APPROVAL DIALOG ────────────────────────────────────
class RepairApprovalDialog(QDialog):
    """Shows a single repair fix for Dave to approve or skip."""

    def __init__(self, fix_data, fix_index, total_fixes, parent=None):
        super().__init__(parent)
        self.fix_data = fix_data
        self.setWindowTitle(f"COI — Repair Fix {fix_index}/{total_fixes}")
        self.setMinimumSize(650, 400)
        self.setStyleSheet("background:#0d1117; color:#d8e8f0;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Header
        severity = fix_data.get("severity", "INFO")
        sev_colors = {"CRITICAL": "#ff4060", "WARNING": "#f0a800", "INFO": "#00c8f0"}
        header = QLabel(f"[{severity}] Fix {fix_index} of {total_fixes}")
        header.setStyleSheet(
            f"color:{sev_colors.get(severity, '#00c8f0')}; font-size:13px; "
            f"font-weight:700; font-family:'JetBrains Mono',monospace;"
        )
        layout.addWidget(header)

        # Issue description
        issue_label = QLabel("Issue:")
        issue_label.setStyleSheet("color:#5a8090; font-size:10px;")
        layout.addWidget(issue_label)

        issue_text = QLabel(fix_data.get("issue", "Unknown issue"))
        issue_text.setWordWrap(True)
        issue_text.setStyleSheet("color:#d8e8f0; font-size:12px; padding:4px;")
        layout.addWidget(issue_text)

        # Fix action
        action_label = QLabel("Proposed fix:")
        action_label.setStyleSheet("color:#5a8090; font-size:10px; margin-top:6px;")
        layout.addWidget(action_label)

        fix_view = QTextEdit()
        fix_view.setReadOnly(True)
        fix_content = ""
        fix_type = fix_data.get("type", "unknown")
        if fix_type == "create_file":
            fix_content = f"CREATE FILE: {fix_data.get('path', '?')}\n\n{fix_data.get('content', '')}"
        elif fix_type == "edit_file":
            fix_content = f"EDIT FILE: {fix_data.get('path', '?')}\n\n{fix_data.get('content', '')}"
        elif fix_type == "config":
            fix_content = f"CONFIG CHANGE:\n{fix_data.get('content', '')}"
        elif fix_type == "command":
            fix_content = f"RUN COMMAND:\n{fix_data.get('command', '')}"
        else:
            fix_content = fix_data.get("content", fix_data.get("description", "No details"))
        fix_view.setPlainText(fix_content)
        fix_view.setStyleSheet(
            "background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; "
            "border-radius:6px; padding:10px; font-family:'JetBrains Mono',monospace; font-size:11px;"
        )
        layout.addWidget(fix_view, stretch=1)

        # Buttons
        btn_layout = QHBoxLayout()

        approve_btn = QPushButton("Approve Fix")
        approve_btn.setStyleSheet(
            "background:#00e5a0; color:#07090c; border:none; border-radius:8px; "
            "padding:10px 20px; font-weight:700; font-size:12px;"
        )
        approve_btn.clicked.connect(self.accept)

        skip_btn = QPushButton("Skip")
        skip_btn.setStyleSheet(
            "background:#1e2d3d; color:#f0a800; border:1px solid #f0a800; border-radius:8px; "
            "padding:10px 20px; font-weight:700; font-size:12px;"
        )
        skip_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(approve_btn)
        btn_layout.addWidget(skip_btn)
        layout.addLayout(btn_layout)


# ── TOOLS PANEL ───────────────────────────────────────────────
class COIToolsPanel(QWidget):
    """Sidebar panel — live stats, tools dropdown, token monitor"""

    # Signal for main window to display messages in chat
    tool_message = pyqtSignal(str, str, str)  # sender, text, color
    _show_repair_fixes = pyqtSignal(str, list)  # raw_report, fixes list — main thread

    def __init__(self, main_window=None, token_tracker=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.token_tracker = token_tracker
        self._last_tool_output = ""
        self._spike_flash_timer = None
        self._show_repair_fixes.connect(self._on_repair_fixes_ready)
        self.setFixedWidth(220)
        self.setStyleSheet("background:#0a0e14; border-left:1px solid #1e2d3d;")
        self._init_ui()
        self._start_stats_timer()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── ZONE 1: LIVE STATS STRIP ──────────────────────────
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background:#0d1117; border:1px solid #1e2d3d; border-radius:6px;")
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setContentsMargins(8, 6, 8, 6)
        stats_layout.setSpacing(2)

        stats_header = QLabel("SYSTEM")
        stats_header.setStyleSheet("color:#5a8090; font-size:9px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        stats_layout.addWidget(stats_header)

        mono = "font-family:'JetBrains Mono',monospace; font-size:10px;"
        self.vram_label = QLabel("VRAM: ...")
        self.vram_label.setStyleSheet(f"color:#00e5a0; {mono}")
        stats_layout.addWidget(self.vram_label)

        self.ram_label = QLabel("RAM:  ...")
        self.ram_label.setStyleSheet(f"color:#d8e8f0; {mono}")
        stats_layout.addWidget(self.ram_label)

        self.cpu_label = QLabel("CPU:  ...")
        self.cpu_label.setStyleSheet(f"color:#d8e8f0; {mono}")
        stats_layout.addWidget(self.cpu_label)

        layout.addWidget(stats_frame)

        # ── ZONE 2: TOOLS DROPDOWN ────────────────────────────
        self.tools_btn = QToolButton()
        self.tools_btn.setText("⚙ COI TOOLS ▼")
        self.tools_btn.setFixedHeight(32)
        self.tools_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.tools_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.tools_btn.setStyleSheet(
            "QToolButton { background:#1e2d3d; color:#00c8f0; border:1px solid #00c8f0; "
            "border-radius:6px; font-weight:700; font-size:11px; font-family:'JetBrains Mono',monospace; }"
            "QToolButton::menu-indicator { image: none; }"
            "QToolButton:hover { background:#253545; }"
        )
        menu = self._build_menu()
        self.tools_btn.setMenu(menu)
        layout.addWidget(self.tools_btn)

        # ── TOKEN MONITOR READOUT ─────────────────────────────
        token_frame = QFrame()
        token_frame.setStyleSheet("background:#0d1117; border:1px solid #1e2d3d; border-radius:6px;")
        token_layout = QVBoxLayout(token_frame)
        token_layout.setContentsMargins(8, 6, 8, 6)
        token_layout.setSpacing(2)

        token_header = QLabel("TOKEN MONITOR")
        token_header.setStyleSheet("color:#5a8090; font-size:9px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        token_layout.addWidget(token_header)

        mono_sm = "font-family:'JetBrains Mono',monospace; font-size:9px;"
        self.token_session = QLabel("Session: ↑ 0  ↓ 0")
        self.token_session.setStyleSheet(f"color:#00e5a0; {mono_sm}")
        token_layout.addWidget(self.token_session)

        self.token_last = QLabel("Last:    ↑ 0  ↓ 0")
        self.token_last.setStyleSheet(f"color:#00e5a0; {mono_sm}")
        token_layout.addWidget(self.token_last)

        self.token_rate = QLabel("Rate:    0 tok/min")
        self.token_rate.setStyleSheet(f"color:#00e5a0; {mono_sm}")
        token_layout.addWidget(self.token_rate)

        spike_row = QHBoxLayout()
        self.spike_label = QLabel("Spikes:  0")
        self.spike_label.setStyleSheet(f"color:#00e5a0; {mono_sm}")
        spike_row.addWidget(self.spike_label)
        spike_row.addStretch()

        view_btn = QPushButton("View")
        view_btn.setFixedSize(36, 18)
        view_btn.setStyleSheet(
            "background:#1e2d3d; color:#00c8f0; border:1px solid #1e2d3d; border-radius:3px; "
            "font-size:8px; font-weight:700; font-family:'JetBrains Mono',monospace;"
        )
        view_btn.clicked.connect(self.fn_view_spike_log)
        spike_row.addWidget(view_btn)
        token_layout.addLayout(spike_row)

        layout.addWidget(token_frame)

        # ── SPIKE THRESHOLD SETTINGS (collapsible) ────────────
        self.threshold_frame = QFrame()
        self.threshold_frame.setStyleSheet("background:#0d1117; border:1px solid #1e2d3d; border-radius:6px;")
        self.threshold_frame.setVisible(False)
        thresh_layout = QVBoxLayout(self.threshold_frame)
        thresh_layout.setContentsMargins(8, 6, 8, 6)
        thresh_layout.setSpacing(3)

        thresh_header_row = QHBoxLayout()
        thresh_header = QLabel("SPIKE THRESHOLDS")
        thresh_header.setStyleSheet("color:#5a8090; font-size:9px; font-weight:700; font-family:'JetBrains Mono',monospace;")
        thresh_header_row.addWidget(thresh_header)
        thresh_header_row.addStretch()
        thresh_layout.addLayout(thresh_header_row)

        lbl_style = "color:#5a8090; font-size:8px; font-family:'JetBrains Mono',monospace;"
        spin_style = ("background:#111920; color:#d8e8f0; border:1px solid #1e2d3d; "
                      "border-radius:3px; font-size:9px; font-family:'JetBrains Mono',monospace;")

        def add_double_spin(label_text, default, min_v=0.5, max_v=10.0, step=0.5):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(lbl_style)
            thresh_layout.addWidget(lbl)
            spin = QDoubleSpinBox()
            spin.setRange(min_v, max_v)
            spin.setSingleStep(step)
            spin.setValue(default)
            spin.setFixedHeight(22)
            spin.setStyleSheet(spin_style)
            thresh_layout.addWidget(spin)
            return spin

        def add_int_spin(label_text, default, min_v=1, max_v=999999):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(lbl_style)
            thresh_layout.addWidget(lbl)
            spin = QSpinBox()
            spin.setRange(min_v, max_v)
            spin.setValue(default)
            spin.setFixedHeight(22)
            spin.setStyleSheet(spin_style)
            thresh_layout.addWidget(spin)
            return spin

        def add_check(label_text, default=True):
            cb = QCheckBox(label_text)
            cb.setChecked(default)
            cb.setStyleSheet("color:#d8e8f0; font-size:8px; font-family:'JetBrains Mono',monospace;")
            thresh_layout.addWidget(cb)
            return cb

        self.sp_prompt_mult = add_double_spin("Prompt spike mult:", 2.0)
        self.sp_comp_mult = add_double_spin("Completion spike mult:", 2.0)
        self.sp_max_tpm = add_int_spin("Max tok/min warning:", 500)
        self.sp_warn_wm = add_int_spin("Session warn watermark:", 25000)
        self.sp_crit_wm = add_int_spin("Session crit watermark:", 100000)
        self.cb_ceiling = add_check("Completion ceiling flag")
        self.cb_bloat = add_check("Context bloat detection")
        self.cb_retry = add_check("Retry loop detection")
        self.cb_ratio = add_check("Ratio flip detection")
        self.sp_max_entries = add_int_spin("Spike log max entries:", 500, 10, 10000)
        self.sp_clear_time = add_int_spin("Alert clear time (s):", 30, 5, 300)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(22)
        save_btn.setStyleSheet(
            "background:#00e5a0; color:#07090c; border:none; border-radius:3px; "
            "font-weight:700; font-size:9px;"
        )
        save_btn.clicked.connect(self._save_thresholds)
        btn_row.addWidget(save_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedHeight(22)
        reset_btn.setStyleSheet(
            "background:#1e2d3d; color:#ff4060; border:1px solid #ff4060; border-radius:3px; "
            "font-weight:700; font-size:9px;"
        )
        reset_btn.clicked.connect(self._reset_thresholds)
        btn_row.addWidget(reset_btn)
        thresh_layout.addLayout(btn_row)

        layout.addWidget(self.threshold_frame)

        # Load saved thresholds
        self._load_thresholds()

        layout.addStretch()

    # ── MENU BUILDER ──────────────────────────────────────────
    def _build_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background:#0d1117; color:#d8e8f0; border:1px solid #1e2d3d; "
            "font-family:'JetBrains Mono',monospace; font-size:10px; }"
            "QMenu::item { padding:4px 16px; }"
            "QMenu::item:selected { background:#1e2d3d; color:#00c8f0; }"
            "QMenu::separator { background:#1e2d3d; height:1px; margin:4px 8px; }"
        )

        def add_section(title):
            section = menu.addAction(title)
            section.setEnabled(False)
            menu.addSeparator()

        def add_item(text, fn):
            action = menu.addAction(text)
            action.triggered.connect(fn)

        # 🖥️ SYSTEM
        add_section("🖥️ SYSTEM")
        add_item("Restart COI UI", self.fn_restart_ui)
        add_item("COI Agent Status", self.fn_agent_status)
        add_item("Kill / Restart Ollama", self.fn_restart_ollama)  # DEPRECATED-V5
        add_item("Environment Check", self.fn_env_check)
        add_item("Port Health Check", self.fn_port_check)
        add_item("Task Scheduler Status", self.fn_task_scheduler)  # DEPRECATED-V5
        add_item("Open Codex Folder", self.fn_open_codex)
        add_item("Open Logs", self.fn_open_logs)
        menu.addSeparator()

        # 🧠 VRAM / MODELS
        add_section("🧠 VRAM / MODELS")
        add_item("VRAM Status", self.fn_vram_status)  # DEPRECATED-V5
        add_item("List Loaded Models", self.fn_list_loaded)  # DEPRECATED-V5
        add_item("List All Installed Models", self.fn_list_installed)  # DEPRECATED-V5
        add_item("Model Load Timer", self.fn_model_timer)  # DEPRECATED-V5
        add_item("Clear All VRAM", self.fn_clear_vram)  # DEPRECATED-V5
        menu.addSeparator()

        # 🔍 CODEX HEALTH
        add_section("🔍 CODEX HEALTH")
        add_item("Codex Structure Scan", self.fn_codex_scan)
        add_item("Pending Approvals", self.fn_pending_approvals)
        add_item("Build Order Status", self.fn_build_order_status)
        add_item("Missing CONTEXT.md Scan", self.fn_missing_context)
        add_item("Duplicate ID Scanner", self.fn_duplicate_ids)
        add_item("Last Modified Files", self.fn_last_modified)
        menu.addSeparator()

        # 🛠️ LLM TOOLS
        add_section("🛠️ LLM TOOLS")
        add_item("System Repair", self.fn_llm_repair)
        add_item("System Audit", self.fn_llm_audit)  # DEPRECATED-V5
        add_item("System Test", self.fn_llm_test)  # DEPRECATED-V5
        menu.addSeparator()

        # 📊 TOKEN MONITOR
        add_section("📊 TOKEN MONITOR")
        add_item("View Spike Log", self.fn_view_spike_log)
        add_item("View Session Stats", self.fn_session_stats)
        add_item("Spike Thresholds ⚙", self.fn_spike_thresholds)
        add_item("Export Token Report", self.fn_export_token_report)
        menu.addSeparator()

        # 📋 QUICK ACTIONS
        add_section("📋 QUICK ACTIONS")
        add_item("Copy Last Output", self.fn_copy_last_output)
        add_item("Clear Chat History", self.fn_clear_chat)
        add_item("Save Session Snapshot", self.fn_save_snapshot)
        add_item("Load Previous Snapshot", self.fn_load_snapshot)

        return menu

    # ── STATS TIMER ───────────────────────────────────────────
    def _start_stats_timer(self):
        self._update_stats()
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(10000)

    def _update_stats(self):
        # VRAM — query Ollama
        def update():
            try:
                r = requests.get(f"{OLLAMA_API}/api/ps", timeout=3)  # DEPRECATED-V5
                data = r.json()  # DEPRECATED-V5
                total_vram = sum(m.get("size_vram", 0) for m in data.get("models", []))  # DEPRECATED-V5
                total_size = sum(m.get("size", 0) for m in data.get("models", []))  # DEPRECATED-V5
                vram_mb = total_vram / 1e6  # DEPRECATED-V5
                size_mb = total_size / 1e6  # DEPRECATED-V5
                if total_vram > 0:  # DEPRECATED-V5
                    # GPU active
                    pct = (vram_mb / 8192) * 100  # 8GB VRAM  # DEPRECATED-V5
                    if pct > 80:
                        color = "#ff4060"
                    elif pct > 60:
                        color = "#f0a800"
                    else:
                        color = "#00e5a0"
                    self.vram_label.setText(f"VRAM: {vram_mb:.0f}MB / 8192MB")  # DEPRECATED-V5
                    self.vram_label.setStyleSheet(f"color:{color}; font-family:'JetBrains Mono',monospace; font-size:10px;")
                else:
                    self.vram_label.setText(f"VRAM: CPU ({size_mb:.0f}MB)")  # DEPRECATED-V5
                    self.vram_label.setStyleSheet("color:#f0a800; font-family:'JetBrains Mono',monospace; font-size:10px;")
            except:
                self.vram_label.setText("VRAM: N/A")
                self.vram_label.setStyleSheet("color:#5a8090; font-family:'JetBrains Mono',monospace; font-size:10px;")

            # RAM + CPU
            if HAS_PSUTIL:
                mem = psutil.virtual_memory()
                used_gb = mem.used / 1e9
                total_gb = mem.total / 1e9
                self.ram_label.setText(f"RAM:  {used_gb:.1f}GB / {total_gb:.1f}GB")

                cpu = psutil.cpu_percent(interval=None)
                self.cpu_label.setText(f"CPU:  {cpu:.0f}%")
            else:
                self.ram_label.setText("RAM:  (psutil needed)")
                self.cpu_label.setText("CPU:  (psutil needed)")

            # Token monitor update
            if self.token_tracker:
                stats = self.token_tracker.session_stats()
                self.token_session.setText(f"Session: ↑ {stats['total_prompt']}  ↓ {stats['total_completion']}")
                self.token_last.setText(f"Last:    ↑ {stats['last_prompt']}  ↓ {stats['last_completion']}")
                tpm = self.token_tracker.tokens_per_minute()
                rate_color = "#00e5a0"
                if tpm > 300:
                    rate_color = "#f0a800"
                if tpm > 500:
                    rate_color = "#ff4060"
                self.token_rate.setText(f"Rate:    {tpm:.0f} tok/min")
                self.token_rate.setStyleSheet(f"color:{rate_color}; font-family:'JetBrains Mono',monospace; font-size:9px;")
                self.spike_label.setText(f"Spikes:  {stats['spike_count']}")

        threading.Thread(target=update, daemon=True).start()

    # ── SPIKE ALERT ───────────────────────────────────────────
    def on_spike_detected(self, spike_data):
        """Flash the spike label red for 3 seconds"""
        severity = spike_data.get("severity", "MILD")
        count = spike_data.get("session_spike_count", 0)
        self.spike_label.setText(f"Spikes:  ⚠ {count}")
        self.spike_label.setStyleSheet("color:#ff4060; font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700;")

        if self._spike_flash_timer:
            self._spike_flash_timer.stop()
        self._spike_flash_timer = QTimer(self)
        self._spike_flash_timer.setSingleShot(True)
        self._spike_flash_timer.timeout.connect(
            lambda: self.spike_label.setStyleSheet("color:#ff4060; font-family:'JetBrains Mono',monospace; font-size:9px;")
        )
        self._spike_flash_timer.start(3000)

    # ── THRESHOLD SETTINGS ────────────────────────────────────
    def _load_thresholds(self):
        try:
            if TOKEN_CONFIG_PATH.exists():
                with open(TOKEN_CONFIG_PATH, "r") as f:
                    cfg = json.load(f)
                self.sp_prompt_mult.setValue(cfg.get("prompt_spike_multiplier", 2.0))
                self.sp_comp_mult.setValue(cfg.get("completion_spike_multiplier", 2.0))
                self.sp_max_tpm.setValue(cfg.get("max_tokens_per_min_warning", 500))
                self.sp_warn_wm.setValue(cfg.get("session_warning_watermark", 25000))
                self.sp_crit_wm.setValue(cfg.get("session_critical_watermark", 100000))
                self.cb_ceiling.setChecked(cfg.get("completion_ceiling_flag", True))
                self.cb_bloat.setChecked(cfg.get("context_bloat_detection", True))
                self.cb_retry.setChecked(cfg.get("retry_loop_detection", True))
                self.cb_ratio.setChecked(cfg.get("ratio_flip_detection", True))
                self.sp_max_entries.setValue(cfg.get("spike_log_max_entries", 500))
                self.sp_clear_time.setValue(cfg.get("spike_alert_clear_time", 30))
        except:
            pass

    def _save_thresholds(self):
        cfg = {
            "prompt_spike_multiplier": self.sp_prompt_mult.value(),
            "completion_spike_multiplier": self.sp_comp_mult.value(),
            "max_tokens_per_min_warning": self.sp_max_tpm.value(),
            "session_warning_watermark": self.sp_warn_wm.value(),
            "session_critical_watermark": self.sp_crit_wm.value(),
            "completion_ceiling_flag": self.cb_ceiling.isChecked(),
            "context_bloat_detection": self.cb_bloat.isChecked(),
            "retry_loop_detection": self.cb_retry.isChecked(),
            "ratio_flip_detection": self.cb_ratio.isChecked(),
            "spike_log_max_entries": self.sp_max_entries.value(),
            "spike_alert_clear_time": self.sp_clear_time.value(),
        }
        TOKEN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        # Reload in tracker if available
        if self.token_tracker:
            self.token_tracker.load_config()

    def _reset_thresholds(self):
        self.sp_prompt_mult.setValue(2.0)
        self.sp_comp_mult.setValue(2.0)
        self.sp_max_tpm.setValue(500)
        self.sp_warn_wm.setValue(25000)
        self.sp_crit_wm.setValue(100000)
        self.cb_ceiling.setChecked(True)
        self.cb_bloat.setChecked(True)
        self.cb_retry.setChecked(True)
        self.cb_ratio.setChecked(True)
        self.sp_max_entries.setValue(500)
        self.sp_clear_time.setValue(30)

    # ── HELPER: Run async and show result ─────────────────────
    def _run_async(self, title, fn):
        """Run fn in background thread, show result in dialog"""
        def wrapper():
            try:
                result = fn()
                self._last_tool_output = result
                # Show dialog on main thread
                QTimer.singleShot(0, lambda: self._show_result(title, result))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._show_result(title, f"Error: {str(e)}"))
        threading.Thread(target=wrapper, daemon=True).start()

    def _show_result(self, title, content):
        dlg = ResultDialog(title, content, parent=self.main_window or self)
        dlg.exec()

    def _run_llm_tool(self, title, model, prompt):  # DEPRECATED-V5
        """Run LLM tool: evict models, load tool model, stream result"""  # DEPRECATED-V5
        dlg = ResultDialog(title, "Loading model...", parent=self.main_window or self)
        dlg.show()

        def run():
            try:
                # Evict loaded models
                try:
                    ps = requests.get(f"{OLLAMA_API}/api/ps", timeout=5).json()  # DEPRECATED-V5
                    for m in ps.get("models", []):
                        name = m.get("name", "")
                        if name:
                            requests.post(f"{OLLAMA_API}/api/generate",  # DEPRECATED-V5
                                json={"model": name, "prompt": "", "keep_alive": 0}, timeout=10)  # DEPRECATED-V5
                except:
                    pass

                dlg.append_text(f"\nRunning {model}...\n")  # DEPRECATED-V5

                r = requests.post(f"{OLLAMA_API}/api/chat", json={  # DEPRECATED-V5
                    "model": model,  # DEPRECATED-V5
                    "stream": False,
                    "options": {"num_ctx": 4096},
                    "messages": [{"role": "user", "content": prompt}]
                }, timeout=300)
                r.raise_for_status()
                reply = r.json().get("message", {}).get("content", "No response")
                self._last_tool_output = reply
                dlg.append_text("\n" + reply)

                # Reload foreground model
                try:
                    with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
                        cfg = json.load(f)
                    fg_model = cfg.get("roles", {}).get("foreground", {}).get("model", "llama3.1:8b")  # DEPRECATED-V5
                    requests.post(f"{OLLAMA_API}/api/generate",  # DEPRECATED-V5
                        json={"model": fg_model, "prompt": "", "keep_alive": -1,  # DEPRECATED-V5
                              "options": {"num_ctx": 4096}}, timeout=60)
                except:
                    pass

            except Exception as e:
                dlg.append_text(f"\nError: {str(e)}")

        threading.Thread(target=run, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    # TOOL FUNCTIONS
    # ══════════════════════════════════════════════════════════

    # ── 🖥️ SYSTEM ────────────────────────────────────────────
    def fn_restart_ui(self):
        reply = QMessageBox.question(self, "Restart COI UI",
            "Restart the desktop UI?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            python = sys.executable
            script = str(Path(__file__).parent / "coi-desktop-v4.py")
            subprocess.Popen([python, script])
            sys.exit(0)

    def fn_agent_status(self):
        def check():
            lines = []
            if HAS_PSUTIL:
                found = False
                for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
                    try:
                        cmdline = proc.info.get("cmdline") or []
                        if any("coi-agent" in str(c) for c in cmdline):
                            uptime = datetime.now() - datetime.fromtimestamp(proc.info["create_time"])
                            lines.append(f"COI Agent: RUNNING")
                            lines.append(f"  PID: {proc.info['pid']}")
                            lines.append(f"  Uptime: {str(uptime).split('.')[0]}")
                            found = True
                    except:
                        pass
                if not found:
                    lines.append("COI Agent: NOT RUNNING")
            else:
                lines.append("COI Agent: psutil not installed")

            # Port 7700 check
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            result = s.connect_ex(("localhost", 7700))
            s.close()
            lines.append(f"Port 7700: {'LIVE' if result == 0 else 'CLOSED'}")
            return "\n".join(lines)
        self._run_async("COI Agent Status", check)

    def fn_restart_ollama(self):  # DEPRECATED-V5
        reply = QMessageBox.question(self, "Restart Ollama",  # DEPRECATED-V5
            "This will kill Ollama and restart it. Continue?",  # DEPRECATED-V5
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def restart():
            lines = []
            if HAS_PSUTIL:
                killed = 0
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        if "ollama" in (proc.info["name"] or "").lower():
                            proc.kill()
                            killed += 1
                    except:
                        pass
                lines.append(f"Killed {killed} ollama process(es)")
            else:
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"],
                        capture_output=True, timeout=10)
                    lines.append("Killed ollama via taskkill")
                except:
                    lines.append("Failed to kill ollama")

            import time
            time.sleep(2)

            try:
                subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)  # DEPRECATED-V5
                lines.append("Started: ollama serve")  # DEPRECATED-V5
            except Exception as e:
                lines.append(f"Failed to start: {e}")

            import time
            time.sleep(3)
            try:
                r = requests.get(f"{OLLAMA_API}", timeout=3)  # DEPRECATED-V5
                lines.append("Ollama: ONLINE")  # DEPRECATED-V5
            except:
                lines.append("Ollama: NOT RESPONDING (may need a moment)")  # DEPRECATED-V5
            return "\n".join(lines)
        self._run_async("Restart Ollama", restart)  # DEPRECATED-V5

    def fn_env_check(self):
        def check():
            lines = []
            # Python
            lines.append(f"Python: {sys.version.split()[0]} ✓")

            # PyQt6
            try:
                from PyQt6.QtCore import PYQT_VERSION_STR
                lines.append(f"PyQt6: {PYQT_VERSION_STR} ✓")
            except:
                lines.append("PyQt6: ✗ MISSING")

            # psutil
            if HAS_PSUTIL:
                lines.append(f"psutil: {psutil.__version__} ✓")
            else:
                lines.append("psutil: ✗ MISSING (pip install psutil)")

            # requests
            try:
                lines.append(f"requests: {requests.__version__} ✓")
            except:
                lines.append("requests: ✗ MISSING")

            # Ollama
            try:
                r = requests.get(f"{OLLAMA_API}", timeout=3)  # DEPRECATED-V5
                lines.append("Ollama (11434): ✓ reachable")  # DEPRECATED-V5
            except:
                lines.append("Ollama (11434): ✗ unreachable")  # DEPRECATED-V5

            # Bridge
            try:
                r = requests.get("http://localhost:11435/health", timeout=3)
                lines.append("Bridge (11435): ✓ reachable")
            except:
                lines.append("Bridge (11435): ✗ unreachable")

            return "\n".join(lines)
        self._run_async("Environment Check", check)

    def fn_port_check(self):
        def check():
            ports = {"Ollama": 11434, "Bridge": 11435, "Agent": 7700, "HTTP": 8080}  # DEPRECATED-V5
            lines = []
            for name, port in ports.items():
                import time
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                start = time.time()
                result = s.connect_ex(("localhost", port))
                elapsed = (time.time() - start) * 1000
                s.close()
                status = "LIVE" if result == 0 else "DEAD"
                lines.append(f":{port} {name:8s} {status} ({elapsed:.0f}ms)")
            return "\n".join(lines)
        self._run_async("Port Health Check", check)

    def fn_task_scheduler(self):  # DEPRECATED-V5
        def check():
            try:
                r = subprocess.run(
                    ["schtasks", "/query", "/tn", "\\COI*", "/fo", "LIST"],
                    capture_output=True, text=True, timeout=10
                )
                output = r.stdout.strip()
                if output:
                    return output
                return "No COI scheduled tasks found."
            except FileNotFoundError:
                return "schtasks not available"
            except subprocess.TimeoutExpired:
                return "schtasks timed out"
            except Exception as e:
                return f"Error: {e}"
        self._run_async("Task Scheduler Status", check)

    def fn_open_codex(self):
        os.startfile(str(ICM_ROOT))

    def fn_open_logs(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        logs = sorted(LOGS_DIR.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
        if logs:
            subprocess.Popen(["notepad.exe", str(logs[0])])
        else:
            # Open the logs folder instead
            os.startfile(str(LOGS_DIR))

    # ── 🧠 VRAM / MODELS ─────────────────────────────────────
    def fn_vram_status(self):  # DEPRECATED-V5
        def check():  # DEPRECATED-V5
            try:
                r = requests.get(f"{OLLAMA_API}/api/ps", timeout=5)  # DEPRECATED-V5
                data = r.json()
                models = data.get("models", [])
                if not models:
                    return "No models loaded in VRAM."
                lines = []
                for m in models:
                    name = m.get("name", "?")
                    size_gb = m.get("size", 0) / 1e9
                    vram_gb = m.get("size_vram", 0) / 1e9
                    expires = m.get("expires_at", "unknown")
                    lines.append(f"{name}")
                    lines.append(f"  Total: {size_gb:.1f}GB  VRAM: {vram_gb:.1f}GB")
                    lines.append(f"  Expires: {expires[:19]}")
                    lines.append("")
                return "\n".join(lines)
            except Exception as e:
                return f"Error: {e}"
        self._run_async("VRAM Status", check)

    def fn_list_loaded(self):
        self.fn_vram_status()

    def fn_list_installed(self):  # DEPRECATED-V5
        def check():  # DEPRECATED-V5
            try:
                r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)  # DEPRECATED-V5
                models = r.json().get("models", [])
                lines = [f"{'Model':<35s} {'Size':>8s}  {'Modified'}"]
                lines.append("-" * 65)
                for m in sorted(models, key=lambda x: x["name"]):
                    name = m["name"]
                    size = f"{m.get('size', 0)/1e9:.1f}GB"
                    modified = m.get("modified_at", "?")[:10]
                    lines.append(f"{name:<35s} {size:>8s}  {modified}")
                lines.append(f"\nTotal: {len(models)} models")
                return "\n".join(lines)
            except Exception as e:
                return f"Error: {e}"
        self._run_async("All Installed Models", check)

    def fn_model_timer(self):
        def check():
            timer_path = LOGS_DIR / "model_load_times.json"
            if not timer_path.exists():
                return "No model load times recorded yet."
            try:
                with open(timer_path, "r") as f:
                    data = json.load(f)
                lines = [f"{'Model':<30s} {'Load Time':>10s}  {'When'}"]
                lines.append("-" * 60)
                for entry in data[-20:]:
                    lines.append(f"{entry['model']:<30s} {entry['time_s']:>8.1f}s  {entry['timestamp'][:19]}")
                return "\n".join(lines)
            except Exception as e:
                return f"Error: {e}"
        self._run_async("Model Load Times", check)

    def fn_clear_vram(self):  # DEPRECATED-V5
        reply = QMessageBox.question(self, "Clear VRAM",  # DEPRECATED-V5
            "Unload all models from VRAM?",  # DEPRECATED-V5
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def clear():
            try:
                r = requests.get(f"{OLLAMA_API}/api/ps", timeout=5)  # DEPRECATED-V5
                models = r.json().get("models", [])  # DEPRECATED-V5
                evicted = 0
                for m in models:
                    name = m.get("name", "")
                    if name:
                        requests.post(f"{OLLAMA_API}/api/generate",  # DEPRECATED-V5
                            json={"model": name, "prompt": "", "keep_alive": 0}, timeout=10)  # DEPRECATED-V5
                        evicted += 1
                return f"Evicted {evicted} model(s) from VRAM."  # DEPRECATED-V5
            except Exception as e:
                return f"Error: {e}"
        self._run_async("Clear VRAM", clear)

    # ── 🔍 CODEX HEALTH ──────────────────────────────────────
    def fn_codex_scan(self):
        def scan():
            lines = []
            folder_count = 0
            file_count = 0
            empty_folders = []
            issues = []

            for root, dirs, files in os.walk(str(ICM_ROOT)):
                # Skip .git and node_modules
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".claude")]
                folder_count += 1
                file_count += len(files)
                if not files and not dirs:
                    rel = os.path.relpath(root, str(ICM_ROOT))
                    empty_folders.append(rel)

            # Key files check
            key_files = ["COI/00-constitution/COI-Constitution.md",
                         "COI/00-constitution/SUCCESSION.md",
                         "COI/L1-Routing/CODEX-MAP.md"]
            for kf in key_files:
                if not (ICM_ROOT / kf).exists():
                    issues.append(f"MISSING: {kf}")

            lines.append(f"Folders: {folder_count}")
            lines.append(f"Files: {file_count}")
            if empty_folders:
                lines.append(f"\nEmpty folders ({len(empty_folders)}):")
                for ef in empty_folders[:10]:
                    lines.append(f"  {ef}")
            if issues:
                lines.append(f"\nIssues ({len(issues)}):")
                for i in issues:
                    lines.append(f"  {i}")
            else:
                lines.append("\nKey files: all present ✓")
            return "\n".join(lines)
        self._run_async("Codex Structure Scan", scan)

    def fn_pending_approvals(self):
        def check():
            inbox = ICM_ROOT / "inbox"
            if not inbox.exists():
                return "No inbox folder found."
            files = list(inbox.iterdir())
            if not files:
                return "No pending approvals."
            lines = [f"{len(files)} pending item(s):\n"]
            for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                lines.append(f"  {f.name}  ({mtime})")
            return "\n".join(lines)
        self._run_async("Pending Approvals", check)

    def fn_build_order_status(self):
        def check():
            counts = {"Complete": 0, "In-Progress": 0, "Blocked": 0, "Not-Started": 0, "Other": 0}
            bo_items = {}

            for md_file in ICM_ROOT.rglob("*.md"):
                if ".git" in str(md_file):
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8", errors="ignore")
                    # Find BO-XXX patterns
                    ids = re.findall(r"(BO-\d{3})", content)
                    for bo_id in ids:
                        if bo_id not in bo_items:
                            bo_items[bo_id] = md_file.name

                    # Parse status fields
                    for match in re.finditer(r"BO-\d{3}.*?Status:\s*(\w[\w\s-]*)", content, re.IGNORECASE):
                        status = match.group(1).strip()
                        if "complete" in status.lower():
                            counts["Complete"] += 1
                        elif "progress" in status.lower() or "active" in status.lower():
                            counts["In-Progress"] += 1
                        elif "block" in status.lower():
                            counts["Blocked"] += 1
                        elif "not" in status.lower() or "pending" in status.lower():
                            counts["Not-Started"] += 1
                        else:
                            counts["Other"] += 1
                except:
                    pass

            lines = [f"Build Order Items Found: {len(bo_items)}\n"]
            for status, count in counts.items():
                if count > 0:
                    lines.append(f"  {status}: {count}")
            return "\n".join(lines)
        self._run_async("Build Order Status", check)

    def fn_missing_context(self):
        def scan():
            missing = []
            skip = {".git", "node_modules", "__pycache__", ".claude", "config", "logs", "inbox"}
            for root, dirs, files in os.walk(str(ICM_ROOT)):
                dirs[:] = [d for d in dirs if d not in skip]
                rel = os.path.relpath(root, str(ICM_ROOT))
                if rel == ".":
                    continue
                # Only check pipeline and COI directories
                if not (rel.startswith("pipeline") or rel.startswith("COI")):
                    continue
                if "CONTEXT.md" not in files and files:
                    missing.append(rel)

            if not missing:
                return "All directories have CONTEXT.md ✓"
            lines = [f"{len(missing)} directories missing CONTEXT.md:\n"]
            for m in sorted(missing)[:30]:
                lines.append(f"  {m}")
            return "\n".join(lines)
        self._run_async("Missing CONTEXT.md", scan)

    def fn_duplicate_ids(self):
        def scan():
            id_locations = {}
            for md_file in ICM_ROOT.rglob("*.md"):
                if ".git" in str(md_file):
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8", errors="ignore")
                    ids = re.findall(r"(BO-\d{3})", content)
                    for bo_id in set(ids):
                        if bo_id not in id_locations:
                            id_locations[bo_id] = []
                        id_locations[bo_id].append(md_file.name)
                except:
                    pass

            dupes = {k: v for k, v in id_locations.items() if len(v) > 1}
            if not dupes:
                return "No duplicate BO-IDs found ✓"
            lines = [f"{len(dupes)} BO-IDs appear in multiple files:\n"]
            for bo_id, files in sorted(dupes.items()):
                lines.append(f"  {bo_id}: {', '.join(set(files))}")
            return "\n".join(lines)
        self._run_async("Duplicate ID Scanner", scan)

    def fn_last_modified(self):
        def scan():
            files = []
            skip = {".git", "node_modules", "__pycache__"}
            for root, dirs, filenames in os.walk(str(ICM_ROOT)):
                dirs[:] = [d for d in dirs if d not in skip]
                for fn in filenames:
                    fp = Path(root) / fn
                    try:
                        mtime = fp.stat().st_mtime
                        rel = fp.relative_to(ICM_ROOT)
                        files.append((mtime, str(rel), fn))
                    except:
                        pass
            files.sort(reverse=True)
            lines = ["Top 10 most recently modified:\n"]
            for mtime, rel, fn in files[:10]:
                ts = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                lines.append(f"  {ts}  {rel}")
            return "\n".join(lines)
        self._run_async("Last Modified Files", scan)

    # ── 🛠️ LLM TOOLS ─────────────────────────────────────────

    def _gather_system_state(self):
        """Collect real system state for LLM tools to analyze."""
        state_lines = []

        # Ollama status
        try:
            r = requests.get(f"{OLLAMA_API}/api/ps", timeout=5)  # DEPRECATED-V5
            ps = r.json()  # DEPRECATED-V5
            loaded = [m.get("name", "?") for m in ps.get("models", [])]  # DEPRECATED-V5
            state_lines.append(f"LOADED MODELS: {', '.join(loaded) if loaded else 'none'}")  # DEPRECATED-V5
        except Exception:
            state_lines.append("OLLAMA: unreachable")  # DEPRECATED-V5

        # Available models
        try:
            r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)  # DEPRECATED-V5
            models = [m["name"] for m in r.json().get("models", [])]  # DEPRECATED-V5
            state_lines.append(f"AVAILABLE MODELS: {', '.join(models)}")  # DEPRECATED-V5
        except Exception:
            pass

        # Model config
        try:
            with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
                cfg = json.load(f)  # DEPRECATED-V5
            roles = cfg.get("roles", {})  # DEPRECATED-V5
            for role, info in roles.items():  # DEPRECATED-V5
                state_lines.append(f"ROLE {role}: {info.get('model', '?')} (score: {info.get('score', '?')})")  # DEPRECATED-V5
        except Exception:
            state_lines.append("MODEL CONFIG: could not load")  # DEPRECATED-V5

        # Key files check
        key_files = {
            "CLAUDE.md": ICM_ROOT / "CLAUDE.md",
            "COI-Personality.md": ICM_ROOT / "COI" / "L3-Reference" / "COI-Personality.md",
            "next-session-briefing.md": ICM_ROOT / "COI" / "L4-Working" / "memory" / "next-session-briefing.md",
            "MASTER-BUILD-ORDER.md": ICM_ROOT / "COI" / "L1-Routing" / "MASTER-BUILD-ORDER.md",
            "config.json": ICM_ROOT / "config" / "config.json",
            "coi-orchestrator.py": ICM_ROOT / "scripts" / "coi-orchestrator.py",
            "coi-bridge.py": ICM_ROOT / "scripts" / "coi-bridge.py",
            "coi-desktop-v4.py": ICM_ROOT / "ui" / "coi-desktop-v4.py",
        }
        missing = []
        present = []
        for name, path in key_files.items():
            if path.exists():
                present.append(name)
            else:
                missing.append(name)
        state_lines.append(f"KEY FILES PRESENT: {', '.join(present)}")
        if missing:
            state_lines.append(f"KEY FILES MISSING: {', '.join(missing)}")

        # Memory files
        mem_dir = ICM_ROOT / "COI" / "L4-Working" / "memory"
        if mem_dir.exists():
            mem_files = list(mem_dir.glob("*.md"))
            state_lines.append(f"MEMORY FILES: {len(mem_files)}")
            for mf in mem_files:
                try:
                    age_h = (datetime.now() - datetime.fromtimestamp(mf.stat().st_mtime)).total_seconds() / 3600
                    state_lines.append(f"  {mf.name}: {mf.stat().st_size} bytes, {age_h:.1f}h old")
                except Exception:
                    pass

        # Pipeline stages
        pipeline_dir = ICM_ROOT / "pipeline"
        if pipeline_dir.exists():
            stages = sorted([d.name for d in pipeline_dir.iterdir() if d.is_dir()])
            state_lines.append(f"PIPELINE STAGES: {', '.join(stages) if stages else 'none'}")
            for stage in stages:
                ctx = pipeline_dir / stage / "CONTEXT.md"
                state_lines.append(f"  {stage}: CONTEXT.md {'present' if ctx.exists() else 'MISSING'}")

        # Open loops
        loops_path = mem_dir / "open-loops.md"
        if loops_path.exists():
            try:
                content = loops_path.read_text(encoding="utf-8")
                open_count = content.count("| Open |")
                state_lines.append(f"OPEN LOOPS: {open_count}")
            except Exception:
                pass

        # Sessions
        sess_dir = ICM_ROOT / "COI" / "L4-Working" / "sessions"
        if sess_dir.exists():
            all_sess = list(sess_dir.glob("*.md"))
            processed = list(sess_dir.glob("*.processed"))
            state_lines.append(f"SESSIONS: {len(all_sess)} total, {len(processed)} processed")

        # Bridge status
        try:
            r = requests.get("http://localhost:11435/health", timeout=3)
            state_lines.append(f"BRIDGE: online (port 11435)")
        except Exception:
            state_lines.append("BRIDGE: offline")

        # Recent runtime errors from COI Desktop
        if self.main_window and hasattr(self.main_window, '_recent_errors'):
            errors = self.main_window._recent_errors
            if errors:
                state_lines.append(f"\nRECENT ERRORS ({len(errors)}):")
                for err in errors:
                    state_lines.append(f"  [{err['time']}] {err['error']}")
            else:
                state_lines.append("\nRECENT ERRORS: none")
        else:
            state_lines.append("\nRECENT ERRORS: none captured yet")

        # Error memory — known past failures
        error_mem = ICM_ROOT / "COI" / "L4-Working" / "memory" / "error-memory.md"
        if error_mem.exists():
            try:
                content = error_mem.read_text(encoding="utf-8")
                # Get last 5 entries (skip header lines)
                lines = [l for l in content.strip().split("\n") if l.startswith("| 20")]
                if lines:
                    state_lines.append(f"\nERROR HISTORY (last {min(5, len(lines))}):")
                    for l in lines[-5:]:
                        state_lines.append(f"  {l}")
            except Exception:
                pass

        # Diagnostic results if available
        diag_path = ICM_ROOT / "COI" / "L4-Working" / "memory" / "diagnostic-results.md"
        if diag_path.exists():
            try:
                content = diag_path.read_text(encoding="utf-8")
                fail_lines = [l for l in content.split("\n") if "FAIL" in l]
                warn_lines = [l for l in content.split("\n") if "WARN" in l]
                if fail_lines or warn_lines:
                    state_lines.append(f"\nDIAGNOSTIC FAILURES:")
                    for l in fail_lines[:10]:
                        state_lines.append(f"  {l.strip()}")
                    for l in warn_lines[:5]:
                        state_lines.append(f"  {l.strip()}")
                else:
                    state_lines.append("\nDIAGNOSTICS: all passing")
            except Exception:
                pass

        return "\n".join(state_lines)

    def fn_llm_repair(self):
        """Deterministic system repair — Python checks first, LLM only for content generation."""
        dlg = ResultDialog("System Repair", "Scanning system (deterministic checks)...",
                           parent=self.main_window or self)
        dlg.show()

        def run():
            try:
                issues = self._run_deterministic_scan(dlg)
                self._last_tool_output = "\n".join(
                    f"[{i['severity']}] {i['issue']}" for i in issues
                ) if issues else "No issues found."

                if issues:
                    dlg.append_text(f"\n\n{'='*50}")
                    dlg.append_text(f"SCAN COMPLETE: {len(issues)} issue(s) found")
                    dlg.append_text(f"  CRITICAL: {sum(1 for i in issues if i['severity']=='CRITICAL')}")
                    dlg.append_text(f"  WARNING:  {sum(1 for i in issues if i['severity']=='WARNING')}")
                    dlg.append_text(f"  INFO:     {sum(1 for i in issues if i['severity']=='INFO')}")
                    fixable = [i for i in issues if i.get("auto_fix")]
                    if fixable:
                        dlg.append_text(f"\n{len(fixable)} auto-fixable issue(s). Opening approval queue...")
                        self._show_repair_fixes.emit("", fixable)
                    else:
                        dlg.append_text("\nNo auto-fixable issues — all require manual attention.")
                else:
                    dlg.append_text("\n\nAll checks passed. System is healthy.")

            except Exception as e:
                dlg.append_text(f"\nScan error: {str(e)}")

        threading.Thread(target=run, daemon=True).start()

    def _run_deterministic_scan(self, dlg):
        """Run all deterministic system checks. Returns list of issue dicts."""
        issues = []

        def check(name, fn):
            dlg.append_text(f"\n  Checking {name}...")
            try:
                result = fn()
                if result:
                    issues.extend(result if isinstance(result, list) else [result])
                    for r in (result if isinstance(result, list) else [result]):
                        sev = r.get("severity", "INFO")
                        dlg.append_text(f"    [{sev}] {r['issue']}")
                else:
                    dlg.append_text(f"    PASS")
            except Exception as e:
                dlg.append_text(f"    ERROR: {str(e)[:100]}")

        dlg.append_text("\n--- SERVICES ---")
        check("Ollama status", self._check_ollama)
        check("Bridge status", self._check_bridge)

        dlg.append_text("\n--- MODELS ---")
        check("Required models", self._check_required_models)
        check("Model config", self._check_model_config)
        check("Foreground model loaded", self._check_foreground_loaded)

        dlg.append_text("\n--- KEY FILES ---")
        check("Core files", self._check_core_files)
        check("Config file", self._check_config)
        check("Scripts syntax", self._check_script_syntax)
        check("UI syntax", self._check_ui_syntax)

        dlg.append_text("\n--- PIPELINE ---")
        check("Pipeline stages", self._check_pipeline)

        dlg.append_text("\n--- MEMORY ---")
        check("Memory freshness", self._check_memory_freshness)
        check("Briefing file", self._check_briefing)

        dlg.append_text("\n--- RUNTIME ---")
        check("Recent errors", self._check_recent_errors)
        check("Diagnostic results", self._check_diagnostics)

        return issues

    # ── INDIVIDUAL CHECKS ─────────────────────────────────────

    def _check_ollama(self):  # DEPRECATED-V5
        try:
            r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)  # DEPRECATED-V5
            r.raise_for_status()
            return None
        except Exception as e:
            return {"severity": "CRITICAL", "issue": f"Ollama unreachable: {str(e)[:80]}",  # DEPRECATED-V5
                    "auto_fix": False, "type": "manual",
                    "content": "Start Ollama: run 'ollama serve' or launch from system tray"}  # DEPRECATED-V5

    def _check_bridge(self):
        try:
            r = requests.get("http://localhost:11435/health", timeout=3)
            r.raise_for_status()
            return None
        except Exception:
            return {"severity": "WARNING", "issue": "COI Bridge offline (port 11435)",
                    "auto_fix": False, "type": "manual",
                    "content": "Start bridge: python scripts/coi-bridge.py"}

    def _check_required_models(self):  # DEPRECATED-V5
        required = {  # DEPRECATED-V5
            "llama3.1:8b": "orchestrator/foreground",  # DEPRECATED-V5
            "deepseek-coder-v2:lite": "code generation",  # DEPRECATED-V5
            "dolphin3:8b": "code review",  # DEPRECATED-V5
            "llama3.2:3b": "classifier/fallback",  # DEPRECATED-V5
            "mistral:latest": "executor",  # DEPRECATED-V5
        }
        try:
            r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)  # DEPRECATED-V5
            available = [m["name"] for m in r.json().get("models", [])]
            issues = []
            for model, role in required.items():
                # Check with and without tag suffix
                found = any(model in a or a.startswith(model.split(":")[0]) for a in available)
                if not found:
                    issues.append({
                        "severity": "WARNING",
                        "issue": f"Model '{model}' not installed (used for: {role})",
                        "auto_fix": False, "type": "manual",
                        "content": f"Run: ollama pull {model}"
                    })
            return issues if issues else None
        except Exception:
            return None  # Ollama check already covers this

    def _check_model_config(self):  # DEPRECATED-V5
        if not MODEL_CONFIG_PATH.exists():  # DEPRECATED-V5
            return {"severity": "CRITICAL", "issue": "model-config.json missing",  # DEPRECATED-V5
                    "auto_fix": False, "type": "manual",
                    "content": "Recreate scripts/model-config.json with role assignments"}  # DEPRECATED-V5
        try:
            with open(MODEL_CONFIG_PATH, "r") as f:
                cfg = json.load(f)
            issues = []
            roles = cfg.get("roles", {})
            required_roles = ["orchestrator", "generator", "reviewer", "classifier",
                              "executor", "foreground", "fallback"]
            for role in required_roles:
                if role not in roles:
                    issues.append({
                        "severity": "WARNING",
                        "issue": f"Role '{role}' missing from model-config.json",
                        "auto_fix": False, "type": "manual",
                        "content": f"Add '{role}' entry to scripts/model-config.json roles"
                    })
            return issues if issues else None
        except json.JSONDecodeError as e:
            return {"severity": "CRITICAL", "issue": f"model-config.json invalid JSON: {e}",
                    "auto_fix": False, "type": "manual",
                    "content": "Fix JSON syntax in scripts/model-config.json"}

    def _check_foreground_loaded(self):  # DEPRECATED-V5
        try:
            with open(MODEL_CONFIG_PATH, "r") as f:  # DEPRECATED-V5
                cfg = json.load(f)
            fg_model = cfg.get("roles", {}).get("foreground", {}).get("model", "llama3.1:8b")  # DEPRECATED-V5
            r = requests.get(f"{OLLAMA_API}/api/ps", timeout=5)  # DEPRECATED-V5
            loaded = [m.get("name", "") for m in r.json().get("models", [])]  # DEPRECATED-V5
            if not any(fg_model in m for m in loaded):
                return {"severity": "WARNING",
                        "issue": f"Foreground model '{fg_model}' not loaded in VRAM",
                        "auto_fix": True, "type": "reload_foreground",
                        "content": f"Reload {fg_model} into VRAM with keep_alive=-1",
                        "path": "N/A", "model": fg_model}
            return None
        except Exception:
            return None

    def _check_core_files(self):
        core = {
            "CLAUDE.md": ICM_ROOT / "CLAUDE.md",
            "COI-Personality.md": ICM_ROOT / "COI" / "L3-Reference" / "COI-Personality.md",
            "QUICK-LOAD.md": ICM_ROOT / "COI" / "L1-Routing" / "QUICK-LOAD.md",
            "MASTER-BUILD-ORDER.md": ICM_ROOT / "COI" / "L1-Routing" / "MASTER-BUILD-ORDER.md",
            "COI-MISSION-CRITICAL.md": ICM_ROOT / "COI-MISSION-CRITICAL.md",
        }
        issues = []
        for name, path in core.items():
            if not path.exists():
                issues.append({
                    "severity": "CRITICAL", "issue": f"Core file missing: {name}",
                    "auto_fix": False, "type": "manual", "path": str(path.relative_to(ICM_ROOT)),
                    "content": f"Restore {name} — this is a critical system file"
                })
            elif path.stat().st_size == 0:
                issues.append({
                    "severity": "WARNING", "issue": f"Core file empty: {name}",
                    "auto_fix": False, "type": "manual", "path": str(path.relative_to(ICM_ROOT)),
                    "content": f"{name} exists but is empty — needs content"
                })
        return issues if issues else None

    def _check_config(self):
        config_path = ICM_ROOT / "config" / "config.json"
        if not config_path.exists():
            return {"severity": "CRITICAL", "issue": "config/config.json missing",
                    "auto_fix": True, "type": "create_file",
                    "path": "config/config.json",
                    "content": json.dumps({"anthropic_api_key": "", "_note": "Add your API key"}, indent=2)}
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
            if not cfg.get("anthropic_api_key"):
                return {"severity": "INFO", "issue": "No Anthropic API key in config (Claude escalation disabled)",
                        "auto_fix": False, "type": "manual",
                        "content": "Add 'anthropic_api_key' to config/config.json for Claude fallback"}
            return None
        except json.JSONDecodeError as e:
            return {"severity": "CRITICAL", "issue": f"config.json invalid JSON: {e}",
                    "auto_fix": False, "type": "manual",
                    "content": "Fix JSON syntax in config/config.json"}

    def _check_script_syntax(self):
        import ast
        scripts = [
            "scripts/coi-bridge.py", "scripts/coi-orchestrator.py",
            "scripts/coi-briefing.py", "scripts/coi-diagnostic.py",  # DEPRECATED-V5
            "scripts/coi-tools.py", "scripts/coi-codex-intelligence.py",
            "scripts/coi-systems-test.py", "scripts/coi-log-watcher.py",  # DEPRECATED-V5
            "scripts/session-intelligence.py", "scripts/coi-benchmark.py",  # DEPRECATED-V5
        ]
        issues = []
        for script in scripts:
            path = ICM_ROOT / script
            if not path.exists():
                continue
            try:
                source = path.read_text(encoding="utf-8")
                ast.parse(source)
            except SyntaxError as e:
                issues.append({
                    "severity": "CRITICAL",
                    "issue": f"Syntax error in {script}: line {e.lineno} — {e.msg}",
                    "auto_fix": False, "type": "manual", "path": script,
                    "content": f"Fix syntax error at line {e.lineno}: {e.msg}\n{e.text or ''}"
                })
        return issues if issues else None

    def _check_ui_syntax(self):
        import ast
        ui_files = [
            "ui/coi-desktop-v4.py", "ui/coi_tools_panel.py",
            "ui/coi_token_tracker.py", "ui/coi_tools_worker.py",
            "ui/coi_dropoff_panel.py", "ui/coi_dropoff_worker.py",
        ]
        issues = []
        for ui_file in ui_files:
            path = ICM_ROOT / ui_file
            if not path.exists():
                continue
            try:
                source = path.read_text(encoding="utf-8")
                ast.parse(source)
            except SyntaxError as e:
                issues.append({
                    "severity": "CRITICAL",
                    "issue": f"Syntax error in {ui_file}: line {e.lineno} — {e.msg}",
                    "auto_fix": False, "type": "manual", "path": ui_file,
                    "content": f"Fix syntax error at line {e.lineno}: {e.msg}\n{e.text or ''}"
                })
        return issues if issues else None

    def _check_pipeline(self):
        pipeline_dir = ICM_ROOT / "pipeline"
        if not pipeline_dir.exists():
            return {"severity": "WARNING", "issue": "Pipeline directory missing",
                    "auto_fix": True, "type": "create_dir", "path": "pipeline",
                    "content": "Create pipeline directory"}
        expected = ["01-intake", "02-generate", "03-review", "04-sandbox", "05-dave-approval", "06-deploy"]
        issues = []
        for stage in expected:
            stage_dir = pipeline_dir / stage
            if not stage_dir.exists():
                issues.append({
                    "severity": "WARNING",
                    "issue": f"Pipeline stage missing: {stage}",
                    "auto_fix": True, "type": "create_dir",
                    "path": f"pipeline/{stage}",
                    "content": f"Create pipeline stage directory: {stage}"
                })
            else:
                ctx = stage_dir / "CONTEXT.md"
                if not ctx.exists():
                    issues.append({
                        "severity": "WARNING",
                        "issue": f"CONTEXT.md missing in pipeline/{stage}",
                        "auto_fix": True, "type": "create_file",
                        "path": f"pipeline/{stage}/CONTEXT.md",
                        "content": f"# {stage}\n\nPipeline stage contract. Define inputs, outputs, and rules.\n"
                    })
        return issues if issues else None

    def _check_memory_freshness(self):
        critical_memory = {
            "next-session-briefing.md": 48,   # Should update every session
            "open-loops.md": 72,              # Should be reviewed regularly
            "decisions.md": 168,              # Weekly is fine
        }
        mem_dir = ICM_ROOT / "COI" / "L4-Working" / "memory"
        issues = []
        for filename, max_hours in critical_memory.items():
            path = mem_dir / filename
            if not path.exists():
                issues.append({
                    "severity": "WARNING", "issue": f"Memory file missing: {filename}",
                    "auto_fix": False, "type": "manual",
                    "content": f"Create COI/L4-Working/memory/{filename}"
                })
            else:
                try:
                    age_hours = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).total_seconds() / 3600
                    if age_hours > max_hours:
                        issues.append({
                            "severity": "INFO",
                            "issue": f"Memory file stale: {filename} ({age_hours:.0f}h old, threshold {max_hours}h)",
                            "auto_fix": False, "type": "manual",
                            "content": f"Review and update COI/L4-Working/memory/{filename}"
                        })
                except Exception:
                    pass
        return issues if issues else None

    def _check_briefing(self):
        path = ICM_ROOT / "COI" / "L4-Working" / "memory" / "next-session-briefing.md"
        if not path.exists():
            return {"severity": "WARNING", "issue": "Session briefing file missing",
                    "auto_fix": True, "type": "create_file",
                    "path": "COI/L4-Working/memory/next-session-briefing.md",
                    "content": "# Next Session Briefing\n\nNo briefing generated yet.\n"}
        try:
            content = path.read_text(encoding="utf-8")
            if len(content.strip()) < 20:
                return {"severity": "INFO", "issue": "Session briefing is mostly empty",
                        "auto_fix": False, "type": "manual",
                        "content": "Run briefing processor to populate next-session-briefing.md"}
        except Exception:
            pass
        return None

    def _check_recent_errors(self):
        if not self.main_window or not hasattr(self.main_window, '_recent_errors'):
            return None
        errors = self.main_window._recent_errors
        if not errors:
            return None
        issues = []
        # Group by similar error messages
        seen = {}
        for err in errors:
            key = err["error"][:60]
            if key not in seen:
                seen[key] = 0
            seen[key] += 1
        for msg, count in seen.items():
            sev = "CRITICAL" if count >= 3 else "WARNING" if count >= 2 else "INFO"
            issues.append({
                "severity": sev,
                "issue": f"Runtime error ({count}x): {msg}",
                "auto_fix": False, "type": "manual",
                "content": f"Error occurred {count} time(s) this session. Investigate and fix root cause."
            })
        return issues if issues else None

    def _check_diagnostics(self):
        diag_path = ICM_ROOT / "COI" / "L4-Working" / "memory" / "diagnostic-results.md"
        if not diag_path.exists():
            return {"severity": "INFO", "issue": "No diagnostic results found — diagnostics never run",
                    "auto_fix": False, "type": "manual",
                    "content": "Run: python scripts/coi-diagnostic.py"}  # DEPRECATED-V5
        try:
            content = diag_path.read_text(encoding="utf-8")
            fails = [l.strip() for l in content.split("\n") if "| FAIL |" in l]
            if fails:
                issues = []
                for f in fails[:5]:
                    issues.append({
                        "severity": "WARNING",
                        "issue": f"Diagnostic failure: {f[:100]}",
                        "auto_fix": False, "type": "manual",
                        "content": f"Investigate: {f}"
                    })
                return issues
        except Exception:
            pass
        return None

    # ── REPAIR FIX APPROVAL + EXECUTION ───────────────────────

    def _on_repair_fixes_ready(self, raw_report, fixes):
        """Show repair approval dialogs — runs on main thread."""
        approved = 0
        skipped = 0
        for i, fix in enumerate(fixes, 1):
            dlg = RepairApprovalDialog(fix, i, len(fixes), parent=self.main_window or self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._execute_repair_fix(fix)
                approved += 1
            else:
                skipped += 1

        if self.main_window and hasattr(self.main_window, 'append_message'):
            self.main_window.append_message(
                "COI",
                f"[Repair] {approved} fix(es) applied, {skipped} skipped.",
                "#00e5a0" if approved > 0 else "#f0a800"
            )

    def _execute_repair_fix(self, fix):
        """Execute an approved repair fix."""
        fix_type = fix.get("type", "manual")
        path_str = fix.get("path", "N/A")
        content = fix.get("content", "")
        msg = self.main_window.append_message if self.main_window and hasattr(self.main_window, 'append_message') else None

        try:
            if fix_type == "create_file" and path_str != "N/A":
                target = ICM_ROOT / path_str
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                if msg:
                    msg("COI", f"[Repair] Created: {path_str}", "#00e5a0")

            elif fix_type == "create_dir" and path_str != "N/A":
                target = ICM_ROOT / path_str
                target.mkdir(parents=True, exist_ok=True)
                if msg:
                    msg("COI", f"[Repair] Created directory: {path_str}", "#00e5a0")

            elif fix_type == "reload_foreground":  # DEPRECATED-V5
                model = fix.get("model", "llama3.1:8b")  # DEPRECATED-V5
                requests.post(f"{OLLAMA_API}/api/generate", json={  # DEPRECATED-V5
                    "model": model, "prompt": "", "keep_alive": -1  # DEPRECATED-V5
                }, timeout=30)
                if msg:
                    msg("COI", f"[Repair] Reloaded foreground model: {model}", "#00e5a0")

            elif fix_type == "manual":
                if msg:
                    msg("COI", f"[Repair] Manual: {fix.get('issue', '?')} — {content}", "#f0a800")

            else:
                if msg:
                    msg("COI", f"[Repair] Unknown fix type '{fix_type}' — logged for review", "#f0a800")

        except Exception as e:
            if msg:
                msg("COI", f"[Repair] Fix failed: {str(e)[:150]}", "#ff4060")

    def fn_llm_audit(self):  # DEPRECATED-V5
        state = self._gather_system_state()
        self._run_llm_tool("System Audit", "llama3.1:8b",  # DEPRECATED-V5
            f"You are COI's system auditor. Below is the ACTUAL current system state. "
            f"Audit it for: missing dependencies, security gaps, inefficient configurations, "
            f"agent role overlaps, stale memory files, and pipeline completeness. "
            f"Produce a structured report with PASS/FAIL/WARN per category.\n\n"
            f"SYSTEM STATE:\n{state}")

    def fn_llm_test(self):  # DEPRECATED-V5
        state = self._gather_system_state()
        self._run_llm_tool("System Test", "dolphin3:8b",  # DEPRECATED-V5
            f"You are COI's test agent. Below is the ACTUAL current system state. "
            f"Test COI's readiness: are all required models available? Are memory files current? "
            f"Is the pipeline complete? Are key files present? Is the bridge running? "
            f"For each area report PASS/FAIL with reasoning based on the data below.\n\n"
            f"SYSTEM STATE:\n{state}")

    # ── 📊 TOKEN MONITOR ─────────────────────────────────────
    def fn_view_spike_log(self):
        def load():
            spike_path = LOGS_DIR / "token_spikes.json"
            if not spike_path.exists():
                return "No spike log found."
            try:
                with open(spike_path, "r") as f:
                    spikes = json.load(f)
                if not spikes:
                    return "No spikes recorded."
                lines = [f"{'Time':<20s} {'Model':<20s} {'Severity':<10s} {'P↑':>6s} {'C↓':>6s} {'Triggers'}"]
                lines.append("-" * 90)
                for s in spikes[-20:]:
                    ts = s.get("timestamp", "?")[:19]
                    model = s.get("model", "?")[:18]
                    sev = s.get("severity", "?")
                    pt = str(s.get("prompt_tokens", 0))
                    ct = str(s.get("completion_tokens", 0))
                    triggers = ", ".join(s.get("trigger_flags", []))
                    lines.append(f"{ts:<20s} {model:<20s} {sev:<10s} {pt:>6s} {ct:>6s} {triggers}")
                return "\n".join(lines)
            except Exception as e:
                return f"Error: {e}"
        self._run_async("Spike Log", load)

    def fn_session_stats(self):
        if not self.token_tracker:
            self._show_result("Session Stats", "Token tracker not initialized.")
            return
        stats = self.token_tracker.session_stats()
        lines = [
            "TOKEN SESSION STATS",
            "=" * 40,
            f"Total prompt tokens:      {stats['total_prompt']}",
            f"Total completion tokens:   {stats['total_completion']}",
            f"Total all tokens:          {stats['total_prompt'] + stats['total_completion']}",
            f"",
            f"Last prompt tokens:        {stats['last_prompt']}",
            f"Last completion tokens:    {stats['last_completion']}",
            f"",
            f"Avg prompt (last 20):      {stats['avg_prompt']:.0f}",
            f"Avg completion (last 20):  {stats['avg_completion']:.0f}",
            f"",
            f"Requests this session:     {stats['request_count']}",
            f"Tokens per minute:         {self.token_tracker.tokens_per_minute():.1f}",
            f"Spike count:               {stats['spike_count']}",
        ]
        self._show_result("Session Stats", "\n".join(lines))

    def fn_spike_thresholds(self):
        self.threshold_frame.setVisible(not self.threshold_frame.isVisible())

    def fn_export_token_report(self):
        if not self.token_tracker:
            self._show_result("Export", "Token tracker not initialized.")
            return

        def export():
            stats = self.token_tracker.session_stats()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report = f"""# COI Token Report — {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Session Summary
- Total prompt tokens: {stats['total_prompt']}
- Total completion tokens: {stats['total_completion']}
- Requests: {stats['request_count']}
- Spikes: {stats['spike_count']}
- Tokens/min: {self.token_tracker.tokens_per_minute():.1f}

## Averages (last 20)
- Avg prompt: {stats['avg_prompt']:.0f}
- Avg completion: {stats['avg_completion']:.0f}

## Generated
{datetime.now().isoformat()}
"""
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            path = LOGS_DIR / f"token_report_{ts}.md"
            path.write_text(report, encoding="utf-8")
            return f"Report saved to:\n{path}"
        self._run_async("Export Token Report", export)

    # ── 📋 QUICK ACTIONS ─────────────────────────────────────
    def fn_copy_last_output(self):
        if self._last_tool_output:
            QApplication.clipboard().setText(self._last_tool_output)

    def fn_clear_chat(self):
        if not self.main_window:
            return
        reply = QMessageBox.question(self, "Clear Chat",
            "Clear the chat display?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.main_window.chat.clear()
            self.main_window.history.clear()

    def fn_save_snapshot(self):
        def save():
            SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Gather data
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "chat_history": self.main_window.history if self.main_window else [],
                "token_stats": self.token_tracker.session_stats() if self.token_tracker else {},
            }

            # Loaded models
            try:
                r = requests.get(f"{OLLAMA_API}/api/ps", timeout=5)  # DEPRECATED-V5
                snapshot["loaded_models"] = [m["name"] for m in r.json().get("models", [])]  # DEPRECATED-V5
            except:
                snapshot["loaded_models"] = []

            path = SNAPSHOTS_DIR / f"snapshot_{ts}.json"
            with open(path, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)
            return f"Snapshot saved:\n{path}"
        self._run_async("Save Snapshot", save)

    def fn_load_snapshot(self):
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Snapshot", str(SNAPSHOTS_DIR),
            "JSON (*.json)"
        )
        if not path or not self.main_window:
            return
        try:
            with open(path, "r") as f:
                snapshot = json.load(f)
            self.main_window.history = snapshot.get("chat_history", [])
            self.main_window.chat.clear()
            for msg in self.main_window.history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                sender = "DAVE" if role == "user" else "COI"
                color = "#f0a800" if role == "user" else "#00c8f0"
                self.main_window.append_message(sender, content, color)
        except Exception as e:
            self._show_result("Load Snapshot", f"Error: {e}")
