import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QStackedWidget, QLabel
from PySide6.QtCore import Qt
from qfluentwidgets import TabBar, setTheme, Theme, TabCloseButtonDisplayMode


class Demo(QWidget):
	def __init__(self):
		super().__init__()
		setTheme(Theme.DARK)
		self.tabBar = TabBar(self)
		print(self.tabBar.styleSheet())
		self.stackedWidget = QStackedWidget(self)
		self.vBoxLayout = QVBoxLayout(self)

		self.songInterface = QLabel("Song Interface", self)
		self.albumInterface = QLabel("Album Interface", self)
		self.artistInterface = QLabel("Artist Interface", self)

		# add page
		self.addSubInterface(self.songInterface, "songInterface", "Song")
		self.addSubInterface(self.albumInterface, "albumInterface", "Album")
		self.addSubInterface(self.artistInterface, "artistInterface", "Artist")

		# connect signals to slots
		self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
		self.stackedWidget.setCurrentWidget(self.songInterface)
		self.tabBar.setTabsClosable(False)
		self.tabBar.setAddButtonVisible(False)
		self.tabBar.setTabSelectedBackgroundColor("#330099", "#330099")
		# self.tabBar.setTabTextColor("#FFFFFF", "#FFFFFF")

		self.vBoxLayout.setContentsMargins(30, 0, 30, 30)
		self.vBoxLayout.addWidget(self.tabBar, 0, Qt.AlignHCenter)
		self.vBoxLayout.addWidget(self.stackedWidget)
		self.resize(400, 400)

	def addSubInterface(self, widget: QLabel, objectName: str, text: str):
		widget.setObjectName(objectName)
		widget.setAlignment(Qt.AlignCenter)
		self.stackedWidget.addWidget(widget)

		# use the unique objectName as route key
		self.tabBar.addTab(
			routeKey=objectName,
			text=text,
			onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
		)

	def onCurrentIndexChanged(self, index):
		widget = self.stackedWidget.widget(index)
		self.tabBar.setCurrentTab(widget.objectName())


if __name__ == "__main__":
	app = QApplication(sys.argv)
	demo = Demo()
	demo.show()
	sys.exit(app.exec_())
