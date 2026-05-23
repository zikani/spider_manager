"""Light stylesheet for Spider Manager (simple high-contrast light UI)."""

LIGHT_QSS = """
QWidget {
    background-color:
    color:
    font-family: "Segoe UI", "SF Pro Text", Ubuntu, sans-serif;
    font-size: 13px;
    border: none;
    outline: none;
}
QMainWindow { background-color:

/* ── Menu Bar ─────────────────────────────────────────── */
QMenuBar {
    background-color:
    color:
    border-bottom: 1px solid
    padding: 2px;
}
QMenuBar::item { padding: 4px 10px; border-radius: 4px; }
QMenuBar::item:selected { background-color:

QMenu {
    background-color:
    border: 1px solid
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 24px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background-color:
QMenu::separator { height: 1px; background:

/* ── Toolbar ──────────────────────────────────────────── */
QToolBar {
    background-color:
    border-bottom: 1px solid
    spacing: 6px;
    padding: 6px 12px;
}
QToolButton {
    background-color: transparent;
    border: 1px solid
    border-radius: 6px;
    padding: 5px 12px;
    color:
    font-size: 12px;
}
QToolButton:hover { background-color:
QToolButton:pressed { background-color:
QToolButton
QToolButton

/* ── Sidebar ──────────────────────────────────────────── */
    background-color:
    border-right: 1px solid
}
    color:
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    padding: 10px 16px 4px 16px;
}
    text-align: left;
    padding: 7px 16px;
    border-radius: 6px;
    margin: 1px 8px;
    color:
    background: transparent;
    border: none;
    font-size: 12px;
}
    background-color: rgba(9, 105, 218, 0.1);
    color:
    font-weight: 600;
}

/* ── Table ────────────────────────────────────────────── */
QTableView {
    background-color:
    gridline-color: rgba(208, 215, 222, 0.8);
    selection-background-color: rgba(9, 105, 218, 0.1);
    selection-color:
    border: none;
    outline: none;
}
QTableView::item { padding: 9px 12px; border-bottom: 1px solid rgba(208, 215, 222, 0.5); }
QHeaderView::section {
    background-color:
    color:
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Progress Bar ─────────────────────────────────────── */
QProgressBar {
    background-color:
    border-radius: 3px;
    height: 5px;
    text-align: center;
    font-size: 0px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0
    border-radius: 3px;
}
QProgressBar
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0
}
QProgressBar
    background-color:
}

/* ── Tabs ─────────────────────────────────────────────── */
QTabBar::tab {
    background: transparent;
    padding: 8px 16px;
    color:
    border-bottom: 2px solid transparent;
    font-size: 12px;
}
QTabBar::tab:selected { color:
QTabBar::tab:hover { color:
QTabWidget::pane { border: none; }

/* ── Status Bar ───────────────────────────────────────── */
QStatusBar {
    background-color:
    border-top: 1px solid
    color:
    font-size: 11px;
}

"""
