"""Water dashboard UI, chart, and water-entry dialogs."""
import math
from datetime import date, datetime

from PySide6.QtCore import Qt, QDate, QDateTime
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
    QFormLayout, QSpinBox, QDialogButtonBox, QDateEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView, QDateTimeEdit,
    QComboBox, QListView, QAbstractSpinBox
)

class WaterBarChart(QWidget):
    """Fresh-blue, dependency-free daily intake chart."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.goal_ml = 2500
        self.goal_values = []
        self.setMinimumHeight(220)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())

    def set_values(self, values, goal_ml=2500, goal_values=None):
        self.values = list(values)
        self.goal_ml = max(1, int(goal_ml))
        self.goal_values = list(goal_values or [self.goal_ml] * len(self.values))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        w, h = self.width(), self.height()
        left, right, top, bottom = 48, 16, 20, 36
        chart_h = max(20, h - top - bottom)
        chart_w = max(20, w - left - right)
        # Scale to actual intake data, not the daily goal. This ensures smaller
        # daily totals remain visible and the bars use the chart's available height.
        actual_max = max([int(v) for _, v in self.values] + [0])
        max_value = max(500, int(math.ceil(max(actual_max, 1) / 500.0) * 500))
        tick_step = max(250, int(math.ceil(max_value / 4 / 250.0) * 250))

        # Soft blue plot background and horizontal guide lines.
        painter.fillRect(left, top, chart_w, chart_h, Qt.GlobalColor.white)
        for tick in range(0, max_value + 1, tick_step):
            y = top + chart_h - int(chart_h * tick / max_value)
            painter.setPen(Qt.GlobalColor.lightGray)
            painter.drawLine(left, y, w - right, y)
            painter.setPen(QColor("#38546B"))
            painter.drawText(4, y + 4, f"{tick:,}")

        # Daily target line intentionally removed for a cleaner, aligned chart.

        count = max(1, len(self.values))
        slot = chart_w / count
        bar_w = max(8, min(38, int(slot * 0.56)))
        for i, (label, value) in enumerate(self.values):
            x = int(left + i * slot + (slot - bar_w) / 2)
            bh = int(chart_h * min(value, max_value) / max_value)
            y = top + chart_h - bh
            # Rounded blue bars; slightly deeper blue for the selected/latest day.
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#318CE7"))
            painter.drawRoundedRect(x, y, bar_w, max(3, bh), 5, 5)
            # Dark, high-contrast day labels.
            painter.setPen(QColor("#38546B"))
            painter.drawText(int(left + i * slot), h - 22, int(slot), 18,
                             Qt.AlignmentFlag.AlignHCenter, label)
            if slot >= 48:
                value_y = max(top + 18, y - 23)
                value_text = f"{value:,}"
                value_rect = painter.boundingRect(
                    int(left + i * slot), value_y, int(slot), 18,
                    Qt.AlignmentFlag.AlignHCenter, value_text
                )
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#FFFFFF"))
                painter.drawRoundedRect(value_rect.adjusted(5, 0, -5, 0), 4, 4)
                painter.setPen(QColor("#17324D"))
                painter.drawText(int(left + i * slot), value_y, int(slot), 18,
                                 Qt.AlignmentFlag.AlignHCenter, value_text)
        painter.end()


class WaterEntryDialog(QDialog):
    def __init__(self, parent=None, amount=250, timestamp=None):
        super().__init__(parent)
        self.setWindowTitle("Water entry")
        layout = QFormLayout(self)
        self.amount = QSpinBox()
        self.amount.setRange(1, 5000)
        self.amount.setSuffix(" ml")
        self.amount.setValue(int(amount))
        self.timestamp = QDateTimeEdit()
        self.timestamp.setCalendarPopup(True)
        self.timestamp.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.timestamp.setDateTime(timestamp or QDateTime.currentDateTime())
        layout.addRow("Amount:", self.amount)
        layout.addRow("Date and time:", self.timestamp)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)


class WaterDashboard(QDialog):
    """Blue wellness dashboard with CRUD and 7/30-day intake comparison."""
    def __init__(self, buddy):
        super().__init__(buddy)
        self.buddy = buddy
        self.setWindowTitle("Aadya Water Buddy — Water Dashboard")
        self.resize(900, 800)
        self.setMinimumSize(760, 700)
        self.setStyleSheet("""
            QDialog { background: #F4F9FF; color: #17324D; }
            QLabel { color: #17324D; }
            QFrame#card { background: #FFFFFF; border: 1px solid #D9EAFB; border-radius: 16px; }
            QLabel#eyebrow { color: #58738E; font-size: 11px; font-weight: 600; }
            QLabel#cardValue { color: #1769AA; font-size: 25px; font-weight: 800; }
            QLabel#sectionTitle { color: #17324D; font-size: 14px; font-weight: 700; }
            QPushButton { background: #247FD1; color: white; border: 0; border-radius: 9px; padding: 8px 13px; font-weight: 650; }
            QPushButton:hover { background: #176BB7; }
            QPushButton:disabled { background: #B8CDE0; color: #F6FAFF; }
            QPushButton#secondary { background: #E5F1FC; color: #1C659F; }
            QPushButton#secondary:hover { background: #D5E9FA; }
            QPushButton#danger { background: #FDECEC; color: #A53A3A; }
            QPushButton#danger:hover { background: #FADADA; }
            QDateEdit, QComboBox { background: #FFFFFF; color: #17324D; border: 1px solid #C9DFF3; border-radius: 8px; padding: 6px 8px; min-height: 30px; }
            QComboBox { combobox-popup: 0; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 30px; border-left: 1px solid #D9EAFB; border-top-right-radius: 8px; border-bottom-right-radius: 8px; background: #EAF4FE; }
            QComboBox::down-arrow { width: 9px; height: 9px; }
            QComboBox QAbstractItemView { background: #FFFFFF; color: #17324D; selection-background-color: #D9EDFF; selection-color: #17324D; border: 1px solid #C9DFF3; outline: 0; }
            QComboBox QAbstractItemView::item { min-height: 30px; padding: 6px 10px; }
            QDateEdit::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 30px; border-left: 1px solid #D9EAFB; background: #EAF4FE; }
            QTableWidget { background: #FFFFFF; color: #17324D; alternate-background-color: #F5FAFF; border: 1px solid #D9EAFB; border-radius: 10px; gridline-color: #E6F0FA; selection-background-color: #D9EDFF; selection-color: #17324D; }
            QTableWidget::item { color: #17324D; padding: 6px 8px; }
            QTableCornerButton::section { background: #EAF4FE; border: 0; }
            QHeaderView::section { background: #EAF4FE; color: #315D80; border: 0; border-bottom: 1px solid #D6E8F8; padding: 9px; font-weight: 700; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Your Water Journey")
        title.setStyleSheet("font-size: 25px; font-weight: 800; color: #153E61;")
        subtitle = QLabel("Small sips, steady progress.")
        subtitle.setStyleSheet("font-size: 12px; color: #67829A;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        header.addWidget(QLabel("Selected day"))
        self.day = QDateEdit()
        self.day.setCalendarPopup(True)
        self.day.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.day.setStyleSheet("""
            QDateEdit { background: #FFFFFF; color: #17324D; border: 1px solid #C9DFF3;
                        border-radius: 8px; padding: 6px 8px; min-height: 30px; }
            QDateEdit::drop-down { subcontrol-origin: padding; subcontrol-position: top right;
                                   width: 30px; border-left: 1px solid #D9EAFB;
                                   background: #EAF4FE; }
        """)
        cal = self.day.calendarWidget()
        cal.setGridVisible(True)
        cal.setMinimumSize(300, 245)
        cal.setStyleSheet("""
            QCalendarWidget QWidget { background: #FFFFFF; color: #17324D; }
            QCalendarWidget QToolButton { background: #EAF4FE; color: #17324D;
                border: 0; padding: 6px; font-weight: 600; }
            QCalendarWidget QToolButton:hover { background: #D9EDFF; }
            QCalendarWidget QMenu { background: #FFFFFF; color: #17324D; }
            QCalendarWidget QSpinBox { background: #FFFFFF; color: #17324D; }
            QCalendarWidget QAbstractItemView { background: #FFFFFF; color: #17324D;
                selection-background-color: #247FD1; selection-color: #FFFFFF;
                alternate-background-color: #F4F9FF; outline: 0; }
        """)
        self.day.setDisplayFormat("dd MMM yyyy")
        self.day.setMinimumWidth(150)
        self.day.setMaximumWidth(170)
        self.day.setDate(QDate.currentDate())
        self.day.dateChanged.connect(self.refresh)
        header.addWidget(self.day)
        root.addLayout(header)

        # Summary cards
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.intake_card, self.progress_card, self.remaining_card = [], [], []
        self.summary = QLabel()
        self.progress_text = QLabel()
        self.remaining_text = QLabel()
        for icon, eyebrow, value_label, detail_label in [
            ("💧", "TODAY'S INTAKE", self.summary, None),
            ("🎯", "GOAL PROGRESS", self.progress_text, None),
            ("↗", "REMAINING", self.remaining_text, None),
        ]:
            card = QFrame()
            card.setObjectName("card")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(16, 13, 16, 13)
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 20px;")
            eyebrow_label = QLabel(eyebrow)
            eyebrow_label.setObjectName("eyebrow")
            value_label.setObjectName("cardValue")
            layout.addWidget(icon_label)
            layout.addWidget(eyebrow_label)
            layout.addWidget(value_label)
            cards.addWidget(card)
        root.addLayout(cards)

        # Progress strip
        progress_frame = QFrame()
        progress_frame.setObjectName("card")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(16, 12, 16, 14)
        progress_head = QHBoxLayout()
        progress_head.addWidget(QLabel("Daily goal progress"))
        progress_head.addStretch(1)
        self.progress_percent = QLabel("0%")
        self.progress_percent.setStyleSheet("font-weight: 800; color: #247FD1;")
        progress_head.addWidget(self.progress_percent)
        progress_layout.addLayout(progress_head)
        self.progress_bar = QFrame()
        self.progress_bar.setFixedHeight(13)
        self.progress_bar.setStyleSheet("background: #E2EFFB; border-radius: 6px;")
        self.progress_fill = QFrame(self.progress_bar)
        self.progress_fill.setGeometry(0, 0, 0, 13)
        self.progress_fill.setStyleSheet("background: #318CE7; border-radius: 6px;")
        progress_layout.addWidget(self.progress_bar)
        self.progress_note = QLabel("Your daily goal is 2,500 ml.")
        self.progress_note.setStyleSheet("color: #67829A; font-size: 11px;")
        progress_layout.addWidget(self.progress_note)
        root.addWidget(progress_frame)

        # Chart card and range selector
        chart_frame = QFrame()
        chart_frame.setObjectName("card")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(16, 12, 16, 12)
        chart_head = QHBoxLayout()
        chart_title = QLabel("Daily intake")
        chart_title.setObjectName("sectionTitle")
        chart_head.addWidget(chart_title)
        chart_head.addStretch(1)
        chart_head.addWidget(QLabel("Compare"))
        self.range_select = QComboBox()
        self.range_select.addItems(["Last 7 days", "Last 30 days"])
        self.range_select.setView(QListView())
        self.range_select.view().setStyleSheet(
            "QListView { background: #FFFFFF; color: #17324D; border: 1px solid #C9DFF3; "
            "outline: 0; } QListView::item { min-height: 30px; padding: 6px 10px; } "
            "QListView::item:selected { background: #D9EDFF; color: #17324D; }"
        )
        self.range_select.setMinimumWidth(145)
        self.range_select.setMaximumWidth(165)
        self.range_select.setMinimumHeight(34)
        self.range_select.currentIndexChanged.connect(self.refresh_chart)
        chart_head.addWidget(self.range_select)
        chart_layout.addLayout(chart_head)
        self.chart_caption = QLabel("Daily totals compared with your 2,500 ml goal")
        self.chart_caption.setStyleSheet("color: #67829A; font-size: 11px;")
        chart_layout.addWidget(self.chart_caption)
        self.chart = WaterBarChart()
        self.chart.setMinimumHeight(250)
        chart_layout.addWidget(self.chart)
        root.addWidget(chart_frame, 3)

        # Entries card
        entries_frame = QFrame()
        entries_frame.setObjectName("card")
        entries_layout = QVBoxLayout(entries_frame)
        entries_layout.setContentsMargins(16, 12, 16, 12)
        entries_head = QHBoxLayout()
        entries_title = QLabel("Water entries")
        entries_title.setObjectName("sectionTitle")
        entries_head.addWidget(entries_title)
        entries_head.addStretch(1)
        self.entries_count = QLabel("0 entries")
        self.entries_count.setStyleSheet("color: #67829A; font-size: 11px;")
        entries_head.addWidget(self.entries_count)
        entries_layout.addLayout(entries_head)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Time", "Amount", "Type"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(105)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setStyleSheet(self.table.styleSheet() + " QTableWidget::item { color: #17324D; }")
        entries_layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        add_btn = QPushButton("＋ Add water")
        edit_btn = QPushButton("Edit selected")
        edit_btn.setObjectName("secondary")
        delete_btn = QPushButton("Delete selected")
        delete_btn.setObjectName("danger")
        reset_btn = QPushButton("Reset selected day")
        reset_btn.setObjectName("secondary")
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary")
        add_btn.clicked.connect(self.add_entry)
        edit_btn.clicked.connect(self.edit_entry)
        delete_btn.clicked.connect(self.delete_entry)
        reset_btn.clicked.connect(self.reset_day)
        close_btn.clicked.connect(self.accept)
        actions.addWidget(add_btn)
        actions.addWidget(edit_btn)
        actions.addWidget(delete_btn)
        actions.addWidget(reset_btn)
        actions.addStretch(1)
        actions.addWidget(close_btn)
        entries_layout.addLayout(actions)
        root.addWidget(entries_frame, 1)

        self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        percent = getattr(self, "_progress_percent_value", 0)
        if hasattr(self, "progress_bar") and hasattr(self, "progress_fill"):
            self.progress_fill.setGeometry(
                0, 0, int(self.progress_bar.width() * percent / 100), 13
            )

    def _selected_date(self):
        return self.day.date().toString("yyyy-MM-dd")

    def _find_day_data(self, day):
        if self.buddy.data.get("date") == day:
            return self.buddy.data
        for item in self.buddy.data.get("history", []):
            if item.get("date") == day:
                return item
        return None

    def _events_for_day(self, day):
        record = self._find_day_data(day)
        if record is None:
            return []
        return record.setdefault("events", record.get("entries", []))

    def _total_for_day(self, day):
        return sum(int(e.get("ml", 0)) for e in self._events_for_day(day)
                   if e.get("action") == "drank_water" and int(e.get("ml", 0)) > 0)

    def _save_selected_record(self, day):
        record = self._find_day_data(day)
        if record is not None:
            record["water_ml"] = self._total_for_day(day)
        self.buddy._save_data()
        self.buddy.update_total_label()

    def _daily_total(self, day):
        record = self._find_day_data(day)
        if record is None:
            return 0
        return self._total_for_day(day)

    def _refresh_summary(self):
        day = self._selected_date()
        total = self._daily_total(day)
        goal = int(self.buddy.settings.get("daily_goal_ml", 2500))
        percent = int(round(total * 100 / max(1, goal)))
        remaining = max(0, goal - total)
        self.summary.setText(f"{total:,} ml")
        self.progress_text.setText(f"{percent}%")
        self.remaining_text.setText(f"{remaining:,} ml")
        self.progress_percent.setText(f"{percent}%")
        self.progress_fill.setGeometry(0, 0, int(self.progress_bar.width() * min(100, percent) / 100), 13)
        self.progress_note.setText(f"{total:,} ml logged · {goal:,} ml daily goal")
        self._progress_percent_value = min(100, percent)
        self.progress_fill.setGeometry(
            0, 0, int(self.progress_bar.width() * self._progress_percent_value / 100), 13
        )

    def refresh_chart(self, *args):
        days = 7 if self.range_select.currentIndex() == 0 else 30
        selected = date.fromisoformat(self._selected_date())
        start = selected - __import__("datetime").timedelta(days=days - 1)
        vals = []
        goals = []
        goal_history = self.buddy.settings.get("daily_goal_history", {})
        current_goal = int(self.buddy.settings.get("daily_goal_ml", 2500))
        for offset in range(days):
            day = start + __import__("datetime").timedelta(days=offset)
            day_key = day.isoformat()
            record = self._find_day_data(day_key)
            vals.append((day.strftime("%a" if days == 7 else "%d"), self._daily_total(day_key)))
            if record is not None and record.get("target_ml") is not None:
                goals.append(int(record["target_ml"]))
            else:
                goals.append(int(goal_history.get(day_key, current_goal)))
        self.chart.set_values(vals, current_goal, goals)
        self.chart_caption.setText(
            f"Daily totals · {days} days · blue line shows each day's target"
        )

    def refresh(self, *args):
        day = self._selected_date()
        self._refresh_summary()
        self.refresh_chart()
        events = self._events_for_day(day)
        water_events = [(i, e) for i, e in enumerate(events)
                        if e.get("action") == "drank_water" and int(e.get("ml", 0)) > 0]
        self.table.setRowCount(0)
        for row, (event_index, event) in enumerate(water_events):
            self.table.insertRow(row)
            try:
                stamp = datetime.fromisoformat(event.get("time", ""))
                time_text = stamp.strftime("%I:%M %p").lstrip("0")
            except Exception:
                time_text = event.get("time", "")
            time_item = QTableWidgetItem(time_text)
            time_item.setForeground(QColor("#17324D"))
            time_item.setData(Qt.ItemDataRole.UserRole, event_index)
            amount_item = QTableWidgetItem(f"{int(event.get('ml', 0)):,} ml")
            amount_item.setForeground(QColor("#17324D"))
            type_item = QTableWidgetItem("Water")
            type_item.setForeground(QColor("#247FD1"))
            self.table.setItem(row, 0, time_item)
            self.table.setItem(row, 1, amount_item)
            self.table.setItem(row, 2, type_item)
        self.entries_count.setText(f"{len(water_events)} entr{'y' if len(water_events) == 1 else 'ies'}")
        if not water_events:
            self.table.setRowCount(1)
            empty = QTableWidgetItem("No water entries for this day")
            empty.setForeground(QColor("#67829A"))
            empty.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(0, 0, empty)
            self.table.setSpan(0, 0, 1, 3)
        self.table.clearSelection()

    def _selected_event(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Select an entry", "Choose a water entry first.", parent=self)
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole)

    def add_entry(self):
        dialog = WaterEntryDialog(self, 250)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        day = dialog.timestamp.dateTime().date().toString("yyyy-MM-dd")
        stamp = dialog.timestamp.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
        record = self._find_day_data(day)
        if record is None:
            if day == self.buddy.data.get("date"):
                record = self.buddy.data
            else:
                record = {
                    "date": day, "water_ml": 0, "events": [],
                    "target_ml": int(self.buddy.settings.get("daily_goal_history", {}).get(
                        day, self.buddy.settings.get("daily_goal_ml", 2500)))
                }
                self.buddy.data.setdefault("history", []).append(record)
        record.setdefault("events", []).append({"time": stamp, "action": "drank_water", "ml": dialog.amount.value()})
        record["water_ml"] = self._total_for_day(day)
        self.buddy._save_data()
        self.day.setDate(QDate.fromString(day, "yyyy-MM-dd"))
        self.buddy.update_total_label()
        self.refresh()

    def edit_entry(self):
        index = self._selected_event()
        if index is None:
            return
        day = self._selected_date()
        events = self._events_for_day(day)
        event = events[index]
        try:
            stamp = QDateTime.fromString(event.get("time", ""), Qt.DateFormat.ISODate)
            if not stamp.isValid():
                stamp = QDateTime.currentDateTime()
        except Exception:
            stamp = QDateTime.currentDateTime()
        dialog = WaterEntryDialog(self, int(event.get("ml", 250)), stamp)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        dt = dialog.timestamp.dateTime()
        event["time"] = dt.toString("yyyy-MM-ddTHH:mm:ss")
        event["ml"] = dialog.amount.value()
        target_day = dt.date().toString("yyyy-MM-dd")
        if target_day != day:
            events.pop(index)
            old_record = self._find_day_data(day)
            if old_record is not None:
                old_record["water_ml"] = self._total_for_day(day)
            new_record = self._find_day_data(target_day)
            if new_record is None:
                new_record = {
                    "date": target_day, "water_ml": 0, "events": [],
                    "target_ml": int(self.buddy.settings.get("daily_goal_history", {}).get(
                        target_day, self.buddy.settings.get("daily_goal_ml", 2500)))
                }
                self.buddy.data.setdefault("history", []).append(new_record)
            new_record.setdefault("events", []).append(event)
            new_record["water_ml"] = self._total_for_day(target_day)
            self.day.setDate(QDate.fromString(target_day, "yyyy-MM-dd"))
        else:
            rec = self._find_day_data(day)
            if rec is not None:
                rec["water_ml"] = self._total_for_day(day)
        self.buddy._save_data()
        self.buddy.update_total_label()
        self.refresh()

    def delete_entry(self):
        index = self._selected_event()
        if index is None:
            return
        answer = QMessageBox.question(self, "Delete water entry",
                                      "Delete the selected water entry?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        day = self._selected_date()
        events = self._events_for_day(day)
        if 0 <= index < len(events):
            events.pop(index)
        record = self._find_day_data(day)
        if record is not None:
            record["water_ml"] = self._total_for_day(day)
        self.buddy._save_data()
        self.buddy.update_total_label()
        self.refresh()

    def reset_day(self):
        day = self._selected_date()
        answer = QMessageBox.question(self, "Reset selected day",
                                      f"Set water intake for {day} to zero? This removes water entries for that day.",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        record = self._find_day_data(day)
        if record is None:
            record = {
                "date": day, "water_ml": 0, "events": [],
                "target_ml": int(self.buddy.settings.get("daily_goal_history", {}).get(
                    day, self.buddy.settings.get("daily_goal_ml", 2500)))
            }
            self.buddy.data.setdefault("history", []).append(record)
        record["events"] = [e for e in record.get("events", []) if e.get("action") != "drank_water"]
        record["water_ml"] = 0
        self.buddy._save_data()
        self.buddy.update_total_label()
        self.refresh()

