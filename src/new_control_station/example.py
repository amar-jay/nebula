import sys
from PySide6 import QtWidgets
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QMdiSubWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
from qfluentwidgets import FluentWindow


class BrowserWindow(QMainWindow):
	def __init__(self, url):
		super().__init__()
		self.setWindowTitle("Embedded Browser")
		self.resize(900, 600)

		view = QWebEngineView()
		# view.load(QUrl(url))
		self.setCentralWidget(view)


class MyApp(QMdiSubWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Main Fluent App")
		self.resize(800, 500)

		button = QPushButton("Open Browser")
		button.setObjectName("open_browser_button")
		button.clicked.connect(self.open_browser)
		self.setWidget(button)
		# self.addSubInterface(button, "up", "button")
		# self.setCentralWidget(button)

	def open_browser(self):
		# ✅ open browser in a separate native window
		self.browser = BrowserWindow("https://qt.io")
		self.browser.show()


if __name__ == "__main__":
	app = QApplication(sys.argv)

	w = MyApp()
	w.show()
	sys.exit(app.exec())
