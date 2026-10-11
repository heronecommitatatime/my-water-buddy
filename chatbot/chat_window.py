"""Local Ollama chatbot UI and asynchronous model worker."""
import json
import urllib.request
import urllib.error

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser, QPushButton

from config import HAPPY_PATH

class OllamaAnswerWorker(QThread):
    """Ask the local Ollama server without blocking the Qt UI thread."""
    answer_ready = Signal(str)

    def __init__(self, question, water_context, parent=None):
        super().__init__(parent)
        self.question = question
        self.water_context = water_context

    def run(self):
        prompt = (
            "You are Aadya, a warm and encouraging water-tracking buddy. "
            "Answer the user's question using ONLY the supplied water-log data. "
            "Do not invent missing numbers or claim an unrecorded day had zero intake. "
            "If data is missing, say it is not recorded. Keep the answer friendly, concise, "
            "and easy to read. This is hydration tracking, not medical advice.\n\n"
            f"Water-log data (JSON):\n{json.dumps(self.water_context, ensure_ascii=False)}\n\n"
            f"Question: {self.question}\nAnswer:"
        )
        payload = json.dumps({
            "model": "qwen3:8b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
            answer = (result.get("response") or "").strip()
            # Qwen3 may include an internal thinking section in its response.
            if "</think>" in answer:
                answer = answer.rsplit("</think>", 1)[-1].strip()
            if not answer:
                answer = "I couldn't form an answer from the water log. Please try again."
        except urllib.error.URLError:
            answer = ("I can't reach Ollama right now. Please make sure Ollama is running "
                      "and the qwen3:8b model is available.\n\nIn Terminal, run:\n"
                      "ollama serve\n\nIn another Terminal window, run:\nollama run qwen3:8b")
        except Exception as exc:
            answer = f"Sorry Mommy, I couldn't get an answer from the local model.\nDetails: {exc}"
        self.answer_ready.emit(answer)


class WaterChatbotDialog(QDialog):
    """Small static-question chatbot backed by the local water log and Ollama."""
    QUESTIONS = [
        "How much water did I drink today?",
        "Am I drinking enough water today?",
        "How much water did I drink this week?",
        "Which day did I drink the most water?",
    ]

    def __init__(self, buddy):
        super().__init__(buddy)
        self.buddy = buddy
        self.worker = None
        self.setWindowTitle("Aadya Water Buddy — Ask AI")
        self.resize(470, 570)
        self.setMinimumSize(420, 500)
        self.setStyleSheet("""
            QDialog { background: #F4F9FF; color: #17324D; }
            QLabel#heading { color: #153E61; font-size: 22px; font-weight: 800; }
            QLabel#subtitle { color: #67829A; font-size: 12px; }
            QPushButton { background: #FFFFFF; color: #1C659F; border: 1px solid #C9DFF3;
                border-radius: 11px; padding: 11px 12px; text-align: left; font-weight: 650; }
            QPushButton:hover { background: #E5F1FC; border-color: #78B9EF; }
            QPushButton:disabled { color: #8AA0B5; background: #EDF3F8; }
            QPushButton#closeButton { background: #247FD1; color: white; text-align: center; }
            QTextBrowser { background: #FFFFFF; color: #17324D; border: 1px solid #D9EAFB;
                border-radius: 12px; padding: 10px; font-size: 13px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(10)

        # Header: small happy Aadya sticker beside the chatbot greeting.
        header = QHBoxLayout()
        header.setSpacing(12)
        self.happy_sticker = QLabel()
        self.happy_sticker.setFixedSize(76, 76)
        self.happy_sticker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.happy_sticker.setStyleSheet("background: transparent;")
        sticker_source = QPixmap(str(HAPPY_PATH))
        if not sticker_source.isNull():
            self.happy_sticker.setPixmap(
                sticker_source.scaled(
                    72, 72,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        else:
            self.happy_sticker.setText("💧")
            self.happy_sticker.setStyleSheet("font-size: 42px; background: transparent;")

        header_text = QVBoxLayout()
        header_text.setSpacing(4)
        heading = QLabel("Hi Mommy! 💧 Ask AI")
        heading.setObjectName("heading")
        subtitle = QLabel("Choose a question. I'll check your saved water log using local AI.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        header_text.addWidget(heading)
        header_text.addWidget(subtitle)
        header.addWidget(self.happy_sticker, 0, Qt.AlignmentFlag.AlignTop)
        header.addLayout(header_text, 1)
        layout.addLayout(header)
        self.answer = QTextBrowser()
        self.answer.setOpenExternalLinks(False)
        self.answer.setMinimumHeight(145)
        self.answer.setPlainText("Your water buddy is ready! Choose one of the questions below. 🌷")
        layout.addWidget(self.answer, 1)
        self.question_buttons = []
        for question in self.QUESTIONS:
            button = QPushButton("💧  " + question)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, q=question: self.ask(q))
            self.question_buttons.append(button)
            layout.addWidget(button)
        close_button = QPushButton("Close")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.hide)
        layout.addWidget(close_button)

    def ask(self, question):
        if self.worker is not None and self.worker.isRunning():
            return
        context = self.buddy.build_water_context(question)
        self.answer.setPlainText("Aadya is checking your water log… 💧\n\nThe local model may take a little while to respond.")
        for button in self.question_buttons:
            button.setEnabled(False)
        self.worker = OllamaAnswerWorker(question, context, self)
        self.worker.answer_ready.connect(self._show_answer)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _show_answer(self, answer):
        self.answer.setPlainText(answer)

    def _worker_finished(self):
        for button in self.question_buttons:
            button.setEnabled(True)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

