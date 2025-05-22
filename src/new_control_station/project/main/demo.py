# coding:utf-8
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout
from qfluentwidgets import (
	NavigationItemPosition,
	MessageBox,
	setTheme,
	Theme,
	SplitFluentWindow,
	NavigationAvatarWidget,
	qrouter,
	SubtitleLabel,
	setFont,
)
from qfluentwidgets import FluentIcon as FIF
from utils import get_asset
from .map_widget import MapWidget


class Widget(QFrame):
	def __init__(self, text: str, parent=None):
		super().__init__(parent=parent)
		self.label = SubtitleLabel(text, self)
		self.hBoxLayout = QHBoxLayout(self)

		setFont(self.label, 24)
		self.label.setAlignment(Qt.AlignCenter)
		self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
		self.setObjectName(text.replace(" ", "-"))

		# !IMPORTANT: leave some space for title bar
		self.hBoxLayout.setContentsMargins(0, 32, 0, 0)


class Window(SplitFluentWindow):
	def __init__(self):
		super().__init__()

		# create sub interface
		# self.homeInterface = MapWidget(center_coord=[41.27442, 28.727317])
		self.homeInterface = Widget("Home", self)
		self.telemetryInterface = Widget("Telemetry", self)
		self.missionInterface = Widget("Missions", self)
		self.consoleInterface = Widget("Console Interface", self)
		self.settingInterface = Widget("Setting Interface", self)
		self.albumInterface = Widget("Album Interface", self)
		self.albumInterface1 = Widget("Album Interface 1", self)
		self.albumInterface2 = Widget("Album Interface 2", self)
		self.albumInterface1_1 = Widget("Album Interface 1-1", self)

		self.initNavigation()
		self.initWindow()

	def initNavigation(self):
		self.addSubInterface(self.homeInterface, FIF.GLOBE, "Maps Page")
		self.addSubInterface(self.telemetryInterface, FIF.WIFI, "Telemetry Page")
		self.addSubInterface(self.missionInterface, FIF.AIRPLANE, "Missions Page")

		self.navigationInterface.addSeparator()

		self.addSubInterface(
			self.albumInterface, FIF.ALBUM, "Albums", NavigationItemPosition.SCROLL
		)
		self.addSubInterface(
			self.albumInterface1, FIF.ALBUM, "Album 1", parent=self.albumInterface
		)
		self.addSubInterface(
			self.albumInterface1_1, FIF.ALBUM, "Album 1.1", parent=self.albumInterface1
		)
		self.addSubInterface(
			self.albumInterface2, FIF.ALBUM, "Album 2", parent=self.albumInterface
		)
		self.addSubInterface(
			self.consoleInterface,
			FIF.CONNECT,
			"Console Page",
			NavigationItemPosition.SCROLL,
		)

		# add custom widget to bottom
		self.navigationInterface.addWidget(
			routeKey="avatar",
			widget=NavigationAvatarWidget("nebula", get_asset("images/logo.png")),
			onClick=self.showMessageBox,
			position=NavigationItemPosition.BOTTOM,
		)

		self.addSubInterface(
			self.settingInterface,
			FIF.SETTING,
			"Settings",
			NavigationItemPosition.BOTTOM,
		)

		# NOTE: enable acrylic effect
		# self.navigationInterface.setAcrylicEnabled(True)

	def initWindow(self):
		self.resize(900, 700)
		self.setWindowIcon(QIcon(get_asset("images/logo.png")))
		self.setWindowTitle("Nebula Control Station")

		desktop = QApplication.screens()[0].availableGeometry()
		w, h = desktop.width(), desktop.height()
		self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

	def showMessageBox(self):
		w = MessageBox(
			"Yazarı Destekleyin",
			"Bu proje için 2025 Nebula ekibimize büyük selamlar! Bize ulaşmak isterseniz, elinize ne geçerse oradan yazın — haha.",
			self,
		)
		w.yesButton.setText("sitesini git")
		w.cancelButton.setText("Iptal et")

		if w.exec():
			QDesktopServices.openUrl(QUrl("https://amarjay.vercel.app/"))
