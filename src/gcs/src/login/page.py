import sys
import yaml
import os
import requests
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QDialog, QFormLayout, QScrollArea,
                               QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtGui import QColor, QPalette, QImage
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QPixmap, QFont, QIcon
from qfluentwidgets import (
    MessageBox,
    setTheme,
    setThemeColor,
    Theme,
)

# Default config structure
DEFAULT_CONFIG = {
  "app": {
    "description": "A control center for Matek drones",
    "name": "Matek Control Center",
    "version": "1.0.0",
    "author": "Amar Jay",
    "user": "nebula",
    "password": "nebula123"
  },
  "camera": {
    "distortion": [0.1, -0.05, 0.01, 0.01],
    "intrinsics": [205.46962738, 0.0, 320.0, 0.0, 205.46965599, 240.0, 0.0, 0.0, 1.0]
  },
  "communication": {
    "mavlink_address": "tcp://localhost:16550",
    "zmq_control_address": "tcp://localhost:5556",
    "zmq_timeout": 1000,
    "zmq_video_address": "tcp://localhost:5555"
  },
  "logging": {
    "level": "DEBUG"
  },
  "ml": {
    "confidence_threshold": 0.6,
    "production_model_path": "src/controls/detection/main.pt",
    "simulation_model_path": "src/controls/detection/sim.pt",
    "workers": 2
  },
  "simulation": True
}


class MessageType:
    ERROR = "Error"
    WARNING = "Warning"
    INFO = "Info"

def show_message(self, type:MessageType, message:str):
    """Show an error message dialog."""
    msg = MessageBox(
        title=type,
        content=message,
        parent=self
    )

    style_sheet = msg.yesButton.styleSheet()
    if type == MessageType.ERROR:
      style_sheet += "\nPrimaryPushButton {background-color: #B22222; color: white; border: 1px solid red;}\nPrimaryPushButton::hover {background-color: #B22222; color: white; border: 1px solid red;}"
    elif type == MessageType.WARNING:
      style_sheet += "\nPrimaryPushButton {background-color: #FFA500; color: white; border: 1px solid orange;}\nPrimaryPushButton::hover {background-color: #FFA500; color: white; border: 1px solid orange;}"
    elif type == MessageType.INFO:
      style_sheet += "\nPrimaryPushButton {background-color: #0078D4; color: white; border: 1px solid blue;}\nPrimaryPushButton::hover {background-color: #0078D4; color: white; border: 1px solid blue;}"
    msg.yesButton.setStyleSheet(style_sheet)
    return msg.exec()

