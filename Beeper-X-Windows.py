"""
Beeper-X - MIDI → Beep Converter with Drag&Drop and Stop
--------------------------------------------------------
License: MIT
"""

import sys, os, json, time, subprocess, ctypes
import mido
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QMessageBox, QComboBox,
    QMainWindow, QMenuBar, QMenu, QStatusBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

SETTINGS_FILE = "beeperx_settings.json"

# --------------------- RISORSE E PATH (ONEFILE COMPATIBILE) ---------------------
def resource_path(relative_path):
    """ Ottiene il percorso assoluto delle risorse, compatibile con PyInstaller e script normale """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

# --------------------- NASCONDI IL TERMINALE ----------------------------
def hide_console():
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0) # 0 = SW_HIDE (Nasconde la console)
    except Exception:
        pass

# --------------------- AUTO-ELEVATION ADMIN ----------------------------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate_if_needed():
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        # 1 = SW_SHOWNORMAL (Mostra correttamente la GUI dopo l'elevazione UAC)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit(0)

# --------------------- MIDI PARSER SAFE (TIMELINE MONOFONICA) ----------------------------
class MidiToNotesConverter:
    def __init__(self, note_mode='highest'):
        self.note_mode = note_mode

    def parse_midi(self, midi_path):
        midifile = mido.MidiFile(midi_path)
        track = mido.merge_tracks(midifile.tracks)

        current_bpm = 120
        ticks_per_beat = midifile.ticks_per_beat if midifile.ticks_per_beat else 480
        
        active_notes = set()
        events_timeline = []
        current_time_ms = 0.0

        for event in track:
            delta_ms = (event.time / ticks_per_beat) * (60000.0 / current_bpm)
            current_time_ms += delta_ms

            if event.type == 'set_tempo':
                try:
                    current_bpm = mido.tempo2bpm(event.tempo)
                except Exception:
                    current_bpm = 120

            elif event.type == 'note_on':
                if getattr(event, 'velocity', 0) > 0:
                    active_notes.add(event.note)
                else:
                    active_notes.discard(event.note)
                
                freq = self.select_note(active_notes)
                events_timeline.append((current_time_ms, freq))

            elif event.type == 'note_off':
                active_notes.discard(event.note)
                freq = self.select_note(active_notes)
                events_timeline.append((current_time_ms, freq))

        # Conversione della timeline in sequenza pulita (frequenza, durata_ms)
        notes_sequence = []
        last_time = 0.0
        
        for i in range(len(events_timeline)):
            t, freq = events_timeline[i]
            duration = int(t - last_time)
            
            if duration > 0:
                prev_freq = events_timeline[i-1][1] if i > 0 else 0
                notes_sequence.append((prev_freq, duration))
            
            last_time = t

        return notes_sequence

    def select_note(self, notes):
        if not notes:
            return 0
        notes_list = list(notes)
        if self.note_mode == 'highest':
            note = max(notes_list)
        elif self.note_mode == 'lowest':
            note = min(notes_list)
        elif self.note_mode == 'average':
            note = sum(notes_list) // len(notes_list)
        else:
            note = notes_list[-1]
        
        note = max(0, min(127, note))
        return round(440 * 2 ** ((note - 69) / 12))

# --------------------- PLAYBACK THREAD ---------------------
class PlaybackThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, notes_sequence, exe_path):
        super().__init__()
        self.notes_sequence = notes_sequence
        self.exe_path = exe_path
        self._is_running = True
        self.current_proc = None

    def run(self):
        total = len(self.notes_sequence)
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        for idx, (freq, duration) in enumerate(self.notes_sequence):
            if not self._is_running:
                break
            
            percent = int((idx / total) * 100)
            self.progress.emit(percent, f"Playing: {idx+1}/{total} notes...")

            if freq > 0 and duration > 0:
                try:
                    self.current_proc = subprocess.Popen(
                        [self.exe_path, "-f", str(freq), "-d", str(duration)],
                        creationflags=creation_flags
                    )
                    self.current_proc.wait()
                except Exception:
                    pass
            else:
                time.sleep(duration / 1000.0)

        if self._is_running:
            self.progress.emit(100, "Playback finished!")
            self.finished.emit(True, "Finished playing successfully.")
        else:
            self.stop_hardware_speaker()
            self.finished.emit(False, "Playback stopped by user.")

    def stop(self):
        self._is_running = False
        if self.current_proc and self.current_proc.poll() is None:
            try:
                self.current_proc.kill()
            except Exception:
                pass
        self.stop_hardware_speaker()

    def stop_hardware_speaker(self):
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            subprocess.run(["taskkill", "/F", "/IM", "beeper.exe"], creationflags=creation_flags, capture_output=True)
            if os.path.exists(self.exe_path):
                subprocess.run([self.exe_path, "-f", "37", "-d", "1"], creationflags=creation_flags, capture_output=True)
        except Exception:
            pass

