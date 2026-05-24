"""
Spider Manager - Dark Theme (GitHub Dark inspired)
Professional dark stylesheet for PyQt6.
"""

DARK_QSS = """
/* ── Global ──────────────────────────────────────────── */
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: "Segoe UI", "SF Pro Text", Ubuntu, sans-serif;
    font-size: 13px;
    border: none;
    outline: none;
}

QMainWindow {
    background-color: #0d1117;
}

/* ── Menu Bar ─────────────────────────────────────────── */
QMenuBar {
    background-color: #161b22;
    color: #e6edf3;
    border-bottom: 1px solid #30363d;
    padding: 2px;
}
QMenuBar::item { padding: 4px 10px; border-radius: 4px; }
QMenuBar::item:selected { background-color: #21262d; }

QMenu {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background-color: #21262d; }
QMenu::separator { height: 1px; background: #30363d; margin: 4px 8px; }

/* ── Toolbar ──────────────────────────────────────────── */
QToolBar {
    background-color: #161b22;
    border-bottom: 1px solid #30363d;
    spacing: 6px;
    padding: 6px 12px;
}
QToolButton {
    background-color: transparent;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 5px 12px;
    color: #e6edf3;
    font-size: 12px;
}
QToolButton:hover { background-color: #21262d; }
QToolButton:pressed { background-color: #30363d; }
QToolButton#primaryButton { background-color: #1f6feb; border-color: #1f6feb; color: #ffffff; }
QToolButton#primaryButton:hover { background-color: #388bfd; }

/* ── Sidebar ──────────────────────────────────────────── */
#sidebar {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}
#sidebar QLabel#section_header {
    color: #8b949e;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 10px 16px 4px 16px;
}
#sidebar QPushButton {
    text-align: left;
    padding: 7px 16px;
    border-radius: 6px;
    margin: 1px 8px;
    color: #e6edf3;
    background: transparent;
    border: none;
    font-size: 12px;
}
#sidebar QPushButton:hover { background-color: #21262d; }
#sidebar QPushButton:checked {
    background-color: rgba(31, 111, 235, 0.18);
    color: #58a6ff;
    font-weight: 600;
}

/* ── Table ────────────────────────────────────────────── */
QTableView {
    background-color: #0d1117;
    gridline-color: rgba(48, 54, 61, 0.6);
    selection-background-color: rgba(31, 111, 235, 0.1);
    selection-color: #e6edf3;
    border: none;
    outline: none;
}
QTableView::item { padding: 9px 12px; border-bottom: 1px solid rgba(48, 54, 61, 0.4); }
QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #30363d;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Progress Bar ─────────────────────────────────────── */
QProgressBar {
    background-color: #21262d;
    border-radius: 3px;
    height: 5px;
    text-align: center;
    font-size: 0px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1f6feb, stop:1 #58a6ff);
    border-radius: 3px;
}
QProgressBar#complete::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #238636, stop:1 #3fb950);
}
QProgressBar#error::chunk {
    background-color: #f78166;
}

/* ── Tabs ─────────────────────────────────────────────── */
QTabBar::tab {
    background: transparent;
    padding: 8px 16px;
    color: #8b949e;
    border-bottom: 2px solid transparent;
    font-size: 12px;
}
QTabBar::tab:selected { color: #58a6ff; border-bottom: 2px solid #58a6ff; font-weight: 500; }
QTabBar::tab:hover { color: #e6edf3; }
QTabWidget::pane { border: none; }

/* ── Status Bar ───────────────────────────────────────── */
QStatusBar {
    background-color: #161b22;
    border-top: 1px solid #30363d;
    color: #8b949e;
    font-size: 11px;
}


/* ── Dialog ───────────────────────────────────────────── */
QDialog {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
}

/* ── Tooltip ──────────────────────────────────────────── */
QToolTip {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}

/* ── Splitter ─────────────────────────────────────────── */
QSplitter::handle { background: #30363d; }
QSplitter::handle:horizontal { width: 1px; }

/* ── SpeedGraph frame ─────────────────────────────────── */
#speed_graph_frame {
    background-color: #161b22;
    border-top: 1px solid #30363d;
}
"""
