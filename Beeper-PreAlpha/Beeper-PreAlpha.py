import os
import sys
import subprocess
import tempfile
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class ConversionThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, midi_path):
        super().__init__()
        self.midi_path = midi_path

    def run(self):
        try:
            if not os.path.exists(self.midi_path):
                self.finished.emit(False, "Error: MIDI file does not exist!")
                return

            base_name = os.path.splitext(os.path.basename(self.midi_path))[0]
            self.progress.emit(10, "Creating temporary file...")

            tmp_grub = tempfile.NamedTemporaryFile(delete=False, suffix=".grub")
            tmp_grub_name = tmp_grub.name
            tmp_grub.close()

            # Step 1: MIDI → GRUB
            self.progress.emit(30, "Converting MIDI → GRUB...")
            result = subprocess.run(
                [sys.executable, 'midi2grub.py', self.midi_path],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                os.remove(tmp_grub_name)
                self.finished.emit(False, f"Error in midi2grub.py:\n{result.stderr}")
                return

            with open(tmp_grub_name, "w", encoding="ascii") as f:
                f.write(result.stdout)

            # Step 2: GRUB → SH
            self.progress.emit(70, "Converting GRUB → Shell script (.sh)...")
            sh_file = f"{base_name}.sh"
            cmd = [sys.executable, 'grub2beep.py', tmp_grub_name]
            with open(sh_file, "w", encoding="ascii") as f:
                result = subprocess.run(cmd, stdout=f, text=True)

            if result.returncode != 0:
                os.remove(tmp_grub_name)
                self.finished.emit(False, "Error in grub2beep.py")
                return

            os.remove(tmp_grub_name)
            self.progress.emit(100, "Conversion completed!")
            self.finished.emit(True, sh_file)

        except Exception as e:
            self.finished.emit(False, f"Unexpected error: {e}")


class MidiConverterUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 MIDI → GRUB → Beep Converter")
        self.setFixedSize(480, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Updated stylesheet (no unsupported properties)
        self.setStyleSheet("""
            QWidget {
                background-color: #12121C;
                color: #EDEDED;
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5A5AFD, stop:1 #00E0FF
                );
                border: none;
                border-radius: 12px;
                padding: 10px 14px;
                font-weight: bold;
                font-size: 15px;
                color: white;
            }
            QPushButton:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6A6AFF, stop:1 #33F3FF
                );
            }
            QLabel {
                font-size: 15px;
                letter-spacing: 0.4px;
            }
            QProgressBar {
                border: 2px solid #222236;
                border-radius: 10px;
                background-color: #1A1A28;
                height: 20px;
                text-align: center;
                color: #EDEDED;
            }
            QProgressBar::chunk {
                border-radius: 10px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00FFCC, stop:1 #0066FF
                );
            }
        """)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Select a MIDI file to convert")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button_select = QPushButton("📂 Choose MIDI File")
        self.button_select.setFixedWidth(220)
        self.button_select.clicked.connect(self.select_file)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFixedWidth(340)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(self.label)
        layout.addSpacing(8)
        layout.addWidget(self.button_select, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(16)
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        self.setLayout(layout)

        self.thread = None

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select MIDI File", "", "MIDI Files (*.mid *.midi)"
        )
        if not file_path:
            return
        self.start_conversion(file_path)

    def start_conversion(self, midi_path):
        self.progress.setValue(0)
        self.status_label.setText("Starting conversion...")
        self.thread = ConversionThread(midi_path)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.conversion_finished)
        self.thread.start()

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status_label.setText(message)

    def conversion_finished(self, success, message):
        if success:
            QMessageBox.information(
                self, "✅ Conversion Completed!",
                f"Shell script created:\n{message}"
            )
            self.status_label.setText(f"File created: {message}")
        else:
            QMessageBox.critical(self, "❌ Error", message)
            self.status_label.setText("Conversion failed.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MidiConverterUI()
    window.show()
    sys.exit(app.exec())
