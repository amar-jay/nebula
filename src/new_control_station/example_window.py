import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def create_tab(icon_path, tooltip, widget, tab_widget):
    index = tab_widget.addTab(widget, "")
    tab_widget.setTabIcon(index, QIcon(icon_path))
    tab_widget.setTabToolTip(index, tooltip)
    # Optionally remove the text label
    tab_widget.tabBar().setTabText(index, "")  # Icon-only tab


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Icon Tab App")
        self.setMinimumSize(1000, 600)

        layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.West)
        self.tab_widget.setIconSize(QSize(28, 28))

        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border-radius: 10px;
                padding: 5px;
                margin: 0px;
                background-color: #2c2c2c;
            }
            QTabBar::tab {
                border: 1px solid #444;
                border-radius: 8px;
                background-color: #444;
                margin-bottom: 8px;
                padding: 10px;
                width: 40px;
                height: 40px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                border: 2px solid #0078d4;
            }
            QTabBar::tab:hover:!selected {
                background-color: #555;
            }
        """
        )

        # Sample content widgets
        basic_control_widget = QLabel("Robot Controls Panel")
        camera_widget = QLabel("Camera Stream")
        mission_widget = QLabel("Mission Planner")
        telemetry_widget = QLabel("Telemetry Dashboard")
        console_widget = QLabel("Developer Console")

        # Add icon-only tabs with tooltips
        create_tab(
            "assets/images/drone.png", "Controls", basic_control_widget, self.tab_widget
        )
        create_tab(
            "assets/images/mobileuser.png", "Camera", camera_widget, self.tab_widget
        )
        create_tab(
            "assets/images/target.png", "Missions", mission_widget, self.tab_widget
        )
        create_tab(
            "assets/images/antenna.png", "Telemetry", telemetry_widget, self.tab_widget
        )
        create_tab("assets/images/home.png", "Console", console_widget, self.tab_widget)

        layout.addWidget(self.tab_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
