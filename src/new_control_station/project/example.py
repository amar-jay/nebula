import sys
from PySide6.QtWidgets import (
	QApplication,
	QMainWindow,
	QVBoxLayout,
	QWidget,
	QLineEdit,
	QPushButton,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt
from src.new_control_station.map_widget import (
	MapWidget,
)  # Assuming map_widget.py is in the same directory


# coding:utf-8
from PySide6.QtCore import QEvent, Qt, QSize, QRect
from PySide6.QtWidgets import QWidget, QMainWindow, QDialog
# import QGuiApplication 
from PySide6.QtGui import QGuiApplication

from qframelesswindow import FramelessWindow


class BrowserApp(FramelessWindow):
	def __init__(self):
		super().__init__()

		self.setWindowTitle("Simple PySide6 Browser")
		self.setGeometry(100, 100, 1024, 768)
		self.setResizeEnabled(True)

		# Main widget and layout
		self.browser = MapWidget([37.7749, -122.4194])
		# QWebEngineView()
		# self.browser.setUrl(QUrl("https://www.google.com"))

		self.url_bar = QLineEdit()
		self.url_bar.setPlaceholderText("Enter URL and press Enter...")
		self.url_bar.returnPressed.connect(self.load_url)

		self.go_button = QPushButton("Go")
		self.go_button.clicked.connect(self.load_url)

		layout = QVBoxLayout()
		layout.addWidget(self.url_bar)
		layout.addWidget(self.go_button)
		layout.addWidget(self.browser)

		# container = QWidget()
		# container.setLayout(layout)
		# self.setCentralWidget(container) #not working with frameless window
		self.setLayout(layout)
		self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)

	def load_url(self):
		url = self.url_bar.text()
		if not url.startswith("http"):
			url = "https://" + url
		self.browser.setUrl(QUrl(url))


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = BrowserApp()
	window.show()
	sys.exit(app.exec())
