"""Send feedback dialog - user feedback and suggestions."""

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
    QRadioButton,
    QButtonGroup,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from config.constants import APP_NAME, APP_VERSION


class SendFeedbackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Send Feedback")
        self.resize(600, 650)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        header = QLabel("Send Feedback")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        type_group = QGroupBox("Feedback Type")
        type_layout = QVBoxLayout(type_group)
        
        self.feedback_type_group = QButtonGroup()
        
        self.general_radio = QRadioButton("General Feedback")
        self.general_radio.setChecked(True)
        self.feedback_type_group.addButton(self.general_radio, 0)
        
        self.feature_radio = QRadioButton("Feature Request")
        self.feedback_type_group.addButton(self.feature_radio, 1)
        
        self.improvement_radio = QRadioButton("Improvement Suggestion")
        self.feedback_type_group.addButton(self.improvement_radio, 2)
        
        self.compliment_radio = QRadioButton("Compliment/Encouragement")
        self.feedback_type_group.addButton(self.compliment_radio, 3)
        
        type_layout.addWidget(self.general_radio)
        type_layout.addWidget(self.feature_radio)
        type_layout.addWidget(self.improvement_radio)
        type_layout.addWidget(self.compliment_radio)
        
        layout.addWidget(type_group)
        
        details_group = QGroupBox("Feedback Details")
        details_layout = QFormLayout(details_group)
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Brief subject of your feedback")
        details_layout.addRow("Subject:", self.subject_input)
        
        self.feedback_input = QTextEdit()
        self.feedback_input.setPlaceholderText(
            "Please share your thoughts, suggestions, or feedback...\n\n"
            "We appreciate all feedback as it helps us improve {APP_NAME}!\n\n"
            "Consider including:\n"
            "• What you like about the application\n"
            "• What could be improved\n"
            "• Features you'd like to see\n"
            "• Any issues you've encountered\n"
            "• General comments or suggestions"
        )
        self.feedback_input.setMaximumHeight(200)
        details_layout.addRow("Feedback:", self.feedback_input)
        
        rating_layout = QHBoxLayout()
        rating_layout.addWidget(QLabel("Overall Rating:"))
        
        self.rating_group = QButtonGroup()
        self.rating_buttons = []
        
        for i in range(1, 6):
            btn = QRadioButton(str(i))
            self.rating_group.addButton(btn, i)
            self.rating_buttons.append(btn)
            rating_layout.addWidget(btn)
        
        rating_layout.addStretch()
        details_layout.addRow("", rating_layout)
        
        layout.addWidget(details_group)
        
        usage_group = QGroupBox("Usage Information (Optional)")
        usage_layout = QVBoxLayout(usage_group)
        
        self.how_long = QComboBox()
        self.how_long.addItems([
            "Just started using it",
            "Less than a week",
            "A few weeks",
            "A few months", 
            "More than a year"
        ])
        usage_layout.addWidget(QLabel("How long have you been using Spider Manager?"))
        usage_layout.addWidget(self.how_long)
        
        self.frequency = QComboBox()
        self.frequency.addItems([
            "Daily",
            "Several times a week",
            "Once a week",
            "Occasionally",
            "Rarely"
        ])
        usage_layout.addWidget(QLabel("How often do you use Spider Manager?"))
        usage_layout.addWidget(self.frequency)
        
        self.features = QTextEdit()
        self.features.setPlaceholderText(
            "What features do you use most?\n"
            "(e.g., video downloads, batch operations, scheduling, etc.)"
        )
        self.features.setMaximumHeight(80)
        usage_layout.addWidget(QLabel("Most used features:"))
        usage_layout.addWidget(self.features)
        
        layout.addWidget(usage_group)
        
        contact_group = QGroupBox("Contact Information (Optional)")
        contact_layout = QFormLayout(contact_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Your name")
        contact_layout.addRow("Name:", self.name_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@example.com")
        contact_layout.addRow("Email:", self.email_input)
        
        self.allow_followup = QCheckBox("Allow follow-up contact about this feedback")
        self.allow_followup.setChecked(True)
        contact_layout.addRow("", self.allow_followup)
        
        layout.addWidget(contact_group)
        
        options_group = QGroupBox("Additional Options")
        options_layout = QVBoxLayout(options_group)
        
        self.anonymous = QCheckBox("Submit feedback anonymously")
        self.anonymous.setChecked(False)
        options_layout.addWidget(self.anonymous)
        
        self.include_system = QCheckBox("Include system information")
        self.include_system.setChecked(True)
        options_layout.addWidget(self.include_system)
        
        layout.addWidget(options_group)
        
        button_layout = QHBoxLayout()
        
        preview_btn = QPushButton("Preview Feedback")
        preview_btn.clicked.connect(self._preview_feedback)
        
        submit_btn = QPushButton("Send Feedback")
        submit_btn.clicked.connect(self._send_feedback)
        submit_btn.setObjectName("primary")
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(preview_btn)
        button_layout.addWidget(submit_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)

    def _get_feedback_type(self):
        """Get selected feedback type."""
        type_map = {
            0: "General Feedback",
            1: "Feature Request", 
            2: "Improvement Suggestion",
            3: "Compliment/Encouragement"
        }
        return type_map[self.feedback_type_group.checkedId()]

    def _get_rating(self):
        """Get selected rating."""
        rating_id = self.rating_group.checkedId()
        return rating_id if rating_id > 0 else None

    def _preview_feedback(self):
        """Show preview of the feedback."""
        feedback = self._generate_feedback()
        
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Feedback Preview")
        preview_dialog.resize(700, 600)
        
        layout = QVBoxLayout(preview_dialog)
        
        preview_text = QTextEdit()
        preview_text.setPlainText(feedback)
        preview_text.setReadOnly(True)
        layout.addWidget(preview_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(preview_dialog.accept)
        layout.addWidget(close_btn)
        
        preview_dialog.exec()

    def _generate_feedback(self):
        """Generate the complete feedback message."""
        rating = self._get_rating()
        rating_text = f"{rating}/5 stars" if rating else "Not rated"
        
        feedback = f"""
USER FEEDBACK
============

Subject: {self.subject_input.text() or 'No subject provided'}
Type: {self._get_feedback_type()}
Rating: {rating_text}
Date: {self._get_current_date()}

FEEDBACK
--------
{self.feedback_input.toPlainText() or 'No feedback provided'}

USAGE INFORMATION
----------------
How long using: {self.how_long.currentText()}
Usage frequency: {self.frequency.currentText()}
Most used features: {self.features.toPlainText() or 'Not specified'}

SYSTEM INFORMATION
------------------
Application: {APP_NAME} v{APP_VERSION}
Operating System: {self._get_os_info()}
Python Version: {self._get_python_version()}

CONTACT INFORMATION
------------------
Name: {self.name_input.text() or 'Not provided'}
Email: {self.email_input.text() or 'Not provided'}
Allow Follow-up: {self.allow_followup.isChecked()}
Anonymous: {self.anonymous.isChecked()}

ADDITIONAL OPTIONS
------------------
Include System Info: {self.include_system.isChecked()}
"""
        return feedback

    def _get_current_date(self):
        """Get current date and time."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_os_info(self):
        """Get operating system information."""
        import platform
        return f"{platform.system()} {platform.release()}"

    def _get_python_version(self):
        """Get Python version."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _send_feedback(self):
        """Send the feedback."""
        if not self.feedback_input.toPlainText().strip():
            QMessageBox.warning(self, "Missing Information", 
                              "Please provide your feedback before sending.")
            return
        
        feedback = self._generate_feedback()
        
        reply = QMessageBox.question(
            self, "Send Feedback",
            "Are you ready to send this feedback?\n\n"
            "Your feedback helps us improve Spider Manager for everyone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(
                self, "Feedback Sent",
                "Thank you for your feedback!\n\n"
                "We appreciate you taking the time to share your thoughts with us.\n"
                "Your feedback will be reviewed by our development team."
            )
            
            if not self.anonymous.isChecked():
                QDesktopServices.openUrl(QUrl("https://spidermanager.com/feedback"))
            
            self.accept()

    def _copy_to_clipboard(self):
        """Copy feedback to clipboard."""
        feedback = self._generate_feedback()
        
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(feedback)
        
        QMessageBox.information(self, "Copied", "Feedback copied to clipboard.")
