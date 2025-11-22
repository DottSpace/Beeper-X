"""
Beeper-X - MIDI → Beep Converter Ordinato con Drag&Drop e Stop
-------------------------------------------------------------
Autore: DottSpace12
Licenza: MIT
"""

import sys, os, json, subprocess, signal
import mido
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QMessageBox, QComboBox,
    QMainWindow, QMenuBar, QMenu, QStatusBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

SETTINGS_FILE = "beeperx_settings.json"

# --------------------- MIDI → GRUB ----------------------------
class MidiToGrubConverter:
    def __init__(self, note_mode='highest'):
        self.note_mode = note_mode

    def convert(self, midi_path):
        midifile = mido.MidiFile(midi_path)
        track = mido.merge_tracks(midifile.tracks)

        current_bpm = 120
        ticks_per_beat = midifile.ticks_per_beat
        note_on = []
        accu_ticks = 0
        result = []

        for event in track:
            accu_ticks += event.time
            if event.type == 'set_tempo': current_bpm = mido.tempo2bpm(event.tempo)
            if event.type in ['note_off', 'note_on'] and getattr(event, 'velocity', 0) == 0:
                if note_on and accu_ticks > 0: result.append(f" {self.select_note(note_on)} {accu_ticks}"); accu_ticks=0
                try: note_on.remove(event.note)
                except ValueError: pass
            elif event.type == 'note_on':
                if accu_ticks > 0: 
                    freq = self.select_note(note_on) if note_on else 0
                    result.append(f" {freq} {accu_ticks}"); accu_ticks=0
                note_on.append(event.note)
        return f"{round(current_bpm * ticks_per_beat)}" + ''.join(result)

    def select_note(self, notes):
        if not notes: return 0
        if self.note_mode == 'highest': note = max(notes)
        elif self.note_mode == 'lowest': note = min(notes)
        elif self.note_mode == 'average': note = sum(notes)//len(notes)
        else: note = notes[-1]
        return round(440 * 2 ** ((note - 69) / 12))

# --------------------- GRUB → BEEP ----------------------------
def grub_to_beep(grub_text):
    notes = grub_text.strip().split(" ")
    tempo = int(notes[0])
    notes = notes[1:]
    output=[]
    for i in range(0,len(notes),2):
        if i+1>=len(notes): break
        freq=int(notes[i])
        duration=int(int(notes[i+1])/tempo*1000*60)
        output.append(f"-D {duration}" if freq==0 else f"-n -f {freq} -l {duration}")
    final=" ".join(output).strip()
    if final.startswith("-n"): final=final[2:]
    return "beep "+final

# --------------------- THREAD CONVERSIONE ---------------------
class ConversionThread(QThread):
    progress = pyqtSignal(int,str)
    finished = pyqtSignal(bool,str)
    def __init__(self,midi_path,note_mode='highest',output_dir=None):
        super().__init__()
        self.midi_path=midi_path
        self.note_mode=note_mode
        self.output_dir=output_dir or os.getcwd()
    def run(self):
        try:
            if not os.path.exists(self.midi_path): self.finished.emit(False,"File MIDI inesistente!"); return
            converter=MidiToGrubConverter(note_mode=self.note_mode)
            self.progress.emit(20,"Convertendo MIDI → GRUB...")
            grub_data=converter.convert(self.midi_path)
            self.progress.emit(60,"Convertendo GRUB → BEEP...")
            beep_cmd=grub_to_beep(grub_data)
            base_name=os.path.splitext(os.path.basename(self.midi_path))[0]
            sh_file=os.path.join(self.output_dir,f"{base_name}.sh")
            with open(sh_file,'w',encoding='utf-8') as f: f.write(beep_cmd)
            self.progress.emit(100,"Conversione completata!")
            self.finished.emit(True,sh_file)
        except Exception as e: self.finished.emit(False,f"Errore imprevisto: {e}")