# --------------------- MAIN WINDOW ----------------------------
class BeeperX(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Beeper-X")
        self.setFixedSize(600, 450)
        
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.settings = self.load_settings()
        self.playback_thread = None
        self.current_notes = None
        self.setAcceptDrops(True)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.label = QLabel("Open a MIDI file or drag it here")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)

        self.note_mode_combo = QComboBox()
        self.note_mode_combo.addItems(['highest', 'lowest', 'average'])
        self.layout.addWidget(self.note_mode_combo)

        self.output_dir = get_base_dir()
        self.output_label = QLabel(f"Output folder: {self.output_dir}")
        self.layout.addWidget(self.output_label)

        self.btn_select_file = QPushButton("📂 Open MIDI")
        self.btn_select_file.clicked.connect(self.select_file)
        self.layout.addWidget(self.btn_select_file)

        self.btn_run = QPushButton("▶ Play MIDI")
        self.btn_run.clicked.connect(self.run_playback)
        self.btn_run.setEnabled(False)
        self.layout.addWidget(self.btn_run)

        self.btn_stop = QPushButton("■ Stop execution")
        self.btn_stop.clicked.connect(self.stop_playback)
        self.btn_stop.setEnabled(False)
        self.layout.addWidget(self.btn_stop)

        self.progress = QProgressBar()
        self.layout.addWidget(self.progress)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)
        file_menu = self.menu_bar.addMenu("File")
        file_menu.addAction("Open MIDI").triggered.connect(self.select_file)
        file_menu.addAction("Output folder").triggered.connect(self.select_output_dir)
        file_menu.addAction("Exit").triggered.connect(self.close)
        settings_menu = self.menu_bar.addMenu("Settings")
        self.dark_mode_action = settings_menu.addAction("Dark Mode")
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setChecked(self.settings.get("dark_mode", True))
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        help_menu = self.menu_bar.addMenu("Help")
        help_menu.addAction("About").triggered.connect(self.show_info)

        self.apply_stylesheet()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.load_midi(urls[0].toLocalFile())

    def load_settings(self):
        settings_path = os.path.join(get_base_dir(), SETTINGS_FILE)
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_settings(self):
        settings_path = os.path.join(get_base_dir(), SETTINGS_FILE)
        try:
            with open(settings_path, 'w') as f:
                json.dump(self.settings, f)
        except:
            pass

    def apply_stylesheet(self):
        if self.settings.get("dark_mode", True):
            self.setStyleSheet("""
            QMainWindow{background-color:#1A1A2E;color:#FFD369;font-family:'Courier New';}
            QPushButton{background-color:#6F1E51;border-radius:8px;padding:8px;color:#FFD369;font-weight:bold;}
            QPushButton:hover{background-color:#9B1D87;}
            QLabel{font-size:14px;}
            QProgressBar{border:2px solid #3A3A5E;border-radius:8px;height:20px;text-align:center;color:#FFD369;background-color:#12122A;}
            QProgressBar::chunk{background-color:#FF6F91;border-radius:8px;}
            QComboBox{background-color:#6F1E51;border-radius:6px;padding:3px;color:#FFD369;}
            QMenuBar{background-color:#1A1A2E;color:#FFD369;}
            QMenu{background-color:#1A1A2E;color:#FFD369;}
            QStatusBar{background-color:#12122A;color:#FFD369;}
            """)
        else:
            self.setStyleSheet("")

    def toggle_dark_mode(self):
        self.settings["dark_mode"] = self.dark_mode_action.isChecked()
        self.save_settings()
        self.apply_stylesheet()

    def show_info(self):
        QMessageBox.information(self, "Beeper-X", "Beeper-X (Beeper Windows Edition)\nConvert & Play MIDI on PC Speaker.\nVersion: 1.1\nAuthor: DottSpace \n\nIt uses '/cocafe/pc-beeper' to generate sounds \n\nLicense: MIT")

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select MIDI File", "", "MIDI Files (*.mid *.midi)")
        if file_path:
            self.load_midi(file_path)

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output folder")
        if dir_path:
            self.output_dir = dir_path
            self.output_label.setText(f"Output folder: {self.output_dir}")

    def load_midi(self, midi_path):
        try:
            beeper_exe = os.path.join(get_base_dir(), "beeper.exe")
            if not os.path.exists(beeper_exe):
                QMessageBox.critical(self, "Error", f"'beeper.exe' non trovato nella cartella:\n{get_base_dir()}")
                return

            self.status.showMessage("Parsing MIDI...")
            converter = MidiToNotesConverter(note_mode=self.note_mode_combo.currentText())
            self.current_notes = converter.parse_midi(midi_path)
            
            self.btn_run.setEnabled(True)
            self.status.showMessage(f"Loaded {os.path.basename(midi_path)} - {len(self.current_notes)} events ready.")
            self.progress.setValue(0)
            QMessageBox.information(self, "Ready", f"File parsed successfully!\nEvents: {len(self.current_notes)}")
        except Exception as e:
            QMessageBox.critical(self, "Parsing Error", f"Failed to parse MIDI: {e}")
            self.status.showMessage("Parsing failed.")

    def run_playback(self):
        if not self.current_notes:
            return
        
        beeper_exe = os.path.join(get_base_dir(), "beeper.exe")
        self.playback_thread = PlaybackThread(self.current_notes, beeper_exe)
        self.playback_thread.progress.connect(self.update_progress)
        self.playback_thread.finished.connect(self.playback_finished)
        
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.playback_thread.start()

    def update_progress(self, value, message):
        self.progress.setValue(value)
        self.status.showMessage(message)

    def stop_playback(self):
        if self.playback_thread and self.playback_thread.isRunning():
            self.playback_thread.stop()
            self.status.showMessage("Stopping playback...")

    def playback_finished(self, success, message):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status.showMessage(message)

# --------------------- MAIN -----------------------------
def main():
    elevate_if_needed()
    hide_console()

    app = QApplication(sys.argv)
    
    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = BeeperX()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
