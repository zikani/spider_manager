"""Light stylesheet for Spider Manager (simple high-contrast light UI)."""

LIGHT_QSS = """
QWidget {
    background-color: #ffffff;
    color: #1f2328;
    font-family: "Segoe UI", "SF Pro Text", Ubuntu, sans-serif;
    font-size: 13px;
    border: none;
    outline: none;
}
QMainWindow { background-color: #ffffff; }

/* ── Menu Bar ─────────────────────────────────────────── */
QMenuBar {
    background-color: #f6f8fa;
    color: #1f2328;
    border-bottom: 1px solid #d0d7de;
    padding: 2px;
}
QMenuBar::item { padding: 4px 10px; border-radius: 4px; }
QMenuBar::item:selected { background-color: #eaeef2; }

QMenu {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background-color: #eef2ff; }
QMenu::separator { height: 1px; background: #d0d7de; margin: 4px 8px; }

/* ── Toolbar ──────────────────────────────────────────── */
QToolBar {
    background-color: #f6f8fa;
    border-bottom: 1px solid #d0d7de;
    spacing: 6px;
    padding: 6px 12px;
}
QToolButton {
    background-color: transparent;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 5px 12px;
    color: #1f2328;
    font-size: 12px;
}
QToolButton:hover { background-color: #eaeef2; }
QToolButton:pressed { background-color: #d0d7de; }
QToolButton#primaryButton { background-color: #0969da; border-color: #0969da; color: #ffffff; }
QToolButton#primaryButton:hover { background-color: #0550ae; }

/* ── Sidebar ──────────────────────────────────────────── */
#sidebar {
    background-color: #f6f8fa;
    border-right: 1px solid #d0d7de;
}
#sidebar QLabel#section_header {
    color: #59636e;
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
    color: #1f2328;
    background: transparent;
    border: none;
    font-size: 12px;
}
#sidebar QPushButton:hover { background-color: #eaeef2; }
#sidebar QPushButton:checked {
    background-color: rgba(9, 105, 218, 0.1);
    color: #0969da;
    font-weight: 600;
}

/* ── Table ────────────────────────────────────────────── */
QTableView {
    background-color: #ffffff;
    gridline-color: rgba(208, 215, 222, 0.8);
    selection-background-color: rgba(9, 105, 218, 0.1);
    selection-color: #1f2328;
    border: none;
    outline: none;
}
QTableView::item { padding: 9px 12px; border-bottom: 1px solid rgba(208, 215, 222, 0.5); }
QHeaderView::section {
    background-color: #f6f8fa;
    color: #59636e;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #d0d7de;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Progress Bar ─────────────────────────────────────── */
QProgressBar {
    background-color: #eaeef2;
    border-radius: 3px;
    height: 5px;
    text-align: center;
    font-size: 0px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0969da, stop:1 #54aeff);
    border-radius: 3px;
}
QProgressBar#complete::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1a7f37, stop:1 #2da44e);
}
QProgressBar#error::chunk {
    background-color: #cf222e;
}

/* ── Tabs ─────────────────────────────────────────────── */
QTabBar::tab {
    background: transparent;
    padding: 8px 16px;
    color: #59636e;
    border-bottom: 2px solid transparent;
    font-size: 12px;
}
QTabBar::tab:selected { color: #0969da; border-bottom: 2px solid #0969da; font-weight: 500; }
QTabBar::tab:hover { color: #1f2328; }
QTabWidget::pane { border: none; }

/* ── Status Bar ───────────────────────────────────────── */
QStatusBar {
    background-color: #f6f8fa;
    border-top: 1px solid #d0d7de;
    color: #59636e;
    font-size: 11px;
}

"""
