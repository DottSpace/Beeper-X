# Beeper-X

Beeper-X is a simple graphical tool built with Python and PyQt6 that converts MIDI files (.mid, .midi) into shell scripts containing Linux beep commands.

It allows you to:
- Open or drag and drop a MIDI file into the window  
- Convert it into a .sh script ready to play using the beep command  
- Run and stop the generated script directly from the interface  
- Choose how overlapping notes are interpreted (highest, lowest, or average)  
- Switch between light and dark mode  

---

## System Requirements

Beeper-X works only on Linux systems, because it relies on the native beep command.

To use it, you must:
1. Have a PC speaker (internal buzzer) physically installed and enabled in your BIOS  
2. Install the beep utility:
    ``` sudo apt install beep ```
3. Install the beep driver:
    ```sudo modprobe pcspkr```  
4. Ensure your user has permission to run beep. In some systems, it may require superuser privileges or access to /dev/console

---

## Installation

1. Clone this repository:
   git clone https://github.com/DottSpace/Beeper-X.git
   cd beeper-x

2. Create and activate a virtual environment (optional but recommended):
   python -m venv venv
   source venv/bin/activate  # Linux / macOS
   venv\Scripts\activate     # Windows (for testing only, execution won't work)

3. Install dependencies:
   pip install -r requirements.txt

4. Run the application:
   python3 Beeper-X.py

---

## Usage

1. Open or drag a MIDI file into the main window  
2. Wait for the conversion to finish — a .sh file will be created in the selected output directory  
3. You can run the file directly from the interface or manually using:
   bash your_file.sh  
4. Use the Stop Execution button to interrupt playback at any time

---

## Note Modes

During conversion, you can choose how simultaneous notes are handled:
- highest — keeps the highest note  
- lowest — keeps the lowest note  
- average — uses the average pitch  

---

## Dependencies

All dependencies are listed in requirements.txt:
PyQt6>=6.6.0  
mido>=1.3.0  
python-rtmidi>=1.5.8  

---

## Optional: Create an Executable

You can package Beeper-X as a standalone executable using PyInstaller:
pip install pyinstaller  
pyinstaller --onefile --windowed beeperx.py  

The executable will be located in the dist/ directory

---

## License

This project is distributed under the MIT License  
You may freely use, modify, and share it

---

## Author

DottSpace12  
Make your computer beep like it’s 1999
