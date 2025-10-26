# Pitch Training App (GUI Version)
# GUI implementation of simple version using PyQt5

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                             QComboBox, QTextEdit, QGroupBox, QListWidget, 
                             QDialog, QDialogButtonBox, QMessageBox, QMenuBar, 
                             QAction, QSpinBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint
from PyQt5.QtGui import QFont, QPainter, QPen, QBrush, QColor
import mido
import threading
import time
import json
import os
import subprocess

# Configure mido backend (avoid rtmidi errors)
# On macOS, default backend (rtmidi) is most stable
# Do not explicitly set backend

class StatsWidget(QWidget):
    """Statistics graph display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(40)  # Add space for scale marks
        self.setMaximumHeight(40)
        
        # Statistics data
        self.total_attempts = 0
        self.correct_attempts = 0
        self.recent_window = 30  # Maximum attempts for level-up determination
        
        # Color settings (same colors as keyboard highlights)
        self.correct_color = QColor(100, 150, 255)  # Blue (correct rate)
        self.incorrect_color = QColor(255, 100, 100)  # Red (incorrect rate)
        self.background_color = QColor(240, 240, 240)  # Background color
        self.border_color = QColor(0, 0, 0)
    
    def update_stats(self, total_attempts, correct_attempts):
        """Update statistics data"""
        self.total_attempts = total_attempts
        self.correct_attempts = correct_attempts
        self.update()
    
    def paintEvent(self, event):
        """Draw statistics graph"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Widget size
        width = self.width()
        height = self.height()
        
        # Graph height (excluding scale marks)
        graph_height = height - 15  # Reserve space for scale marks
        
        # Draw background (graph area only)
        painter.setBrush(QBrush(self.background_color))
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(0, 0, width, graph_height)
        
        if self.total_attempts == 0:
            # Draw scale marks
            self.draw_ticks(painter, width, graph_height)
            return
        
        # Calculate bar length
        # Use full width for 10 attempts, width doesn't increase beyond 10
        min_window = 10
        if self.total_attempts < min_window:
            bar_width = int(width * (self.total_attempts / min_window))
        else:
            bar_width = width
        
        # Calculate correct and incorrect rates (using past 30 attempts ratio)
        # Use actual attempt count and correct count
        correct_rate = self.correct_attempts / self.total_attempts
        incorrect_rate = 1.0 - correct_rate
        
        # Draw correct rate portion (blue)
        correct_width = int(bar_width * correct_rate)
        if correct_width > 0:
            painter.setBrush(QBrush(self.correct_color))
            painter.setPen(QPen(self.border_color, 1))
            painter.drawRect(0, 0, correct_width, graph_height)
        
        # Draw incorrect rate portion (red)
        incorrect_width = bar_width - correct_width
        if incorrect_width > 0:
            painter.setBrush(QBrush(self.incorrect_color))
            painter.setPen(QPen(self.border_color, 1))
            painter.drawRect(correct_width, 0, incorrect_width, graph_height)
        
        # Draw scale marks
        self.draw_ticks(painter, width, graph_height)
    
    def draw_ticks(self, painter, width, height):
        """Draw downward triangle and vertical line at 80% position"""
        # Calculate 80% position
        x = int(width * 0.8)
        
        # Triangle size (doubled)
        triangle_size = 16
        
        # Draw 80% vertical line in graph (dark gray)
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawLine(x, 0, x, height)
        
        # Triangle vertex coordinates (downward)
        points = [
            QPoint(x, height),  # Top vertex
            QPoint(x - triangle_size // 2, height + triangle_size),  # Bottom left
            QPoint(x + triangle_size // 2, height + triangle_size)   # Bottom right
        ]
        
        # Draw triangle in black
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawPolygon(points)

class PianoKeyboardWidget(QWidget):
    """Piano keyboard display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setMaximumHeight(120)
        
        # Note range to display (A3-D5)
        self.start_note = 45  # A3
        self.end_note = 74    # D5
        self.highlighted_note = None
        self.valid_notes = set()  # Set of valid notes
        
        # Keyboard colors
        self.white_key_color = QColor(255, 255, 255)
        self.black_key_color = QColor(0, 0, 0)
        self.correct_highlight_color = QColor(100, 150, 255)  # Blue (correct answer)
        self.incorrect_highlight_color = QColor(255, 100, 100)  # Red (incorrect answer)
        self.invalid_key_color = QColor(200, 200, 200)  # Gray (invalid notes)
        self.border_color = QColor(0, 0, 0)
    
    def set_highlighted_note(self, note_number, is_correct=True):
        """Set note to highlight"""
        self.highlighted_note = note_number
        self.is_correct = is_correct
        self.update()
    
    def clear_highlight(self):
        """Clear highlight"""
        self.highlighted_note = None
        self.update()
    
    def set_valid_notes(self, valid_notes):
        """Set valid notes"""
        self.valid_notes = set(valid_notes)
        self.update()
    
    def paintEvent(self, event):
        """Draw piano keyboard"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Widget size
        width = self.width()
        height = self.height()
        
        # Calculate white key width (C3-B4 range)
        white_keys = []
        for note in range(self.start_note, self.end_note + 1):
            if note % 12 in [0, 2, 4, 5, 7, 9, 11]:  # White keys
                white_keys.append(note)
        
        white_key_width = width / len(white_keys)
        
        # Draw white keys
        white_key_index = 0
        for note in range(self.start_note, self.end_note + 1):
            if note % 12 in [0, 2, 4, 5, 7, 9, 11]:  # White keys
                x = white_key_index * white_key_width
                
                # Determine highlight color
                if note == self.highlighted_note:
                    if hasattr(self, 'is_correct') and self.is_correct:
                        color = self.correct_highlight_color
                    else:
                        color = self.incorrect_highlight_color
                elif note not in self.valid_notes:
                    color = self.invalid_key_color  # Invalid notes are gray
                else:
                    color = self.white_key_color
                
                # Draw white keys
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(self.border_color, 1))
                painter.drawRect(int(x), 0, int(white_key_width), height)
                
                white_key_index += 1
        
        # Draw black keys
        white_key_index = 0
        for note in range(self.start_note, self.end_note + 1):
            if note % 12 in [0, 2, 4, 5, 7, 9, 11]:  # White keys
                x = white_key_index * white_key_width
                
                # Check if there's a black key after this white key
                next_note = note + 1
                if (next_note <= self.end_note and 
                    next_note % 12 in [1, 3, 6, 8, 10]):  # Black keys
                    
                    # Draw black key (adjust so black key center aligns with white key boundary)
                    black_width = white_key_width * 0.6
                    black_x = x + white_key_width - black_width / 2
                    black_height = height * 0.6
                    
                    # Determine highlight color
                    if next_note == self.highlighted_note:
                        if hasattr(self, 'is_correct') and self.is_correct:
                            color = self.correct_highlight_color
                        else:
                            color = self.incorrect_highlight_color
                    elif next_note not in self.valid_notes:
                        color = self.invalid_key_color  # Invalid notes are gray
                    else:
                        color = self.black_key_color
                    
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(self.border_color, 1))
                    painter.drawRect(int(black_x), 0, int(black_width), int(black_height))
                
                white_key_index += 1
        
        # Draw half of black key on left side of bottom white key
        if white_keys and white_keys[0] % 12 in [0, 2, 4, 5, 7, 9, 11]:  # First white key
            first_white_note = white_keys[0]
            # Look for black key before this white key
            prev_note = first_white_note - 1
            if prev_note % 12 in [1, 3, 6, 8, 10]:  # Black key
                black_width = white_key_width * 0.6
                black_x = -black_width / 2  # Extend to left side
                black_height = height * 0.6
                
                # Determine highlight color
                if prev_note == self.highlighted_note:
                    if hasattr(self, 'is_correct') and self.is_correct:
                        color = self.correct_highlight_color
                    else:
                        color = self.incorrect_highlight_color
                elif prev_note not in self.valid_notes:
                    color = self.invalid_key_color
                else:
                    color = self.black_key_color
                
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(self.border_color, 1))
                painter.drawRect(int(black_x), 0, int(black_width), int(black_height))
        
        # Draw half of black key on right side of top white key
        if white_keys and white_keys[-1] % 12 in [0, 2, 4, 5, 7, 9, 11]:  # Last white key
            last_white_note = white_keys[-1]
            # Look for black key after this white key
            next_note = last_white_note + 1
            if next_note % 12 in [1, 3, 6, 8, 10]:  # Black key
                black_width = white_key_width * 0.6
                black_x = width - black_width / 2  # Extend to right side
                black_height = height * 0.6
                
                # Determine highlight color
                if next_note == self.highlighted_note:
                    if hasattr(self, 'is_correct') and self.is_correct:
                        color = self.correct_highlight_color
                    else:
                        color = self.incorrect_highlight_color
                elif next_note not in self.valid_notes:
                    color = self.invalid_key_color
                else:
                    color = self.black_key_color
                
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(self.border_color, 1))
                painter.drawRect(int(black_x), 0, int(black_width), int(black_height))
    
    def get_note_name(self, note_number):
        """Get note name from MIDI note number"""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        note_index = note_number % 12
        octave = note_number // 12 - 1
        return f"{note_names[note_index]}{octave}"