# --------------------- MAIN WINDOW ----------------------------
class BeeperX(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Beeper-X")
        self.setFixedSize(600,450)
        self.settings=self.load_settings()
        self.last_sh_file=None
        self.process=None
        self.setAcceptDrops(True)

        # Central widget
        self.central_widget=QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout=QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Label principale
        self.label=QLabel("Apri un file MIDI o trascinalo qui")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)

        # Dropdown modalità nota
        self.note_mode_combo=QComboBox()
        self.note_mode_combo.addItems(['highest','lowest','average'])
        self.layout.addWidget(self.note_mode_combo)

        # Cartella destinazione
        self.output_dir=os.getcwd()
        self.output_label=QLabel(f"Cartella output: {self.output_dir}")
        self.layout.addWidget(self.output_label)

        # Bottoni
        self.btn_select_file=QPushButton("📂 Apri MIDI")
        self.btn_select_file.clicked.connect(self.select_file)
        self.layout.addWidget(self.btn_select_file)

        self.btn_run_sh=QPushButton("▶ Esegui ultimo .sh")
        self.btn_run_sh.clicked.connect(self.run_last_sh)
        self.btn_run_sh.setEnabled(False)
        self.layout.addWidget(self.btn_run_sh)

        self.btn_stop_sh=QPushButton("■ Stop esecuzione")
        self.btn_stop_sh.clicked.connect(self.stop_sh)
        self.btn_stop_sh.setEnabled(False)
        self.layout.addWidget(self.btn_stop_sh)

        # Progress bar
        self.progress=QProgressBar()
        self.layout.addWidget(self.progress)

        # Status bar
        self.status=QStatusBar()
        self.setStatusBar(self.status)

        # Menu
        self.menu_bar=QMenuBar()
        self.setMenuBar(self.menu_bar)
        file_menu=self.menu_bar.addMenu("File")
        file_menu.addAction("Apri MIDI").triggered.connect(self.select_file)
        file_menu.addAction("Seleziona cartella output").triggered.connect(self.select_output_dir)
        file_menu.addAction("Esci").triggered.connect(self.close)
        settings_menu=self.menu_bar.addMenu("Impostazioni")
        self.dark_mode_action=settings_menu.addAction("Dark Mode")
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.setChecked(self.settings.get("dark_mode",True))
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        help_menu=self.menu_bar.addMenu("Aiuto")
        help_menu.addAction("Info").triggered.connect(self.show_info)

        self.apply_stylesheet()

    # ----------------- Drag & Drop --------------------------
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()
    def dropEvent(self,event):
        urls=event.mimeData().urls()
        if urls: self.start_conversion(urls[0].toLocalFile())

    # ----------------- SETTINGS -----------------------------
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE,'r') as f: return json.load(f)
        return {}
    def save_settings(self):
        with open(SETTINGS_FILE,'w') as f: json.dump(self.settings,f)
    def apply_stylesheet(self):
        if self.settings.get("dark_mode",True):
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
        else: self.setStyleSheet("")
    def toggle_dark_mode(self):
        self.settings["dark_mode"]=self.dark_mode_action.isChecked()
        self.save_settings()
        self.apply_stylesheet()
    def show_info(self):
        QMessageBox.information(self,"Beeper-X","Beeper-X\nConverti MIDI in comandi beep.\nAutore: DottSpace12")

    # ----------------- FILE -----------------------------
    def select_file(self):
        file_path,_=QFileDialog.getOpenFileName(self,"Seleziona File MIDI","","MIDI Files (*.mid *.midi)")
        if file_path: self.start_conversion(file_path)
    def select_output_dir(self):
        dir_path=QFileDialog.getExistingDirectory(self,"Seleziona cartella di destinazione")
        if dir_path: self.output_dir=dir_path; self.output_label.setText(f"Cartella output: {self.output_dir}")

    # ----------------- CONVERSIONE ----------------------
    def start_conversion(self,midi_path):
        note_mode=self.note_mode_combo.currentText()
        self.progress.setValue(0)
        self.status.showMessage("Avvio conversione...")
        self.thread=ConversionThread(midi_path,note_mode=note_mode,output_dir=self.output_dir)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.conversion_finished)
        self.thread.start()
    def update_progress(self,value,message): self.progress.setValue(value); self.status.showMessage(message)
    def conversion_finished(self,success,sh_file):
        if success:
            self.last_sh_file=sh_file
            self.btn_run_sh.setEnabled(True)
            QMessageBox.information(self,"✅ Conversione completata!",f"File creato: {sh_file}")
            self.status.showMessage(f"File creato: {sh_file}")
        else:
            QMessageBox.critical(self,"❌ Errore",sh_file)
            self.status.showMessage("Conversione fallita.")

    # ----------------- ESECUZIONE .SH -------------------
    def run_last_sh(self):
        if not self.last_sh_file:
            QMessageBox.warning(self, "⚠️ Nessun file", "Non hai ancora convertito nessun file .sh!")
            return
        try:
            # Lancia il .sh in un nuovo process group
            self.process = subprocess.Popen(
                ["bash", self.last_sh_file],
                preexec_fn=os.setsid  # crea un nuovo process group
            )
            self.btn_stop_sh.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "❌ Errore", f"Errore nell'esecuzione: {e}")

    def stop_sh(self):
        if self.process:
            # Termina l'intero process group
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None
            QMessageBox.information(self, "■ Stop", "Esecuzione interrotta.")
            self.btn_stop_sh.setEnabled(False)

# --------------------- MAIN -----------------------------
def main():
    app=QApplication(sys.argv)
    window=BeeperX()
    window.show()
    sys.exit(app.exec())

if __name__=='__main__':
    main()
