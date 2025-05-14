# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'splash_mainRWSree.ui'
##
## Created by: Qt User Interface Compiler version 5.15.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_MainWindow(object):
	def setupUi(self, MainWindow):
		if not MainWindow.objectName():
			MainWindow.setObjectName("MainWindow")
		MainWindow.resize(795, 600)
		self.centralwidget = QWidget(MainWindow)
		self.centralwidget.setObjectName("centralwidget")
		self.verticalLayout = QVBoxLayout(self.centralwidget)
		self.verticalLayout.setObjectName("verticalLayout")
		self.label = QLabel(self.centralwidget)
		self.label.setObjectName("label")
		self.label.setStyleSheet('font: italic 21pt "UbuntuCondensed Nerd Font Mono";')
		self.label.setAlignment(Qt.AlignCenter)

		self.verticalLayout.addWidget(self.label)

		self.frame = QFrame(self.centralwidget)
		self.frame.setObjectName("frame")
		self.frame.setFrameShape(QFrame.StyledPanel)
		self.frame.setFrameShadow(QFrame.Raised)
		self.verticalLayout_2 = QVBoxLayout(self.frame)
		self.verticalLayout_2.setObjectName("verticalLayout_2")
		self.pushButton = QPushButton(self.frame)
		self.pushButton.setObjectName("pushButton")
		self.pushButton.setStyleSheet(
			"QPushButton {\n"
			'	font: 26pt "Ubuntu";\n'
			'	background-color: "red";\n'
			'	color: "white";\n'
			"border-radius: 15px;\n"
			"}"
		)

		self.verticalLayout_2.addWidget(self.pushButton)

		self.verticalLayout.addWidget(self.frame)

		MainWindow.setCentralWidget(self.centralwidget)
		self.statusbar = QStatusBar(MainWindow)
		self.statusbar.setObjectName("statusbar")
		MainWindow.setStatusBar(self.statusbar)

		self.retranslateUi(MainWindow)

		QMetaObject.connectSlotsByName(MainWindow)

	# setupUi

	def retranslateUi(self, MainWindow):
		MainWindow.setWindowTitle(
			QCoreApplication.translate("MainWindow", "MainWindow", None)
		)
		self.label.setText(
			QCoreApplication.translate("MainWindow", "MAIN WINDOW HERE", None)
		)
		self.pushButton.setText(
			QCoreApplication.translate("MainWindow", "Go to thlkajlkfj;lkjas", None)
		)

	# retranslateUi