class SettingsDialog(QDialog):
    """Settings dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(400, 300)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        
        # MIDI settings group
        midi_group = QGroupBox("MIDI Settings")
        midi_layout = QGridLayout(midi_group)
        
        # Input device
        midi_layout.addWidget(QLabel("Input Device:"), 0, 0)
        self.input_combo = QComboBox()
        self.input_combo.setEditable(False)
        midi_layout.addWidget(self.input_combo, 0, 1)
        
        # Output device
        midi_layout.addWidget(QLabel("Output Device:"), 1, 0)
        self.output_combo = QComboBox()
        self.output_combo.setEditable(False)
        midi_layout.addWidget(self.output_combo, 1, 1)
        
        # MIDI refresh button
        refresh_button = QPushButton("Refresh MIDI Devices")
        refresh_button.clicked.connect(self.refresh_midi_devices)
        midi_layout.addWidget(refresh_button, 2, 0, 1, 2)
        
        layout.addWidget(midi_group)
        
        # Game settings group
        game_group = QGroupBox("Game Settings")
        game_layout = QGridLayout(game_group)
        
        # Level settings
        game_layout.addWidget(QLabel("Starting Level:"), 0, 0)
        self.level_spinbox = QSpinBox()
        self.level_spinbox.setMinimum(1)
        self.level_spinbox.setMaximum(16)
        self.level_spinbox.setValue(1)
        game_layout.addWidget(self.level_spinbox, 0, 1)
        
        layout.addWidget(game_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_dialog)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def accept_dialog(self):
        """Process when OK button is pressed"""
        # Check if MIDI devices are selected
        input_name = self.input_combo.currentText()
        output_name = self.output_combo.currentText()
        
        if not input_name or not output_name:
            QMessageBox.warning(self, "Configuration Error", 
                              "Please select both input and output MIDI devices.")
            return
        
        self.save_settings()
        self.accept()
    
    def refresh_midi_devices(self):
        """Update MIDI devices"""
        if self.parent:
            # Call parent's refresh_midi_devices
            self.parent.refresh_midi_devices()
            # Update settings dialog combo boxes
            self.load_midi_devices()
    
    def load_midi_devices(self):
        """Load MIDI devices"""
        if not self.parent:
            return
            
        # Input device
        self.input_combo.clear()
        if hasattr(self.parent, 'input_devices_display'):
            self.input_combo.addItems(self.parent.input_devices_display)
        
        # Output device
        self.output_combo.clear()
        if hasattr(self.parent, 'output_devices_display'):
            self.output_combo.addItems(self.parent.output_devices_display)
        
        # Restore current selection
        if hasattr(self.parent, 'input_name') and self.parent.input_name:
            index = self.input_combo.findText(self.parent.input_name)
            if index >= 0:
                self.input_combo.setCurrentIndex(index)
        
        if hasattr(self.parent, 'output_name') and self.parent.output_name:
            index = self.output_combo.findText(self.parent.output_name)
            if index >= 0:
                self.output_combo.setCurrentIndex(index)
    
    def load_settings(self):
        """Load settings"""
        # Load MIDI devices
        self.load_midi_devices()
        
        # Load level settings
        if self.parent and hasattr(self.parent, 'current_level'):
            self.level_spinbox.setValue(self.parent.current_level)
    
    def save_settings(self):
        """Save settings"""
        if not self.parent:
            return
        
        # Detect level change
        old_level = self.parent.current_level if hasattr(self.parent, 'current_level') else 1
        new_level = self.level_spinbox.value()
        level_changed = (old_level != new_level)
        
        # Save MIDI device settings
        input_name = self.input_combo.currentText()
        output_name = self.output_combo.currentText()
        
        if input_name and output_name:
            self.parent.input_name = input_name
            self.parent.output_name = output_name
            self.parent.connect_midi_devices()
        
        # Save level settings
        if hasattr(self.parent, 'current_level'):
            self.parent.current_level = new_level
        
        # Save to config file
        self.parent.save_config()
        
        # If level is changed, reset game and return to initial screen
        if level_changed:
            self.parent.reset_game_to_initial_screen()

class PerfectPitchGUI(QMainWindow):
    # Signal definition
    midi_note_received = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pitch Trainer")
        self.setGeometry(100, 100, 600, 260)  # Adjust height to 260px
        self.setMinimumSize(600, 260)
        self.setMaximumSize(600, 260)
        
        # Game state
        self.game_active = False
        self.target_note = None
        self.start_time = None
        self.score = 0
        self.total_attempts = 0
        self.response_times = []
        
        # MIDI setup
        self.input_port = None
        self.output_port = None
        self.input_name = None
        self.output_name = None
        
        # Level system
        self.current_level = 1
        self.max_level = 16
        self.level_threshold = 0.8
        self.level_stats = {}
        self.recent_results = []
        self.recent_window = 30
        
        # Config file
        self.config_file = "pitch_trainer_config.json"
        
        # Note name and MIDI note number mapping
        self.note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.octave_range = (3, 4)  # C3-B4
        
        # Initialize
        self.initialize_levels()
        self.load_config()
        self.setup_ui()
        self.setup_midi()
        
        # Connect signals and slots
        self.midi_note_received.connect(self.check_note)
        
        # Show settings dialog if MIDI devices are not configured
        self.check_midi_setup()
    
    def fix_encoding_for_display(self, device_name):
        """Fix garbled characters for display"""
        # Replace garbled character patterns
        replacements = {
            '„Éâ„É©„Ç§„Éê': 'Driver',
            '„Éê„Çπ': 'Port',
            '„ÅÆ‰ªÆÊÉ≥Âá∫Âäõ': ' Input Port',
            '„ÅÆ‰ªÆÊÉ≥ÂÖ•Âäõ': ' Output Port'
        }
        
        fixed = device_name
        for old, new in replacements.items():
            fixed = fixed.replace(old, new)
        
        return fixed
    
    def initialize_levels(self):
        """Initialize level system"""
        # Level 1: C3-E3 (white keys only)
        self.level_stats[1] = {
            'name': 'Level 1: C3-E3 (white keys only)',
            'notes': [48, 50, 52],  # C3, D3, E3
            'attempts': 0,
            'correct': 0
        }
        
        # Level 2: C3-F3 (white keys only)
        self.level_stats[2] = {
            'name': 'Level 2: C3-F3 (white keys only)',
            'notes': [48, 50, 52, 53],  # C3, D3, E3, F3
            'attempts': 0,
            'correct': 0
        }
        
        # Level 3: C3-G3 (white keys only)
        self.level_stats[3] = {
            'name': 'Level 3: C3-G3 (white keys only)',
            'notes': [48, 50, 52, 53, 55],  # C3, D3, E3, F3, G3
            'attempts': 0,
            'correct': 0
        }
        
        # Level 4: C3-A3 (white keys only)
        self.level_stats[4] = {
            'name': 'Level 4: C3-A3 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57],  # C3, D3, E3, F3, G3, A3
            'attempts': 0,
            'correct': 0
        }
        
        # Level 5: C3-B3 (white keys only)
        self.level_stats[5] = {
            'name': 'Level 5: C3-B3 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57, 59],  # C3, D3, E3, F3, G3, A3, B3
            'attempts': 0,
            'correct': 0
        }
        
        # Level 6: C3-C4 (white keys only)
        self.level_stats[6] = {
            'name': 'Level 6: C3-C4 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57, 59, 60],  # C3, D3, E3, F3, G3, A3, B3, C4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 7: C3-D4 (white keys only)
        self.level_stats[7] = {
            'name': 'Level 7: C3-D4 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57, 59, 60, 62],  # C3, D3, E3, F3, G3, A3, B3, C4, D4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 8: C3-E4 (white keys only)
        self.level_stats[8] = {
            'name': 'Level 8: C3-E4 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57, 59, 60, 62, 64],  # C3, D3, E3, F3, G3, A3, B3, C4, D4, E4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 9: C3-F4 (white keys only)
        self.level_stats[9] = {
            'name': 'Level 9: C3-F4 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65],  # C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 10: C3-G4 (white keys only)
        self.level_stats[10] = {
            'name': 'Level 10: C3-G4 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67],  # C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 11: C3-A4 (white keys only)
        self.level_stats[11] = {
            'name': 'Level 11: C3-A4 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69],  # C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 12: C3-B4 (white keys only)
        self.level_stats[12] = {
            'name': 'Level 12: C3-B4 (white keys only)',
            'notes': [48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71],  # C3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 13: C3-B4 + C#3 (1 black key)
        self.level_stats[13] = {
            'name': 'Level 13: C3-B4 + C#3',
            'notes': [48, 49, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71],  # C3, C#3, D3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 14: C3-B4 + C#3, D#3 (2 black keys)
        self.level_stats[14] = {
            'name': 'Level 14: C3-B4 + C#3, D#3',
            'notes': [48, 49, 50, 51, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71],  # C3, C#3, D3, D#3, E3, F3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 15: C3-B4 + C#3, D#3, F#3 (3 black keys)
        self.level_stats[15] = {
            'name': 'Level 15: C3-B4 + C#3, D#3, F#3',
            'notes': [48, 49, 50, 51, 52, 53, 54, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71],  # C3, C#3, D3, D#3, E3, F3, F#3, G3, A3, B3, C4, D4, E4, F4, G4, A4, B4
            'attempts': 0,
            'correct': 0
        }
        
        # Level 16: C3-B4 (all notes)
        self.level_stats[16] = {
            'name': 'Level 16: C3-B4 (all notes)',
            'notes': list(range(48, 84)),  # C3-B4 all notes
            'attempts': 0,
            'correct': 0
        }
    
    def get_level_notes(self, level):
        """Get valid note range for specified level"""
        if level in self.level_stats:
            return self.level_stats[level]['notes']
        else:
            # Default to level 1 note range
            return [48, 50, 52]  # C3, D3, E3
    
    def setup_menu_bar(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)  # Disable native menu bar to force display
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Settings menu
        settings_action = QAction('Settings', self)
        settings_action.triggered.connect(self.show_settings_dialog)
        file_menu.addAction(settings_action)
        
        # Exit menu
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def check_midi_setup(self):
        """Check MIDI device configuration and show settings dialog if necessary"""
        # If MIDI devices are not configured
        if not self.input_name or not self.output_name:
            QMessageBox.information(self, "MIDI Setup Required", 
                                  "MIDI devices are not configured.\n"
                                  "Please set up your MIDI input and output devices.")
            self.show_settings_dialog()
    
    def show_settings_dialog(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        result = dialog.exec_()
        
        # If dialog is closed with OK, check if MIDI devices are properly configured
        if result == QDialog.Accepted:
            if not self.input_name or not self.output_name:
                QMessageBox.warning(self, "Configuration Incomplete", 
                                  "MIDI devices are still not properly configured.\n"
                                  "Please restart the application and configure MIDI devices.")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", 
                         "Pitch Trainer\n\n"
                         "A pitch training application using MIDI.\n"
                         "Practice with a level system that gradually expands your range.")
    
    def setup_ui(self):
        """Setup UI"""
        # Setup menu bar
        self.setup_menu_bar()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(0)
        
        # Game group
        game_group = QGroupBox()
        game_layout = QVBoxLayout(game_group)
        game_layout.setContentsMargins(5, 5, 5, 5)
        game_layout.setSpacing(10)  # Add spacing
        
        # Level display
        self.level_label = QLabel()
        level_font = QFont()
        level_font.setPointSize(18)
        level_font.setBold(True)
        self.level_label.setFont(level_font)
        self.level_label.setAlignment(Qt.AlignCenter)
        game_layout.addWidget(self.level_label)
        
        # Problem display (hidden)
        self.question_label = QLabel()
        self.question_label.setVisible(False)
        game_layout.addWidget(self.question_label)
        
        # Result display (hidden)
        self.result_label = QLabel()
        self.result_label.setVisible(False)
        game_layout.addWidget(self.result_label)
        
        # Keyboard display (hidden in initial state)
        self.piano_keyboard = PianoKeyboardWidget()
        self.piano_keyboard.setVisible(False)
        game_layout.addWidget(self.piano_keyboard)
        
        # Level-up display (hidden)
        self.levelup_label = QLabel("Level Up!")
        levelup_font = QFont()
        levelup_font.setPointSize(24)
        levelup_font.setBold(True)
        self.levelup_label.setFont(levelup_font)
        self.levelup_label.setAlignment(Qt.AlignCenter)
        self.levelup_label.setStyleSheet("color: #FF6B35; background-color: #FFF8DC; border: 2px solid #FF6B35; border-radius: 10px; padding: 20px;")
        self.levelup_label.setVisible(False)
        game_layout.addWidget(self.levelup_label)
        
        # Statistics graph display (hidden in initial state)
        self.stats_widget = StatsWidget()
        self.stats_widget.setVisible(False)
        game_layout.addWidget(self.stats_widget)
        
        # Large Start Training button (displayed in initial state)
        self.start_button = QPushButton("Start Training")
        start_font = QFont()
        start_font.setPointSize(24)
        start_font.setBold(True)
        self.start_button.setFont(start_font)
        self.start_button.setMinimumHeight(100)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 3px solid #45a049;
                border-radius: 15px;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.start_button.clicked.connect(self.start_game)
        game_layout.addWidget(self.start_button)
        main_layout.addWidget(game_group)
        
        
        # Initial display
        self.update_display()
    
    def setup_midi(self):
        """MIDI setup"""
        try:
            # Always call refresh_midi_devices to select device names loaded from config file
            self.refresh_midi_devices()
        except Exception as e:
            QMessageBox.critical(self, "MIDI Setup Error", f"Error occurred during MIDI setup: {e}")
    
    def refresh_midi_devices(self):
        """Update MIDI device list"""
        try:
            # Close existing connections
            if self.input_port:
                self.input_port.close()
            if self.output_port:
                self.output_port.close()
            
            # Get device list (keep original garbled names)
            self.input_devices_raw = mido.get_input_names()
            self.output_devices_raw = mido.get_output_names()
            
            self.input_devices_display = [self.fix_encoding_for_display(name) for name in self.input_devices_raw]
            self.output_devices_display = [self.fix_encoding_for_display(name) for name in self.output_devices_raw]
            
            print(f"Raw input devices: {self.input_devices_raw}")
            print(f"Display input devices: {self.input_devices_display}")
            print(f"Raw output devices: {self.output_devices_raw}")
            print(f"Display output devices: {self.output_devices_display}")
            
            # Update combo boxes (for display) - only if they exist
            if hasattr(self, 'input_combo'):
                self.input_combo.clear()
                self.input_combo.addItems(self.input_devices_display)
            
            if hasattr(self, 'output_combo'):
                self.output_combo.clear()
                self.output_combo.addItems(self.output_devices_display)
            
            # Default selection
            if self.input_devices_display:
                print(f"Config file input device name: '{self.input_name}' (length: {len(self.input_name) if self.input_name else 0})")
                print(f"Available input devices: {self.input_devices_display}")
                for i, device in enumerate(self.input_devices_display):
                    print(f"  Device {i}: '{device}' (length: {len(device)})")
                    if self.input_name and device == self.input_name:
                        print(f"    Exact match found!")
                    elif self.input_name and self.input_name in device:
                        print(f"    Partial match found!")
                
                if self.input_name and self.input_name in self.input_devices_display:
                    index = self.input_devices_display.index(self.input_name)
                    print(f"Selecting input device '{self.input_name}' at index {index}")
                    if hasattr(self, 'input_combo'):
                        self.input_combo.setCurrentIndex(index)
                else:
                    print(f"Input device '{self.input_name}' not found, selecting first device")
                    if hasattr(self, 'input_combo'):
                        self.input_combo.setCurrentIndex(0)
                    
            if self.output_devices_display:
                print(f"Config file output device name: '{self.output_name}' (length: {len(self.output_name) if self.output_name else 0})")
                print(f"Available output devices: {self.output_devices_display}")
                for i, device in enumerate(self.output_devices_display):
                    print(f"  Device {i}: '{device}' (length: {len(device)})")
                    if self.output_name and device == self.output_name:
                        print(f"    Exact match found!")
                    elif self.output_name and self.output_name in device:
                        print(f"    Partial match found!")
                
                if self.output_name and self.output_name in self.output_devices_display:
                    index = self.output_devices_display.index(self.output_name)
                    print(f"Selecting output device '{self.output_name}' at index {index}")
                    if hasattr(self, 'output_combo'):
                        self.output_combo.setCurrentIndex(index)
                else:
                    print(f"Output device '{self.output_name}' not found, selecting first device")
                    if hasattr(self, 'output_combo'):
                        self.output_combo.setCurrentIndex(0)
            
            # Connect to devices (after ensuring combo box selection is set)
            # Temporarily disable combo box change events (only if connected)
            if hasattr(self, 'input_combo'):
                try:
                    self.input_combo.currentTextChanged.disconnect()
                except TypeError:
                    pass  # Ignore if not yet connected
            
            if hasattr(self, 'output_combo'):
                try:
                    self.output_combo.currentTextChanged.disconnect()
                except TypeError:
                    pass  # Ignore if not yet connected
            
            if hasattr(self, 'input_combo') and self.input_devices_display and self.input_name and self.input_name in self.input_devices_display:
                index = self.input_devices_display.index(self.input_name)
                self.input_combo.setCurrentIndex(index)
                print(f"Final confirmation: Setting input device at index {index}")
                
            if hasattr(self, 'output_combo') and self.output_devices_display and self.output_name and self.output_name in self.output_devices_display:
                index = self.output_devices_display.index(self.output_name)
                self.output_combo.setCurrentIndex(index)
                print(f"Final confirmation: Setting output device at index {index}")
            
            # Force update combo box selection
            if hasattr(self, 'input_combo'):
                self.input_combo.update()
            if hasattr(self, 'output_combo'):
                self.output_combo.update()
            
            # Reconnect change events
            if hasattr(self, 'input_combo'):
                self.input_combo.currentTextChanged.connect(self.on_input_device_changed)
            if hasattr(self, 'output_combo'):
                self.output_combo.currentTextChanged.connect(self.on_output_device_changed)
            
            self.connect_midi_devices()
            
        except Exception as e:
            QMessageBox.critical(self, "MIDI Device Update Error", f"Error occurred during MIDI device update: {e}")
    
    def on_input_device_changed(self, device_name):
        """Process when input device is changed"""
        print(f"Input device changed: {device_name}")
        if device_name and hasattr(self, 'output_combo') and self.output_combo.currentText():
            self.connect_midi_devices()
    
    def on_output_device_changed(self, device_name):
        """Process when output device is changed"""
        print(f"Output device changed: {device_name}")
        if device_name and hasattr(self, 'input_combo') and self.input_combo.currentText():
            self.connect_midi_devices()
    
    def connect_midi_devices(self):
        """Connect to selected MIDI devices"""
        try:
            # Get only if combo box exists
            if hasattr(self, 'input_combo'):
                input_display_name = self.input_combo.currentText()
            else:
                input_display_name = self.input_name
            
            if hasattr(self, 'output_combo'):
                output_display_name = self.output_combo.currentText()
            else:
                output_display_name = self.output_name
            
            print(f"Connection attempt: input={input_display_name}, output={output_display_name}")
            
            if not input_display_name or not output_display_name:
                print("Device name is empty")
                return
            
            # Get original name from display name
            def get_raw_name_from_display(display_name, raw_list):
                # Create mapping between display name and original name
                for raw_name in raw_list:
                    # Compare with name converted for display
                    display_converted = self.fix_encoding_for_display(raw_name)
                    if display_converted == display_name:
                        print(f"Mapping found: '{display_name}' -> '{raw_name}'")
                        return raw_name
                
                # If not found, use as is (English names, etc.)
                print(f"Mapping not found: using '{display_name}' as is")
                return display_name
            
            # Connect to input device
            input_name_raw = get_raw_name_from_display(input_display_name, self.input_devices_raw)
            self.input_port = mido.open_input(input_name_raw, callback=self.on_midi_input)
            self.input_name = input_display_name
            print(f"Input device connection successful: {input_display_name} (raw: {input_name_raw})")
            
            # Connect to output device
            output_name_raw = get_raw_name_from_display(output_display_name, self.output_devices_raw)
            self.output_port = mido.open_output(output_name_raw)
            self.output_name = output_display_name
            print(f"Output device connection successful: {output_display_name} (raw: {output_name_raw})")
            
            # Save settings
            self.save_config()
            
            print(f"MIDI device connection completed: input={input_display_name}, output={output_display_name}")
            
        except Exception as e:
            print(f"MIDI connection error: {e}")
            QMessageBox.critical(self, "MIDI Connection Error", f"Error occurred during MIDI device connection: {e}")
    
    def on_midi_input(self, message):
        """Process MIDI input"""
        print(f"MIDI received: {message}")  # Debug
        
        if not self.game_active:
            print("Game is not active")
            return
            
        if message.type != 'note_on':
            print(f"Non-note_on message: {message.type}")
            return
            
        if message.velocity == 0:
            print("Ignoring due to velocity=0")
            return
        
        # Prevent duplicate reception (filter consecutive reception of same note)
        current_time = time.time()
        last_input_time = getattr(self, 'last_input_time', 0)
        last_input_note = getattr(self, 'last_input_note', None)
        
        # Ignore if same note is received within 0.1 seconds
        if (last_input_note == message.note and 
            current_time - last_input_time < 0.1):
            print(f"Ignoring duplicate reception: note={message.note}")
            return
        
        # Record input information
        self.last_input_time = current_time
        self.last_input_note = message.note
        
        print(f"Valid note_on received: note={message.note}, velocity={message.velocity}")
        
        # Notify main thread via signal
        print(f"About to call check_note via signal: note={message.note}")
        self.midi_note_received.emit(message.note)
    
    def start_game(self):
        """Start game"""
        print(f"Game start attempt: input_port={self.input_port}, output_port={self.output_port}")
        
        if not self.input_port or not self.output_port:
            QMessageBox.critical(self, "Error", "MIDI devices are not configured")
            return
        
        self.game_active = True
        self.score = 0
        self.total_attempts = 0
        self.response_times = []
        self.recent_results = []
        
        print("Game started: Now in active state")
        
        # Hide Start Training button and show keyboard and graph
        self.start_button.setVisible(False)
        self.piano_keyboard.setVisible(True)
        self.stats_widget.setVisible(True)
        
        self.update_display()
        self.generate_new_note()
    
    def reset_game_to_initial_screen(self):
        """Reset game and return to initial screen"""
        print("Resetting game and returning to initial screen")
        
        # Stop game
        self.game_active = False
        self.stop_current_note()
        
        # Reset game state
        self.score = 0
        self.total_attempts = 0
        self.response_times = []
        self.recent_results = []
        self.target_note = None
        self.start_time = None
        self.judging = False
        
        # Clear keyboard highlights
        if hasattr(self, 'piano_keyboard'):
            self.piano_keyboard.clear_highlight()
        
        # Hide level-up display
        if hasattr(self, 'levelup_label'):
            self.levelup_label.setVisible(False)
        
        # Return to initial screen (show Start Training button, hide keyboard and graph)
        if hasattr(self, 'start_button'):
            self.start_button.setVisible(True)
        if hasattr(self, 'piano_keyboard'):
            self.piano_keyboard.setVisible(False)
        if hasattr(self, 'stats_widget'):
            self.stats_widget.setVisible(False)
        
        # Update display
        self.update_display()
    
    
    def generate_new_note(self):
        """Generate new note"""
        if not self.game_active:
            return
        
        # Stop current note
        self.stop_current_note()
        
        # Select note according to level
        available_notes = self.level_stats[self.current_level]['notes']
        
        # Avoid consecutive same notes
        if len(available_notes) > 1:
            if self.current_level <= 3:
                # Initial levels: avoid last 2 notes
                recent_notes = getattr(self, 'recent_notes', [])
                available_notes = [n for n in available_notes if n not in recent_notes[-2:]]
            else:
                # Advanced levels: avoid last 1 note
                last_note = getattr(self, 'last_note', None)
                if last_note in available_notes:
                    available_notes = [n for n in available_notes if n != last_note]
        
        if not available_notes:
            available_notes = self.level_stats[self.current_level]['notes']
        
        # Select note
        import random
        self.target_note = random.choice(available_notes)
        self.last_note = self.target_note
        print(f"New note generated: target_note={self.target_note} ({self.get_note_name(self.target_note)})")
        
        # Record recent notes
        if not hasattr(self, 'recent_notes'):
            self.recent_notes = []
        self.recent_notes.append(self.target_note)
        if len(self.recent_notes) > 5:
            self.recent_notes.pop(0)
        
        # Play sound
        if self.output_port:
            self.output_port.send(mido.Message('note_on', note=self.target_note, velocity=100))
            print(f"Note-on sent: {self.target_note} ({self.get_note_name(self.target_note)})")
            
            # Auto note-off after 0.5 seconds
            QTimer.singleShot(500, self.auto_note_off)
        
        # Record start time
        self.start_time = time.time()
        
        # Update display
        self.question_label.setText("")
        self.result_label.setText("")
        
        # Clear keyboard highlights
        self.piano_keyboard.clear_highlight()
        
        self.update_display()
    
    def check_note(self, played_note):
        """Pitch judgment"""
        print(f"check_note called: played_note={played_note}, game_active={self.game_active}, target_note={self.target_note}")
        
        # Prevent duplicate judgment
        if getattr(self, 'judging', False):
            print("Already judging")
            return
        
        # Game state check
        if not self.game_active:
            print("Game is not active")
            return
            
        if not self.target_note:
            print("target_note is not set")
            return
        
        # Get valid note range for current level
        current_level_notes = self.get_level_notes(self.current_level)
        
        # Ignore MIDI notes outside valid range
        if played_note not in current_level_notes:
            print(f"Invalid range MIDI note: {played_note} (current level: {self.current_level})")
            return
        
        self.judging = True
        
        try:
            
            self.total_attempts += 1
            response_time = time.time() - self.start_time if self.start_time else 0
            
            # Update level statistics
            current_stats = self.level_stats[self.current_level]
            current_stats['attempts'] += 1
            
            # Pitch judgment
            note_diff = abs(played_note - self.target_note)
            
            if note_diff == 0:
                # Perfect match
                self.score += 1
                self.response_times.append(response_time)
                current_stats['correct'] += 1
                
                # Record correct answer in recent results
                self.recent_results.append(True)
                
                # Correct answer display (text display removed)
                
                # Highlight on keyboard (blue for correct answer)
                self.piano_keyboard.set_highlighted_note(self.target_note, is_correct=True)
                
                # Play correct answer sound effect
                self.play_sound("OK.mp3")
                
                # Level-up check
                level_up_occurred = self.check_level_up()
                
                # Transition to next note
                if level_up_occurred:
                    QTimer.singleShot(3000, self.generate_new_note)
                else:
                    QTimer.singleShot(2000, self.generate_new_note)
            else:
                # Incorrect answer (text display removed)
                
                # Highlight on keyboard (red for incorrect answer)
                self.piano_keyboard.set_highlighted_note(played_note, is_correct=False)
                
                # Record incorrect answer in recent results
                self.recent_results.append(False)
                
                # Play incorrect answer sound effect
                self.play_sound("NG.mp3")
                
                # Replay the same problem note
                QTimer.singleShot(1000, self.replay_current_note)
            
            self.update_display()
        
        finally:
            # Reset judgment flag
            self.judging = False
    
    def stop_current_note(self):
        """Stop current note"""
        if self.target_note and self.output_port:
            try:
                # Send note-off (send even with velocity=0)
                self.output_port.send(mido.Message('note_off', note=self.target_note, velocity=0))
                print(f"Note-off sent: {self.target_note} ({self.get_note_name(self.target_note)})")
            except Exception as e:
                print(f"Note-off send error: {e}")
    
    def auto_note_off(self):
        """Auto note-off (called after 0.5 seconds)"""
        if self.target_note and self.output_port:
            try:
                # Send note-off
                self.output_port.send(mido.Message('note_off', note=self.target_note, velocity=0))
                print(f"Auto note-off sent: {self.target_note} ({self.get_note_name(self.target_note)})")
            except Exception as e:
                print(f"Auto note-off send error: {e}")
    
    def replay_current_note(self):
        """Replay current note"""
        if not self.game_active or not self.target_note:
            return
        
        # Stop current note
        self.stop_current_note()
        
        # Replay sound
        if self.output_port:
            self.output_port.send(mido.Message('note_on', note=self.target_note, velocity=100))
            print(f"Note-on sent: {self.target_note} ({self.get_note_name(self.target_note)})")
            
            # Auto note-off after 0.5 seconds
            QTimer.singleShot(500, self.auto_note_off)
        
        # Record start time
        self.start_time = time.time()
        
        # Update display
        self.question_label.setText("")
        self.result_label.setText("")
        
        # Clear keyboard highlights
        self.piano_keyboard.clear_highlight()
        
        self.update_display()
    
    def get_note_name(self, note_number):
        """Convert MIDI note number to note name"""
        octave = (note_number // 12) - 1
        note_name = self.note_names[note_number % 12]
        return f"{note_name}{octave}"
    
    
    
    def check_level_up(self):
        """Check for level up"""
        # Level up if accuracy is high after 10 or more attempts
        min_attempts = 10
        max_window = 30
        
        if len(self.recent_results) >= min_attempts:
            # Use results from past maximum 30 attempts
            window_size = min(len(self.recent_results), max_window)
            recent_window_results = self.recent_results[-window_size:]
            recent_correct = sum(recent_window_results)
            recent_accuracy = recent_correct / len(recent_window_results)
            
            if recent_accuracy >= self.level_threshold and self.current_level < self.max_level:
                # Save statistics before level-up (for graph display)
                self.levelup_stats = {
                    'total_attempts': self.total_attempts,
                    'correct_attempts': self.score,
                    'accuracy': recent_accuracy
                }
                
                self.current_level += 1
                
                # Level-up display
                self.show_levelup_display()
                
                # Play level-up sound effect
                QTimer.singleShot(500, lambda: self.play_sound("LevelUp.mp3"))
                
                # Save settings
                self.save_config()
                return True
        return False
    
    def show_levelup_display(self):
        """Show level-up display"""
        # Hide keyboard
        self.piano_keyboard.setVisible(False)
        
        # Show level-up display
        self.levelup_label.setVisible(True)
        
        # Update graph with statistics before level-up
        if hasattr(self, 'levelup_stats'):
            self.stats_widget.update_stats(
                self.levelup_stats['total_attempts'], 
                self.levelup_stats['correct_attempts']
            )
        
        # Return to normal after 2 seconds
        QTimer.singleShot(2000, self.hide_levelup_display)
    
    def hide_levelup_display(self):
        """Hide level-up display"""
        # Hide level-up display
        self.levelup_label.setVisible(False)
        
        # Show keyboard
        self.piano_keyboard.setVisible(True)
        
        # Clear keyboard highlights
        self.piano_keyboard.clear_highlight()
        
        # Clear level-up statistics
        if hasattr(self, 'levelup_stats'):
            delattr(self, 'levelup_stats')
        
        # Reset statistics (after level-up display ends)
        self.recent_results = []
        self.total_attempts = 0
        self.score = 0
        
        # Update display
        self.update_display()
    
    def play_sound(self, sound_file):
        """Play sound effect"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sound_path = os.path.join(script_dir, "audio", sound_file)
            if os.path.exists(sound_path):
                subprocess.Popen(['afplay', sound_path])
        except Exception as e:
            print(f"Sound effect playback error: {e}")
    
    def load_config(self):
        """Load settings"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Device names loaded from config file are used for display
                    self.input_name = config.get('input_device')
                    self.output_name = config.get('output_device')
                    self.current_level = config.get('current_level', 1)
                    print(f"Settings loaded: input={self.input_name}, output={self.output_name}, level={self.current_level}")
            else:
                print("Config file does not exist")
        except Exception as e:
            print(f"Settings load error: {e}")
    
    def save_config(self):
        """Save settings"""
        try:
            config = {
                'input_device': self.input_name,
                'output_device': self.output_name,
                'current_level': self.current_level
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Settings save error: {e}")
    
    def update_display(self):
        """Update display"""
        self.level_label.setText(f"Level {self.current_level}")
        
        # Update statistics graph
        if hasattr(self, 'stats_widget'):
            self.stats_widget.update_stats(self.total_attempts, self.score)
        
        # Update valid notes for keyboard
        if hasattr(self, 'piano_keyboard'):
            current_level_notes = self.level_stats[self.current_level]['notes']
            self.piano_keyboard.set_valid_notes(current_level_notes)
    
    def closeEvent(self, event):
        """Application termination processing"""
        print("Application terminating...")
        self.cleanup()
        event.accept()
        QApplication.quit()
    
    def cleanup(self):
        """Resource cleanup"""
        # Stop current note
        self.stop_current_note()
        
        self.save_config()
        
        if self.input_port:
            self.input_port.close()
        if self.output_port:
            self.output_port.close()

def main():
    app = QApplication(sys.argv)
    window = PerfectPitchGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()