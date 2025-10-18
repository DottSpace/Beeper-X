"""
Beeper 2.0 - Super Precise MIDI → Beep Converter
-------------------------------------------------------------
Inspired by the original concept of Lukas Fink (2019) for MIDI → GRUB conversion.
License: MIT
GUI & logic improved by: DottSpace12
"""

import sys
import os
import struct
import mido

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QMessageBox, QComboBox, QHBoxLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# ==============================================================
# --------------------- SECTION 1: MIDI → GRUB -----------------
# ==============================================================

class MidiToGrubConverter:
    def __init__(self, note_mode='highest', channel=None):
        self.note_mode = note_mode  # 'highest', 'lowest', 'average'
        self.channel = channel

    def convert(self, midi_path):
        midifile = mido.MidiFile(midi_path)

        # Merge tracks, filtering only note_on/off
        track = mido.merge_tracks(midifile.tracks)

        # Dynamic BPM calculation
        current_bpm = 120
        ticks_per_beat = midifile.ticks_per_beat

        note_on = []
        accu_ticks = 0
        result = []

        for event in track:
            accu_ticks += event.time
            if self.channel is not None and getattr(event, 'channel', None) != self.channel:
                continue

            if event.type == 'set_tempo':
                current_bpm = mido.tempo2bpm(event.tempo)

            if event.type == 'note_off' or (event.type == 'note_on' and event.velocity == 0):
                if note_on and accu_ticks > 0:
                    freq = self.select_note(note_on)
                    result.append(f" {freq} {accu_ticks}")
                    accu_ticks = 0
                try:
                    note_on.remove(event.note)
                except ValueError:
                    pass

            elif event.type == 'note_on':
                if accu_ticks > 0:
                    if note_on:
                        freq = self.select_note(note_on)
                        result.append(f" {freq} {accu_ticks}")
                    else:
                        result.append(f" 0 {accu_ticks}")
                    accu_ticks = 0
                note_on.append(event.note)

        return f"{round(current_bpm * ticks_per_beat)}" + ''.join(result)

    def select_note(self, note_list):
        if not note_list:
            return 0
        if self.note_mode == 'highest':
            note = max(note_list)
        elif self.note_mode == 'lowest':
            note = min(note_list)
        elif self.note_mode == 'average':
            note = sum(note_list)//len(note_list)
        else:
            note = note_list[-1]
        return round(440 * 2 ** ((note - 69) / 12))

# ==============================================================
# --------------------- SECTION 2: GRUB → BEEP ----------------
# ==============================================================

def grub_to_beep(grub_text):
    notes = grub_text.strip().split(" ")
    tempo = int(notes[0])
    notes = notes[1:]
    output = []

    for i in range(0, len(notes), 2):
        if i + 1 >= len(notes):
            break
        freq = int(notes[i])
        duration = int(int(notes[i + 1]) / tempo * 1000 * 60)
        if freq == 0:
            output.append(f"-D {duration}")
        else:
            output.append(f"-n -f {freq} -l {duration}")

    final = " ".join(output).strip()
    if final.startswith("-n"):
        final = final[2:]
    return "beep " + final

# ==============================================================
# --------------------- SECTION 3: THREAD ---------------------
# ==============================================================

class ConversionThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, midi_path, note_mode='highest', channel=None):
        super().__init__()
        self.midi_path = midi_path
        self.note_mode = note_mode
        self.channel = channel

    def run(self):
        try:
            if not os.path.exists(self.midi_path):
                self.finished.emit(False, "MIDI file does not exist!")
                return

            converter = MidiToGrubConverter(note_mode=self.note_mode, channel=self.channel)
            self.progress.emit(20, "Converting MIDI → GRUB...")
            grub_data = converter.convert(self.midi_path)

            self.progress.emit(60, "Converting GRUB → BEEP...")
            beep_cmd = grub_to_beep(grub_data)

            base_name = os.path.splitext(os.path.basename(self.midi_path))[0]
            sh_file = f"{base_name}.sh"
            with open(sh_file, 'w', encoding='utf-8') as f:
                f.write(beep_cmd)

            self.progress.emit(100, "Conversion completed!")
            self.finished.emit(True, sh_file)

        except Exception as e:
            self.finished.emit(False, f"Unexpected error: {e}")

# ==============================================================
# --------------------- SECTION 4: GUI ------------------------
# ==============================================================

class Beeper2UI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Beeper 2.0 - 8-bit MIDI → Beep")
        self.setFixedSize(500, 350)
        self.setStyleSheet("""
            QWidget { background-color: #1A1A2E; color: #FFD369; font-family: 'Courier New'; }
            QPushButton {
                background-color: #6F1E51; border-radius: 8px;
                padding: 8px 12px; font-weight: bold; color: #FFD369;
            }
            QPushButton:hover { background-color: #9B1D87; }
            QLabel { font-size: 14px; }
            QProgressBar { border: 2px solid #3A3A5E; border-radius: 8px; background-color: #12122A; height: 20px; text-align: center; color: #FFD369; }
            QProgressBar::chunk { background-color: #FF6F91; border-radius: 8px; }
            QComboBox { background-color: #6F1E51; border-radius: 6px; padding: 3px; color: #FFD369; }
        """)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel("Select a MIDI file to convert")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button_select = QPushButton("📂 Choose MIDI File")
        self.button_select.clicked.connect(self.select_file)

        # Note mode dropdown
        self.note_mode_combo = QComboBox()
        self.note_mode_combo.addItems(['highest', 'lowest', 'average'])

        # Progress bar and status
        self.progress = QProgressBar()
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch(1)
        layout.addWidget(self.label)
        layout.addWidget(self.button_select)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Note mode:"))
        hbox.addWidget(self.note_mode_combo)
        layout.addLayout(hbox)

        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.setLayout(layout)
        self.thread = None

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select MIDI File", "", "MIDI Files (*.mid *.midi)")
        if file_path:
            self.start_conversion(file_path)

    def start_conversion(self, midi_path):
        note_mode = self.note_mode_combo.currentText()
        self.progress.setValue(0)
        self.status_label.setText("Starting conversion...")

        self.thread = ConversionThread(midi_path, note_mode=note_mode)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.conversion_finished)
        self.thread.start()

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status_label.setText(message)

    def conversion_finished(self, success, message):
        if success:
            QMessageBox.information(self, "✅ Conversion completed!", f"File created: {message}")
            self.status_label.setText(f"File created: {message}")
        else:
            QMessageBox.critical(self, "❌ Error", message)
            self.status_label.setText("Conversion failed.")

# ==============================================================
# --------------------- SECTION 5: MAIN ------------------------
# ==============================================================

def main():
    app = QApplication(sys.argv)
    window = Beeper2UI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
