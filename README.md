<img width="50" height="50" alt="buzzer(1)" src="https://github.com/user-attachments/assets/064d83b1-ed25-43cd-a43b-90c3bfe61a33" />


# Beeper-X

Beeper-X is a simple graphical tool built with Python and PyQt6 that converts MIDI files (.mid, .midi) into commands played directly on your motherboard's internal PC Speaker (buzzer).

It allows you to:
- Open or drag and drop a MIDI file into the window  
- Convert and play MIDI files directly using the internal PC speaker  
- Run and stop playback instantly from the interface with zero latency  
- Choose how overlapping notes are interpreted (highest, lowest, or average)  
- Switch between light and dark mode  

---

## Operating System Guides

### Linux Setup (Shell Scripting Mode)

On Linux, Beeper-X relies on the native beep system utility.

#### System Requirements:
1. Ensure a PC speaker (internal buzzer) is physically installed and enabled in your BIOS.  
2. Install the beep utility:  
   sudo apt install beep  
3. Load the PC speaker kernel module:  
   sudo modprobe pcspkr  
4. Ensure your user has permissions to write to /dev/console or execute beep.

#### Running from Source on Linux:
1. Clone the repository:  
   git clone https://github.com/DottSpace/Beeper-X.git  
   cd Beeper-X  
2. Create and activate a virtual environment (optional but recommended):  
   python3 -m venv venv  
   source venv/bin/activate  
3. Install dependencies:  
   pip install -r requirements.txt  
4. Launch the application:  
   python3 Beeper-X.py  

---

### Windows Setup (Direct Hardware Mode)

On Windows, Beeper-X interacts directly with motherboard I/O ports via the WinRing0 driver to trigger the System Speaker hardware directly.

#### Option A: Download the Executable (Recommended)
1. Download the pre-compiled Beeper-X.exe from the Releases section (https://github.com/DottSpace/Beeper-X/releases).
2. Ensure Beeper-X.exe is in the same directory as the required driver files:
   - beeper.exe
   - WinRing0x64.dll
   - WinRing0x64.sys
3. Launch Beeper-X.exe. Grant Administrator privileges when prompted by Windows UAC (required for loading the hardware driver once at startup).

#### Option B: Run from Source / Build on Windows
1. Clone the repository:  
   git clone https://github.com/DottSpace/Beeper-X.git  
   cd Beeper-X  
2. Install dependencies:  
   pip install -r requirements.txt  
3. Run the script or compile your own standalone executable:  
   pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." Beeper-X.py  
4. Move the generated Beeper-X.exe from the dist/ folder into the main directory alongside beeper.exe, WinRing0x64.dll, and WinRing0x64.sys.

---

## Usage

1. Open or drag a MIDI file into the main window  
2. Select your preferred note conversion mode  
3. Click Play MIDI to start playing music through the motherboard speaker  
4. Click Stop execution at any time to immediately interrupt playback and quiet the PC speaker  

---

## Note Modes

During conversion, you can choose how simultaneous notes (chords) are handled:
- highest — keeps the highest note (default, best for melodies)  
- lowest — keeps the lowest note  
- average — uses the average pitch  

---

## Dependencies

All dependencies are listed in requirements.txt:  
PyQt6>=6.6.0  
mido>=1.3.0  
python-rtmidi>=1.5.8  

---

## Credits & Acknowledgments

- Windows Engine: The Windows backend uses the pc-beeper low-level driver utility created by cocafe. All credits for the WinRing0 I/O port interface go to the original creator.  
  - Repository: https://github.com/cocafe/pc-beeper

---

## License

This project is distributed under the MIT License.  
You may freely use, modify, and share it.

---

## Author

DottSpace12  
Make your computer beep like it’s 1999!
