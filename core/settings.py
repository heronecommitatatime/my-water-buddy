"""Settings dialog for reminder interval, serving size, and daily target."""
from PySide6.QtWidgets import QDialog, QFormLayout, QSpinBox, QDialogButtonBox, QComboBox

class SettingsDialog(QDialog):
    def __init__(self, parent, reminder_minutes, serving_ml, daily_goal_ml=2500):
        super().__init__(parent)
        self.setWindowTitle("Aadya Water Buddy Settings")
        layout = QFormLayout(self)
        self.reminder = QSpinBox()
        self.reminder.setRange(5, 180)
        self.reminder.setSuffix(" minutes")
        self.reminder.setValue(reminder_minutes)
        self.serving = QSpinBox()
        self.serving.setRange(50, 1000)
        self.serving.setSingleStep(50)
        self.serving.setSuffix(" ml")
        self.serving.setValue(serving_ml)
        self.daily_goal = QComboBox()
        self.daily_goal.addItems([f"{ml:,} ml" for ml in (2000, 2500, 3000, 3500, 4000, 4500, 5000)])
        self.daily_goal.setCurrentIndex([2000, 2500, 3000, 3500, 4000, 4500, 5000].index(
            daily_goal_ml if daily_goal_ml in (2000, 2500, 3000, 3500, 4000, 4500, 5000) else 2500
        ))
        layout.addRow("Normal reminder interval:", self.reminder)
        layout.addRow("Water per Yes:", self.serving)
        layout.addRow("Today's water target:", self.daily_goal)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

