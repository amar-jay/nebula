import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import FluentWindow, Theme, setTheme

from src.new_control_station.map_widget import MapWidget


class MainWindow(FluentWindow, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dock Widget in Fullscreen Example")
        self.resize(800, 600)

        # Create central widget
        central = QWidget()
        layout = QVBoxLayout(central)

        # Add buttons for toggling window state
        self.max_button = QPushButton("Show Map")
        self.max_button.clicked.connect(self.toggle_maximized)

        # Add a label to explain functionality
        text_edit = QTextEdit()
        text_edit.setPlainText(
            "This example shows a dock widget that only appears when the window is maximized.\n"
            "Toggle the window state using the button above."
        )
        text_edit.setReadOnly(True)

        self.fullscreen_button_widget = QWidget()
        button_layout = QVBoxLayout(self.fullscreen_button_widget)

        button1 = QPushButton("Select Point")
        button2 = QPushButton("Select Area")
        button3 = QPushButton("Set Waypoint")
        button4 = QPushButton("Clear All")
        button5 = QPushButton("Undo")
        button6 = QPushButton("Choose Field")
        button_row_1 = QWidget()
        button_row_2 = QWidget()
        button_row_1_layout = QHBoxLayout(button_row_1)
        button_row_2_layout = QHBoxLayout(button_row_2)
        button_row_1_layout.addWidget(button1)
        button_row_1_layout.addWidget(button2)
        button_row_1_layout.addWidget(button3)
        button_row_2_layout.addWidget(button4)
        button_row_2_layout.addWidget(button5)
        button_row_2_layout.addWidget(button6)
        button_row_1.setLayout(button_row_1_layout)
        button_row_2.setLayout(button_row_2_layout)
        button_layout.addWidget(button_row_1)
        button_layout.addWidget(button_row_2)
        button_layout.setContentsMargins(10, 10, 10, 10)
        button_row_1_layout.setSpacing(30)
        button_row_2_layout.setSpacing(30)
        button_layout.setSpacing(0)

        button_row_1_layout.addWidget(button1)
        button_row_1_layout.addWidget(button2)
        button_row_1_layout.addWidget(button3)
        button_row_2_layout.addWidget(button4)
        button_row_2_layout.addWidget(button5)
        button_row_2_layout.addWidget(button6)

        button1.clicked.connect(self.select_point)
        button2.clicked.connect(self.select_area)
        button3.clicked.connect(self.waypoint)
        button4.clicked.connect(self.clear_all)
        button5.clicked.connect(self.undo_waypoint)
        button6.clicked.connect(self.choose_field)

        self.fullscreen_button_widget.setVisible(False)

        layout.addWidget(self.max_button)
        layout.addWidget(self.fullscreen_button_widget)
        layout.addWidget(text_edit)

        # wrap widget in a single widget layout
        central_layout = QVBoxLayout(central)
        central_layout.addLayout(layout)
        central_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(central_layout)

        # Create dock widget
        self.dock = QDockWidget("Special Dock (Fullscreen Only)", self)
        self.dock_content = MapWidget([41.27442, 28.727317])
        self.dock_content.setMinimumSize(800, 800)
        self.dock.setWidget(self.dock_content)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)

        # Initially hide the dock widget
        self.dock.setVisible(False)

        # Create the event filter to track window state changes
        self.installEventFilter(self)

    def select_point(self):
        self.dock_content.page().runJavaScript("map.on('click', moveMarkerByClick);")
        self.dock_content.page().runJavaScript("map.off('click', drawRectangle);")
        self.dock_content.page().runJavaScript("map.off('click', putWaypointEvent);")

    def select_area(self):
        self.dock_content.page().runJavaScript("map.off('click', putWaypointEvent);")
        self.dock_content.page().runJavaScript("map.off('click', moveMarkerByClick);")

        self.dock_content.page().runJavaScript("map.on('click', drawRectangle);")

    def waypoint(self):
        self.dock_content.page().runJavaScript("map.off('click', moveMarkerByClick);")
        self.dock_content.page().runJavaScript("map.off('click', drawRectangle);")
        self.dock_content.page().runJavaScript("map.on('click', putWaypointEvent);")

    def clear_all(self):
        self.dock_content.page().runJavaScript("clearAll();")

    def undo_waypoint(self):
        self.dock_content.page().runJavaScript("undoWaypoint();")

    def choose_field(self):
        pass

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # def eventFilter(self, obj, event):
    # 	super().eventFilter(obj, event)
    # 	# Check for window state change events
    # 	if obj == self:
    # 		is_maximized = self.isMaximized()
    # 		self.dock.setVisible(is_maximized)
    # 		self.fullscreen_button_widget.setVisible(is_maximized)
    # 		self.max_button.setText("Hide Map" if is_maximized else "Show Map")

    # 	return super().eventFilter(obj, event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
