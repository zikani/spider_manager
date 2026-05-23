"""Report issue dialog - bug reporting and issue tracking."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.constants import APP_NAME, APP_VERSION


class ReportIssueDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Issue")
        self.resize(600, 700)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel("Report an Issue")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        type_group = QGroupBox("Issue Type")
        type_layout = QFormLayout(type_group)
        
        self.issue_type = QComboBox()
        self.issue_type.addItems([
            "Bug Report",
            "Feature Request", 
            "Performance Issue",
            "UI/UX Issue",
            "Crash Report",
            "Other"
        ])
        type_layout.addRow("Type:", self.issue_type)
        
        self.severity = QComboBox()
        self.severity.addItems(["Low", "Medium", "High", "Critical"])
        type_layout.addRow("Severity:", self.severity)
        
        layout.addWidget(type_group)
        
        details_group = QGroupBox("Issue Details")
        details_layout = QFormLayout(details_group)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Brief summary of the issue")
        details_layout.addRow("Title:", self.title_input)
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText(
            "Detailed description of the issue...\n\n"
            "Please include:\n"
            "• What you were trying to do\n"
            "• What happened instead\n"
            "• Any error messages\n"
            "• Steps to reproduce the issue"
        )
        self.description_input.setMaximumHeight(150)
        details_layout.addRow("Description:", self.description_input)
        
        self.steps_input = QTextEdit()
        self.steps_input.setPlaceholderText(
            "1. Step one\n"
            "2. Step two\n"
            "3. Step three\n"
            "4. Issue occurs"
        )
        self.steps_input.setMaximumHeight(100)
        details_layout.addRow("Steps to Reproduce:", self.steps_input)
        
        self.expected_input = QTextEdit()
        self.expected_input.setPlaceholderText("What you expected to happen...")
        self.expected_input.setMaximumHeight(80)
        details_layout.addRow("Expected Behavior:", self.expected_input)
        
        layout.addWidget(details_group)
        
        env_group = QGroupBox("Environment Information")
        env_layout = QVBoxLayout(env_group)
        
        env_info = QLabel(f"""
        <b>Application:</b> {APP_NAME} v{APP_VERSION}<br>
        <b>Operating System:</b> {self._get_os_info()}<br>
        <b>Python Version:</b> {self._get_python_version()}<br>
        <b>Architecture:</b> {self._get_architecture()}
        """)
        env_info.setTextFormat(Qt.TextFormat.RichText)
        env_layout.addWidget(env_info)
        
        self.include_logs = QCheckBox("Include application logs")
        self.include_logs.setChecked(True)
        env_layout.addWidget(self.include_logs)
        
        self.include_config = QCheckBox("Include configuration settings")
        self.include_config.setChecked(False)
        env_layout.addWidget(self.include_config)
        
        layout.addWidget(env_group)
        
        contact_group = QGroupBox("Contact Information (Optional)")
        contact_layout = QFormLayout(contact_group)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@example.com")
        contact_layout.addRow("Email:", self.email_input)
        
        self.allow_contact = QCheckBox("Allow developers to contact me for follow-up")
        contact_layout.addRow("", self.allow_contact)
        
        layout.addWidget(contact_group)
        
        button_layout = QHBoxLayout()
        
        preview_btn = QPushButton("Preview Report")
        preview_btn.clicked.connect(self._preview_report)
        
        submit_btn = QPushButton("Submit Issue")
        submit_btn.clicked.connect(self._submit_issue)
        submit_btn.setObjectName("primary")
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(preview_btn)
        button_layout.addWidget(submit_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _get_os_info(self):
        """Get operating system information."""
        import platform
        return f"{platform.system()} {platform.release()}"

    def _get_python_version(self):
        """Get Python version."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _get_architecture(self):
        """Get system architecture."""
        import platform
        return platform.machine()

    def _preview_report(self):
        """Show preview of the issue report."""
        report = self._generate_report()
        
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Issue Report Preview")
        preview_dialog.resize(700, 600)
        
        layout = QVBoxLayout(preview_dialog)
        
        preview_text = QTextEdit()
        preview_text.setPlainText(report)
        preview_text.setReadOnly(True)
        layout.addWidget(preview_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(preview_dialog.accept)
        layout.addWidget(close_btn)
        
        preview_dialog.exec()

    def _generate_report(self):
        """Generate the complete issue report."""
        report = f"""
ISSUE REPORT
============

Title: {self.title_input.text() or 'No title provided'}
Type: {self.issue_type.currentText()}
Severity: {self.severity.currentText()}
Date: {self._get_current_date()}

DESCRIPTION
-----------
{self.description_input.toPlainText() or 'No description provided'}

STEPS TO REPRODUCE
------------------
{self.steps_input.toPlainText() or 'No steps provided'}

EXPECTED BEHAVIOR
-----------------
{self.expected_input.toPlainText() or 'No expected behavior provided'}

ENVIRONMENT INFORMATION
----------------------
Application: {APP_NAME} v{APP_VERSION}
Operating System: {self._get_os_info()}
Python Version: {self._get_python_version()}
Architecture: {self._get_architecture()}

ADDITIONAL INFORMATION
---------------------
Include Logs: {self.include_logs.isChecked()}
Include Config: {self.include_config.isChecked()}

CONTACT INFORMATION
-------------------
Email: {self.email_input.text() or 'Not provided'}
Allow Contact: {self.allow_contact.isChecked()}
"""
        return report

    def _get_current_date(self):
        """Get current date and time."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _submit_issue(self):
        """Submit the issue report."""
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Missing Information", 
                              "Please provide a title for the issue.")
            return
        
        if not self.description_input.toPlainText().strip():
            QMessageBox.warning(self, "Missing Information", 
                              "Please provide a description of the issue.")
            return
        
        report = self._generate_report()
        
        reply = QMessageBox.question(
            self, "Submit Issue",
            "Are you ready to submit this issue report?\n\n"
            "The report will be sent to the development team for review.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(
                self, "Issue Submitted",
                "Thank you for reporting this issue!\n\n"
                "Your report has been received and will be reviewed by the development team.\n"
                "You can track the issue on GitHub."
            )
            
            QDesktopServices.openUrl(QUrl("https://github.com/spidermanager/spidermanager/issues"))
            
            self.accept()

    def _copy_to_clipboard(self):
        """Copy report to clipboard."""
        report = self._generate_report()
        
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(report)
        
        QMessageBox.information(self, "Copied", "Issue report copied to clipboard.")
