"""Aadya desktop companion, animations, reminders, tray actions, and app orchestration."""
from __future__ import annotations

import json
import sys
import math
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QPoint, QRect, QSize, QDate, QDateTime
from PySide6.QtGui import QAction, QPixmap, QPainter, QTransform, QIcon, QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QSystemTrayIcon, QMenu, QMessageBox, QDialog
)

from config import (
    APP_NAME, APP_DIR, DATA_FILE, SETTINGS_FILE, ASSET_DIR, HAPPY_PATH, SAD_PATH,
    DANCE_FRAMES_DIR, HAPPY_WALK_DIR, SAD_WALK_DIR, WALK_FRAMES_DIR
)
from core.settings import SettingsDialog
from water.dashboard import WaterDashboard
from chatbot.chat_window import WaterChatbotDialog


def now_stamp():
    return datetime.now().isoformat(timespec="seconds")


class AadyaBuddy(QWidget):
    NORMAL_MINUTES = 30
    LATER_MINUTES = 5
    SERVING_ML = 250

    def __init__(self):
        super().__init__()
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.settings = self._load_settings()
        self.normal_minutes = int(self.settings.get("normal_reminder_minutes", self.NORMAL_MINUTES))
        self.serving_ml = int(self.settings.get("serving_ml", self.SERVING_ML))
        self.data = self._load_data()

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
            Qt.Tool | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.resize(300, 350)

        self._drag_offset = None
        self._walking = False
        self._walk_target_x = 0
        self._walk_target_y = 0
        self._walk_direction = 1
        self._walk_phase = 0
        self._pose_angle = 0
        self._prompt_active = False
        self._response_recorded = False
        self._hidden_by_user = False
        self._current_mode = "idle"
        self._last_prompt_kind = "normal"

        self.happy_source = QPixmap(str(HAPPY_PATH))
        self.sad_source = QPixmap(str(SAD_PATH))
        # Load frame folders in filename order. Expected names: frame_01.png, frame_02.png, ...
        self.animations = {
            "dance_happy": self._load_frames(DANCE_FRAMES_DIR),
            "happy_walk": self._load_frames(HAPPY_WALK_DIR),
            "sad_walk": self._load_frames(SAD_WALK_DIR),
            "walk_right": self._load_frames(WALK_FRAMES_DIR),
        }
        # Backward compatibility for older asset folders.
        if not self.animations["happy_walk"]:
            self.animations["happy_walk"] = self.animations["walk_right"]
        if not self.animations["sad_walk"]:
            self.animations["sad_walk"] = self.animations["walk_right"]
        if not self.animations["dance_happy"]:
            self.animations["dance_happy"] = self.animations["happy_walk"]
        self.active_animation = "happy_walk"
        self.walk_frames = self.animations["happy_walk"]
        self.character = QLabel(self)
        self.character.setAlignment(Qt.AlignCenter)
        self.character.setStyleSheet("background: transparent;")
        self.character.setGeometry(35, 110, 230, 215)

        self.water_total = QLabel(self)
        self.water_total.setAlignment(Qt.AlignCenter)
        self.water_total.setStyleSheet("""
            QLabel { background: rgba(255,255,255,245); color: #68433a;
            border: 1px solid #f2b7a0; border-radius: 12px;
            padding: 5px 9px; font-size: 12px; font-weight: 700; }
        """)
        self.water_total.setGeometry(35, 320, 230, 27)

        self.bubble = QFrame(self)
        self.bubble.setObjectName("bubble")
        self.bubble.setStyleSheet("""
            QFrame#bubble { background: rgba(255,255,255,250);
                border: 2px solid #f2b7a0; border-radius: 17px; }
            QLabel { color: #55382f; background: transparent; }
            QPushButton { background: #ff8b69; color: white; border: 0;
                border-radius: 11px; padding: 7px 11px; font-size: 13px; font-weight: 700; }
            QPushButton:hover { background: #f26f4b; }
            QPushButton:disabled { background: #d9d1d0; color: #746a68; }
            QPushButton#later { background: #eee5e5; color: #684b50; }
            QPushButton#close { background: transparent; color: #684b50;
                font-size: 23px; font-weight: 700; padding: 0; }
            QPushButton#close:hover { background: #f6e5e2; }
        """)
        self.bubble.setGeometry(5, 5, 290, 100)
        bl = QVBoxLayout(self.bubble)
        # Keep the question and close button on the same row to remove the
        # excessive empty space above the prompt.
        bl.setContentsMargins(10, 7, 10, 8)
        bl.setSpacing(6)
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        self.message = QLabel("Mommy, drink water? 💧")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setWordWrap(True)
        self.message.setFont(QFont("Arial", 13, QFont.Bold))
        title_row.addWidget(self.message, 1)
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("close")
        self.close_button.setFixedSize(27, 27)
        self.close_button.setFocusPolicy(Qt.NoFocus)
        self.close_button.clicked.connect(self.hide_by_user)
        title_row.addWidget(self.close_button, 0, Qt.AlignTop)
        bl.addLayout(title_row)
        buttons = QHBoxLayout()
        self.yes_button = QPushButton("Yes, drank it!")
        self.later_button = QPushButton("Later")
        self.later_button.setObjectName("later")
        self.yes_button.setFocusPolicy(Qt.NoFocus)
        self.later_button.setFocusPolicy(Qt.NoFocus)
        self.yes_button.clicked.connect(self.answer_yes)
        self.later_button.clicked.connect(self.answer_later)
        buttons.addWidget(self.yes_button)
        buttons.addWidget(self.later_button)
        bl.addLayout(buttons)

        self.update_total_label()
        self._set_expression(True)
        self._position_children()

        # Keep desktop travel timing unchanged, but advance poses much more slowly.
        # Movement ticks every 80 ms; animation frames change every 220 ms (~4.5 FPS).
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._animation_tick)
        self.animation_timer.start(80)
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._frame_tick)
        self.frame_timer.start(220)

        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self._idle_tick)
        self.idle_timer.start(280)

        self.reminder_timer = QTimer(self)
        self.reminder_timer.setSingleShot(True)
        self.reminder_timer.timeout.connect(self._on_reminder_due)
        self.reminder_timer.start(self.normal_minutes * 60_000)

        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip(APP_NAME)
        self.tray.setIcon(self._make_tray_icon())
        menu = QMenu()
        self.show_action = QAction("Show Aadya", self)
        self.show_action.triggered.connect(self.open_chatbot)
        menu.addAction(self.show_action)
        log_action = QAction("View Today's Log", self)
        log_action.triggered.connect(self.show_log)
        menu.addAction(log_action)
        dashboard_action = QAction("Water Dashboard…", self)
        dashboard_action.triggered.connect(self.open_dashboard)
        menu.addAction(dashboard_action)
        settings_action = QAction("Settings…", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)
        menu.addSeparator()
        quit_action = QAction("Quit Aadya Water Buddy", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

        # Startup sequence: dance from the left edge, then ask the water question.
        self._begin_prompt("welcome")

    def _load_frames(self, folder):
        if not folder.exists():
            return []
        frames = [QPixmap(str(p)) for p in sorted(folder.glob("*.png"))]
        return [frame for frame in frames if not frame.isNull()]

    def _use_animation(self, name):
        frames = self.animations.get(name, [])
        if frames:
            self.active_animation = name
            self.walk_frames = frames
            self._walk_phase = 0
            self._render_walk_pose()

    def _position_children(self):
        self.character.setGeometry(35, 110, 230, 215)
        self.water_total.setGeometry(35, 320, 230, 27)
        self.bubble.setGeometry(5, 5, 290, 105)

    def _make_tray_icon(self):
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(Qt.GlobalColor.transparent)
        painter.drawEllipse(3, 3, 58, 58)
        painter.setPen(Qt.GlobalColor.darkBlue)
        painter.setFont(QFont("Arial", 27, QFont.Bold))
        painter.drawText(pix.rect(), Qt.AlignCenter, "💧")
        painter.end()
        return QIcon(pix)

    def _load_settings(self):
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            return {}

    def _save_settings(self):
        self.settings["normal_reminder_minutes"] = self.normal_minutes
        self.settings["serving_ml"] = self.serving_ml
        self.settings.setdefault("daily_goal_ml", 2500)
        self.settings.setdefault("daily_goal_history", {})
        SETTINGS_FILE.write_text(json.dumps({
            "normal_reminder_minutes": self.normal_minutes,
            "serving_ml": self.serving_ml,
            "daily_goal_ml": self.settings["daily_goal_ml"],
            "daily_goal_history": self.settings.get("daily_goal_history", {})
        }, indent=2))

    def _load_data(self):
        try:
            data = json.loads(DATA_FILE.read_text())
        except Exception:
            data = {}
        today = date.today().isoformat()
        if data.get("date") != today:
            # Preserve prior day's file content in history before starting a new day.
            history = data.get("history", [])
            if data.get("date"):
                history.append({
                    "date": data.get("date"),
                    "water_ml": int(data.get("water_ml", 0)),
                    "events": data.get("events", []),
                    "target_ml": int(data.get("target_ml", self.settings.get("daily_goal_ml", 2500)))
                })
            data = {
                "date": today, "water_ml": 0, "events": [], "history": history,
                "target_ml": int(self.settings.get("daily_goal_ml", 2500))
            }
        data.setdefault("water_ml", 0)
        data.setdefault("events", [])
        data.setdefault("history", [])
        # Daily target belongs with each day's water record, so historical
        # charts can show different targets for different dates.
        current_goal = int(self.settings.get("daily_goal_ml", 2500))
        data.setdefault("target_ml", current_goal)
        for day_record in data["history"]:
            day_key = day_record.get("date")
            if "target_ml" not in day_record:
                day_record["target_ml"] = int(
                    self.settings.get("daily_goal_history", {}).get(day_key, current_goal)
                )
        return data

    def _save_data(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(self.data, indent=2))

    def update_total_label(self):
        self.water_total.setText(f"💧 Total water today: {self.data.get('water_ml', 0)} ml")

    def _set_expression(self, happy=True):
        source = self.happy_source if happy else self.sad_source
        if source.isNull():
            self.character.setText("💧")
            return
        scaled = source.scaled(220, 215, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.character.setPixmap(scaled)

    def _render_walk_pose(self):
        """Render the current PNG pose; frame advancement is handled by frame_timer."""
        if self.walk_frames:
            frame = self.walk_frames[self._walk_phase % len(self.walk_frames)]
            scaled = frame.scaled(220, 215, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.character.setPixmap(scaled)
            self.character.move(35, 110)
            return
        source = self.happy_source
        if source.isNull():
            return
        angle = (5 if self._walk_phase % 2 else -5)
        rotated = source.transformed(QTransform().rotate(angle), Qt.SmoothTransformation)
        self.character.setPixmap(rotated.scaled(220, 215, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.character.move(35, 110 + (3 if self._walk_phase % 2 else 0))

    def _available_geometry(self):
        screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1200, 800)

    def _random_walk_target(self):
        geo = self._available_geometry()
        # Keep the character inside available desktop space; availableGeometry excludes the Dock/menu bar.
        min_x = geo.left() + 12
        max_x = max(min_x, geo.right() - self.width() - 12)
        min_y = geo.top() + 30
        max_y = max(min_y, geo.bottom() - self.height() - 8)
        return min_x, max_x, min_y, max_y

    def _walk_to(self, target_x, target_y=None, on_complete=None):
        geo = self._available_geometry()
        self._walk_target_x = max(geo.left() + 8, min(target_x, geo.right() - self.width() - 8))
        self._walk_target_y = self.y() if target_y is None else max(geo.top() + 8, min(target_y, geo.bottom() - self.height() - 8))
        self._walk_complete = on_complete
        self._walking = True
        self._current_mode = "walking"

    def _frame_tick(self):
        """Advance character poses slowly without changing travel speed or arrival time."""
        if not self._walking or not self.isVisible():
            return
        self._walk_phase += 1
        self._render_walk_pose()

    def _animation_tick(self):
        if not self._walking or not self.isVisible():
            return
        x, y = self.x(), self.y()
        dx = self._walk_target_x - x
        dy = self._walk_target_y - y
        step = 2  # slower desktop travel; the animation frames still play at ~12 FPS
        if abs(dx) <= step and abs(dy) <= step:
            self.move(self._walk_target_x, self._walk_target_y)
            self._walking = False
            self._current_mode = "idle"
            if hasattr(self, "_walk_complete") and self._walk_complete:
                callback = self._walk_complete
                self._walk_complete = None
                callback()
            return
        nx = x + (step if dx > 0 else -step if dx < 0 else 0)
        ny = y + (step if dy > 0 else -step if dy < 0 else 0)
        self.move(nx, ny)

    def _idle_tick(self):
        if self._walking or not self.isVisible() or self._prompt_active:
            return
        # A subtle idle sway when waiting.
        self._walk_phase += 1
        offset = int(2 * math.sin(self._walk_phase / 3))
        self.character.move(35, 110 + offset)

    def _begin_prompt(self, kind="normal"):
        if self._prompt_active:
            self._queued_prompt = kind
            return
        self._prompt_active = True
        self._response_recorded = False
        self._last_prompt_kind = kind
        self._hidden_by_user = False
        self.yes_button.setEnabled(True)
        self.later_button.setEnabled(True)
        self.yes_button.setText("Yes, drank it!")
        self.later_button.setText("Later")
        self.message.setText("Mommy, drink water? 💧")
        self._set_expression(True)
        # Keep the question hidden until Aadya finishes her entrance animation.
        self.bubble.hide()
        self.water_total.hide()
        if not self.isVisible():
            self.show()
        self.raise_()
        geo = self._available_geometry()
        target_x = geo.left() + 28  # settle near the left side of the desktop
        target_y = geo.bottom() - self.height() - 10
        self.move(geo.left() - self.width() + 4, target_y)
        if kind == "welcome":
            self._use_animation("dance_happy")
        else:
            self._use_animation("happy_walk")
        self._walk_to(target_x, target_y, self._prompt_arrived)

    def _prompt_arrived(self):
        self._walking = False
        self._current_mode = "prompt"
        self._prompt_active = True
        self._set_expression(True)
        self.bubble.show()
        self.water_total.show()
        self.raise_()

    def answer_yes(self):
        if self._response_recorded:
            return
        self._response_recorded = True
        self.yes_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.data["water_ml"] = int(self.data.get("water_ml", 0)) + self.serving_ml
        self.data.setdefault("events", []).append({
            "time": now_stamp(), "action": "drank_water", "ml": self.serving_ml
        })
        self._save_data()
        self.update_total_label()
        self.message.setText(f"Yay! 💖 {self.data['water_ml']} ml logged today!")
        self._set_expression(True)
        self._use_animation("happy_walk")
        self._prompt_active = False
        self.reminder_timer.start(self.normal_minutes * 60_000)
        QTimer.singleShot(900, lambda: self._walk_away_and_hide("happy_walk"))

    def answer_later(self):
        if self._response_recorded:
            return
        self._response_recorded = True
        self.yes_button.setEnabled(False)
        self.later_button.setEnabled(False)
        self.data.setdefault("events", []).append({"time": now_stamp(), "action": "later"})
        self._save_data()
        self.message.setText("Okay, I'll remind you in 5 minutes 🥺")
        # First show the still sad portrait (aadya_sad.png) so the reaction is visible.
        # After a short pause, switch to the sad walking frames and exit to the left.
        self._set_expression(False)
        self._prompt_active = False
        self.reminder_timer.start(5 * 60_000)
        QTimer.singleShot(1100, lambda: self._walk_away_and_hide("sad_walk"))

    def _walk_away_and_hide(self, animation_name="happy_walk"):
        self.bubble.hide()
        self.water_total.hide()
        geo = self._available_geometry()
        self._use_animation(animation_name)
        # Walk left and continue just beyond the visible screen before hiding.
        target_x = geo.left() - self.width() - 12
        def finish():
            self.hide()
            self._walking = False
            self._current_mode = "hidden"
        self._walk_to(target_x, self.y(), finish)
        # _walk_to normally clamps targets to the visible area; allow a left-side exit.
        self._walk_target_x = target_x

    def _on_reminder_due(self):
        # Hidden-by-user is not permanent: reminder causes Aadya to return.
        self._begin_prompt("normal")

    def hide_by_user(self):
        self._hidden_by_user = True
        self._prompt_active = False
        self.bubble.hide()
        self.water_total.hide()
        self.hide()
        self._walking = False
        self._current_mode = "hidden"
        # The existing reminder timer is intentionally left running.

    def build_water_context(self, question):
        """Read water_log.json afresh and prepare factual data for the selected question."""
        try:
            raw = json.loads(DATA_FILE.read_text())
        except Exception:
            raw = self.data if isinstance(self.data, dict) else {}

        records = {}
        for item in raw.get("history", []):
            if item.get("date"):
                records[item["date"]] = item
        if raw.get("date"):
            records[raw["date"]] = raw

        def total_for(record):
            events = record.get("events", record.get("entries", [])) or []
            logged = sum(
                int(event.get("ml", 0) or 0)
                for event in events
                if event.get("action") == "drank_water" and int(event.get("ml", 0) or 0) > 0
            )
            # Use recorded water_ml only when event-level entries are unavailable.
            return logged if events else int(record.get("water_ml", 0) or 0)

        today = date.today()
        today_key = today.isoformat()
        today_record = records.get(today_key)
        today_goal = int((today_record or {}).get(
            "target_ml", self.settings.get("daily_goal_ml", 2500)
        ) or self.settings.get("daily_goal_ml", 2500))
        week = []
        for offset in range(6, -1, -1):
            day = today - __import__("datetime").timedelta(days=offset)
            key = day.isoformat()
            record = records.get(key)
            week.append({
                "date": key,
                "recorded": record is not None,
                "water_ml": total_for(record) if record is not None else None,
                "target_ml": int(record.get("target_ml", self.settings.get("daily_goal_ml", 2500))) if record else None,
            })
        recorded_week = [entry for entry in week if entry["recorded"]]
        highest = max(recorded_week, key=lambda entry: entry["water_ml"], default=None)
        return {
            "source_file": str(DATA_FILE),
            "today": today_key,
            "today_recorded": today_record is not None,
            "today_water_ml": total_for(today_record) if today_record is not None else None,
            "today_target_ml": today_goal,
            "today_progress_percent": round(total_for(today_record) * 100 / today_goal) if today_record is not None and today_goal > 0 else None,
            "last_7_days": week,
            "highest_intake_day_in_available_last_7_days": highest,
            "note": "Missing records mean data was not recorded/available; do not describe missing data as zero intake."
        }

    def open_chatbot(self):
        """Open the static-question chatbot without changing Aadya's desktop animation."""
        self._check_new_day()
        # "Show Aadya" now opens the chatbot only. In particular, do not call
        # show_from_tray(): if Aadya is finishing her happy/sad walk-away animation,
        # that animation should continue naturally without being restarted or redirected.
        if getattr(self, "_chatbot_window", None) is not None:
            try:
                if self._chatbot_window.isVisible():
                    self._chatbot_window.raise_()
                    self._chatbot_window.activateWindow()
                    return
            except RuntimeError:
                self._chatbot_window = None
        self._chatbot_window = WaterChatbotDialog(self)
        self._chatbot_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._chatbot_window.show()
        self._chatbot_window.raise_()
        self._chatbot_window.activateWindow()

    def show_from_tray(self):
        # Do not redirect an already-visible Aadya when the tray/menu is clicked.
        # This prevents a dashboard/menu interaction from changing the direction
        # of an in-progress happy_walk or sad_walk animation.
        was_visible = self.isVisible()
        self._hidden_by_user = False
        if not was_visible:
            self.show()
            self.raise_()
            self.water_total.show()
            self._walk_to(
                self._available_geometry().left() + 30,
                self._available_geometry().bottom() - self.height() - 8
            )
        else:
            self.raise_()
        if not self._prompt_active:
            self.bubble.hide()

    def _tray_activated(self, reason):
        # Show Aadya is a chatbot action now. Ignore bare tray-icon activation
        # so macOS doesn't also restore the desktop sticker and start a walk.
        # The desktop companion returns naturally on its next water reminder.
        return

    def show_log(self):
        self._check_new_day()
        events = self.data.get("events", [])
        lines = [f"Date: {self.data.get('date')}", f"Total water: {self.data.get('water_ml', 0)} ml", "", "Today's events:"]
        if not events:
            lines.append("No events recorded today.")
        for e in events:
            lines.append(f"{e.get('time', '')} — {e.get('action', '')}" + (f" ({e.get('ml')} ml)" if e.get("ml") else ""))
        QMessageBox.information(self, "Aadya — Today's Log", "\n".join(lines))

    def open_dashboard(self):
        self._check_new_day()
        # Opening the dashboard must not reset Aadya's active animation, frame
        # phase, walking target, or travel direction.
        # Keep the dashboard non-modal: Aadya's floating Yes/Later buttons
        # must remain clickable while the dashboard is open.
        if getattr(self, "_dashboard_window", None) is not None:
            try:
                if self._dashboard_window.isVisible():
                    self._dashboard_window.raise_()
                    self._dashboard_window.activateWindow()
                    return
            except RuntimeError:
                self._dashboard_window = None
        self._dashboard_window = WaterDashboard(self)
        self._dashboard_window.setModal(False)
        self._dashboard_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._dashboard_window.show()
        self._dashboard_window.raise_()
        self.update_total_label()

    def open_settings(self):
        dialog = SettingsDialog(
            self, self.normal_minutes, self.serving_ml,
            int(self.settings.get("daily_goal_ml", 2500))
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.normal_minutes = dialog.reminder.value()
            self.serving_ml = dialog.serving.value()
            # Support either a QComboBox (label such as "2,500 ml") or
            # a QSpinBox (numeric target), depending on the SettingsDialog version.
            if hasattr(dialog.daily_goal, "currentText"):
                goal_text = dialog.daily_goal.currentText()
                self.settings["daily_goal_ml"] = int(goal_text.replace(",", "").split()[0])
            else:
                self.settings["daily_goal_ml"] = int(dialog.daily_goal.value())
            today_key = date.today().isoformat()
            self.settings.setdefault("daily_goal_history", {})[today_key] = self.settings["daily_goal_ml"]
            self.data["target_ml"] = self.settings["daily_goal_ml"]
            self._save_settings()
            self._save_data()
            self.reminder_timer.start(self.normal_minutes * 60_000)

    def _check_new_day(self):
        today = date.today().isoformat()
        if self.data.get("date") == today:
            return
        self.data.setdefault("history", []).append({
            "date": self.data.get("date"),
            "water_ml": self.data.get("water_ml", 0),
            "events": self.data.get("events", [])
        })
        self.data.update({"date": today, "water_ml": 0, "events": []})
        self._save_data()
        self.update_total_label()

    def closeEvent(self, event):
        # Window close hides the buddy; explicit Quit action fully stops the app.
        event.ignore()
        self.hide_by_user()

    def quit_app(self):
        self.reminder_timer.stop()
        self.animation_timer.stop()
        self.frame_timer.stop()
        self.idle_timer.stop()
        self.tray.hide()
        QApplication.quit()

