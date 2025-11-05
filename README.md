# Beeper-X

Beeper-X is a simple graphical tool built with Python and PyQt6 that converts MIDI files (`.mid`, `.midi`) into shell scripts containing Linux `beep` commands.

It allows you to:
- Open or drag and drop a MIDI file into the window  
- Convert it into a `.sh` script ready to play using the `beep` command  
- Run and stop the generated script directly from the interface  
- Choose how overlapping notes are interpreted (highest, lowest, or average)  
- Switch between light and dark mode  

---

## System Requirements

Beeper-X **works only on Linux** systems, because it relies on the native `beep` command.

To use it, you must:
1. Have a **PC speaker (internal buzzer)** physically installed and enabled in your BIOS.
2. Install the `beep` utility:
   ```bash
   sudo apt install beep ``` 
