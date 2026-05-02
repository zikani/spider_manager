"""About dialog."""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel

from config.constants import APP_NAME, APP_VERSION, APP_DESCRIPTION


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{APP_NAME}</b> {APP_VERSION}"))
        layout.addWidget(QLabel(APP_DESCRIPTION))
        layout.addWidget(QLabel("Built with PyQt6 and asyncio."))
