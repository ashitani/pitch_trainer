# Pitch Trainer

A pitch training application with MIDI input/output functionality.

https://github.com/user-attachments/assets/681d9afd-fbf1-418f-bb88-b4e817b7473e

## Requirements

- Python 3.7 or higher
- External MIDI-compatible software synthesizer
- MIDI keyboard (for input)

## Installation

1. Activate virtual environment:
```bash
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python pitch_trainer.py
```

## Usage

1. **MIDI Device Setup**:
   - Launch external software synthesizer (GarageBand, Logic Pro, FL Studio, etc.)
   - The app will automatically detect MIDI devices

2. **Start Training**:
   - The initial screen will be displayed when you run the app
   - Click the "Start Training" button to begin the game
   - A random note will be played, and you should play the same note on your MIDI keyboard

3. **Level System**:
   - 16 levels with progressive range expansion
   - Level up when accuracy reaches 80% or higher
   - Level up notifications with sound effects and display

4. **Statistics**:
   - Real-time display of accuracy and score
   - Visual piano keyboard shows correct/incorrect answers
   - Progress tracking with statistics graph

## File Structure

- `pitch_trainer.py`: Main application (PyQt5 GUI version)
- `audio/`: Sound effect files
  - `OK.mp3`: Correct answer sound
  - `NG.mp3`: Incorrect answer sound
  - `LevelUp.mp3`: Level up sound

## Notes

- Make sure external software synthesizer is running
- Ensure MIDI devices are properly connected
- Pitch detection is performed in semitone units
- Pitch range expands progressively by level (C3-B4)
- Settings are saved to `pitch_trainer_config.json`

## Sound Effects

The sound effects used in this app are obtained from [Sound Effect Lab](https://soundeffect-lab.info/sound/anime/).
- Correct answer: OK.mp3
- Incorrect answer: NG.mp3
- Level up: LevelUp.mp3

These sound effects are provided free of charge for commercial use without requiring credit or links.

## Troubleshooting

### PyQt5 errors
- Reinstall PyQt5 with `pip install PyQt5`
- On macOS, also try `brew install pyqt5`

### MIDI devices not detected
- Check that software synthesizer is running
- Verify MIDI device connections
- Check system MIDI settings
- Manually select MIDI devices from the app's settings menu