class ImageLoader(QThread):
    imageLoaded = Signal(QPixmap)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    self.imageLoaded.emit(pixmap)
        except:
            pass

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.setModal(True)
        self.resize(600, 500)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
                padding: 4px 0;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#cancelBtn {
                background-color: #484848;
            }
            QPushButton#cancelBtn:hover {
                background-color: #5a5a5a;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #484848;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
        """)
        
        self.config_data = {}
        self.form_fields = {}
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 12, 12, 24)
        layout.setSpacing(16)
        
        # Title
        #title = QLabel("Configuration")
        #title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        #title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        #layout.addWidget(title)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        form_widget = QWidget()
        form_widget.setStyleSheet("background-color: #1e1e1e;")
        self.form_layout = QVBoxLayout(form_widget)
        self.form_layout.setSpacing(12)
        
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        save_btn = QPushButton("Save")
        
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.save_config)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as file:
                    self.config_data = yaml.safe_load(file) or {}
            else:
                with open(config_path, 'w', encoding='utf-8') as file:
                    yaml.dump(DEFAULT_CONFIG, file, default_flow_style=False, indent=2)

                self.config_data = DEFAULT_CONFIG.copy()
        except Exception as e:

            show_message(self, MessageType.WARNING, f"Could not load config: {str(e)}\nUsing default configuration.")
            self.config_data = DEFAULT_CONFIG.copy()
        
        self.populate_form()
    
    def populate_form(self):
        self.form_fields.clear()
        
        # Clear existing form
        for i in reversed(range(self.form_layout.count())):
            self.form_layout.itemAt(i).widget().setParent(None)
        
        self._create_form_fields("", self.config_data)
    
    def _create_form_fields(self, prefix, data):
        for key, value in data.items():
            field_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Section header
                if prefix:  # Don't add spacing before first section
                    spacer = QSpacerItem(0, 16, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
                    self.form_layout.addItem(spacer)
                
                header = QLabel(key.upper().replace('_', ' '))
                header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
                header.setStyleSheet("color: #0078d4; padding: 8px 0 4px 0;")
                self.form_layout.addWidget(header)
                
                self._create_form_fields(field_key, value)
            else:
                # Create input field
                label = QLabel(key.replace('_', ' ').title())
                field = QLineEdit(str(value))
                field.setPlaceholderText(f"Enter {key.replace('_', ' ')}")
                
                self.form_fields[field_key] = field
                self.form_layout.addWidget(label)
                self.form_layout.addWidget(field)
    
    def save_config(self):
        try:
            updated_config = self._update_nested_dict(self.config_data.copy())
            
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "config", "config.yaml")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as file:
                yaml.dump(updated_config, file, default_flow_style=False, indent=2)

            show_message(self, MessageType.INFO, "Configuration saved successfully!")
            self.accept()
            
        except Exception as e:
            show_message(self, MessageType.ERROR, f"Failed to save configuration:\n{str(e)}")

    def _update_nested_dict(self, data):
        for field_key, field in self.form_fields.items():
            current = data
            keys = field_key.split('.')
            
            for key in keys[:-1]:
                current = current[key]
            
            value = field.text()
            original_value = current[keys[-1]]
            
            if isinstance(original_value, bool):
                current[keys[-1]] = value.lower() in ('true', 'yes', '1', 'on')
            elif isinstance(original_value, int):
                try:
                    current[keys[-1]] = int(value)
                except ValueError:
                    current[keys[-1]] = value
            elif isinstance(original_value, float):
                try:
                    current[keys[-1]] = float(value)
                except ValueError:
                    current[keys[-1]] = value
            else:
                current[keys[-1]] = value
        
        return data


class LoginWindow(QMainWindow):
    def __init__(self, accept = None):
        super().__init__()
        self.setWindowTitle("Login")
        self.setFixedSize(1000, 600)
        self.center_window()
        
        # Dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
        """)
        if accept is not None:
            self.accept = accept
        else:
            self.accept = lambda: show_message(self, MessageType.INFO, "Login successful!")
        self.dialog = ConfigDialog(self)
        
        self.setup_ui()
    
    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        window = self.frameGeometry()
        window.moveCenter(screen.center())
        self.move(window.topLeft())
    
    def setup_ui(self):

        setTheme(Theme.DARK)
        setThemeColor("#0078d4", save=True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left side - Login form
        self.create_image_section(main_layout)
        
        # Right side - Image
        self.create_login_form(main_layout)
    
    def create_login_form(self, main_layout):
        left_widget = QWidget()
        left_widget.setFixedWidth(450)
        left_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
        
        layout = QVBoxLayout(left_widget)
        layout.setContentsMargins(48, 0, 48, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Logo/Title
        title = QLabel(self.dialog.config_data.get("app", {}).get("name", "Nebula"))
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Light))
        title.setStyleSheet("color: #ffffff; margin-bottom: 8px;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)
        
        subtitle = QLabel(self.dialog.config_data.get("app", {}).get("description", "A control center for Matek drones"))
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet("color: #a0a0a0; margin-bottom: 40px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(subtitle)
        
        # Form fields
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        
        # Username
        self.username_field = QLineEdit()
        self.username_field.setPlaceholderText("Enter username")
        self.username_field.setStyleSheet(self.get_input_style())
        form_layout.addWidget(self.username_field)
        
        # Password
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Enter password")
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_field.setStyleSheet(self.get_input_style())
        form_layout.addWidget(self.password_field)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(0, 32, 0, 0)
        
        # Sign in button
        login_btn = QPushButton("Sign in")
        login_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        login_btn.setStyleSheet(self.get_primary_button_style())
        login_btn.clicked.connect(self.handle_login)
        button_layout.addWidget(login_btn)
        
        # Config button - just an icon button
        config_btn = QPushButton("⚙")
        config_btn.setFixedSize(40, 40)
        config_btn.setFont(QFont("Segoe UI", 16))
        config_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #a0a0a0;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #404040;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #484848;
            }
        """)
        config_btn.clicked.connect(self.open_config_dialog)
        
        # Align config button to the right
        config_layout = QHBoxLayout()
        config_layout.addStretch()
        config_layout.addWidget(config_btn)
        button_layout.addLayout(config_layout)
        
        layout.addLayout(button_layout)
        

        main_layout.addWidget(left_widget)
    
    def create_image_section(self, main_layout):
        right_widget = QWidget()
        right_widget.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
            }
        """)
        
        layout = QVBoxLayout(right_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #a0a0a0;
                font-size: 14px;
            }
        """)
        self.image_label.setText("Loading image...")
        
        layout.addWidget(self.image_label)
        main_layout.addWidget(right_widget)
        
        # Load image from URL
        #image_url = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "placeholder2.png")
        self.load_image("/home/amarjay/Desktop/code/matek/src/gcs/assets/images/placeholder.png")

    def load_image(self, url):
        self.image_label.setPixmap(QPixmap(url))
        self.image_label.setScaledContents(True)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def on_image_loaded(self, pixmap):
        # Scale image to fit while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            550, 600, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
    
    def get_input_style(self):
        return """
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 12px 16px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
            QLineEdit::placeholder {
                color: #808080;
            }
        """
    
    def get_primary_button_style(self):
        return """
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """
    
    def handle_login(self):
        self.dialog.load_config()
        username = self.username_field.text().strip()
        password = self.password_field.text()
        if not username or not password:
            show_message(self, MessageType.WARNING, "Please enter both username and password.")
            return

        if username == self.dialog.config_data.get("app", {}).get("user", "") and password == self.dialog.config_data.get("app", {}).get("password", ""):
            # Simulate login
            self.accept()
            self.close()
            #show_message(self, MessageType.INFO, "Login successful!")
            # Proceed to the main application logic
        else:
            show_message(self, MessageType.ERROR, "Invalid username or password. Please try again.")
        
    def open_config_dialog(self):
        self.dialog.load_config()
        self.dialog.exec()


def main():
    app = QApplication(sys.argv)    

    # Enable high DPI support
    #app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    #app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    window = LoginWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
