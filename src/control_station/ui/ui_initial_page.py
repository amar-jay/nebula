# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'initial_pageIhwXuN.ui'
##
## Created by: Qt User Interface Compiler version 5.15.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_InitialWindow(object):
    def setupUi(self, InitialWindow):
        if not InitialWindow.objectName():
            InitialWindow.setObjectName(u"InitialWindow")
        InitialWindow.resize(680, 350)
        InitialWindow.setAnimated(True)
        self.centralwidget = QWidget(InitialWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.main_frame = QFrame(self.centralwidget)
        self.main_frame.setObjectName(u"main_frame")
        self.main_frame.setStyleSheet(u"QFrame {\n"
"	background-color: rgb(56, 58, 89);	\n"
"	color: rgb(220, 220, 220);\n"
"	border-radius: 10px;\n"
"}")
        self.main_frame.setFrameShape(QFrame.StyledPanel)
        self.main_frame.setFrameShadow(QFrame.Raised)
        self.drone_address_bar = QLineEdit(self.main_frame)
        self.drone_address_bar.setObjectName(u"drone_address_bar")
        self.drone_address_bar.setGeometry(QRect(240, 100, 371, 41))
        self.drone_address_bar.setStyleSheet(u"border-radius: 15px;")
        self.drone_address_label = QLabel(self.main_frame)
        self.drone_address_label.setObjectName(u"drone_address_label")
        self.drone_address_label.setGeometry(QRect(80, 110, 141, 21))
        self.drone_address_label.setStyleSheet(u"color: rgb(200, 143, 202);\n"
"font: 16pt \"Abyssinica SIL\";")
        self.main_title = QLabel(self.main_frame)
        self.main_title.setObjectName(u"main_title")
        self.main_title.setGeometry(QRect(10, 10, 661, 61))
        font = QFont()
        font.setFamily(u"Segoe UI")
        font.setPointSize(40)
        self.main_title.setFont(font)
        self.main_title.setStyleSheet(u"color: rgb(254, 121, 199);")
        self.main_title.setAlignment(Qt.AlignCenter)
        self.camera_address_label = QLabel(self.main_frame)
        self.camera_address_label.setObjectName(u"camera_address_label")
        self.camera_address_label.setGeometry(QRect(80, 170, 151, 21))
        self.camera_address_label.setStyleSheet(u"color: rgb(200, 143, 202);\n"
"font: 16pt \"Abyssinica SIL\";")
        self.camera_address_bar = QLineEdit(self.main_frame)
        self.camera_address_bar.setObjectName(u"camera_address_bar")
        self.camera_address_bar.setGeometry(QRect(240, 160, 371, 41))
        self.camera_address_bar.setStyleSheet(u"border-radius: 15px;")
        self.submit_btn = QPushButton(self.main_frame)
        self.submit_btn.setObjectName(u"submit_btn")
        self.submit_btn.setGeometry(QRect(490, 240, 121, 41))
        self.submit_btn.setStyleSheet(u"font: 11pt \"Abyssinica SIL\";\n"
"color: rgb(255, 255, 255);\n"
"background-color: rgb(107, 73, 131);\n"
"border-radius: 10px;\n"
"padding: 10 10 10 10;\n"
"border-color: rgb(123, 124, 156);")

        self.verticalLayout.addWidget(self.main_frame)

        InitialWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(InitialWindow)

        QMetaObject.connectSlotsByName(InitialWindow)
    # setupUi

    def retranslateUi(self, InitialWindow):
        InitialWindow.setWindowTitle(QCoreApplication.translate("InitialWindow", u"MainWindow", None))
#if QT_CONFIG(tooltip)
        self.drone_address_bar.setToolTip(QCoreApplication.translate("InitialWindow", u"<html><head/><body><p>Address</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.drone_address_label.setText(QCoreApplication.translate("InitialWindow", u"<html><head/><body><p align=\"justify\"><span style=\" font-weight:600;\">Drone</span> Adresi</p></body></html>", None))
        self.main_title.setText(QCoreApplication.translate("InitialWindow", u"<html><head/><body><p><span style=\" font-weight:600;\">MATEK</span> Login</p></body></html>", None))
        self.camera_address_label.setText(QCoreApplication.translate("InitialWindow", u"<html><head/><body><p><span style=\" font-weight:600;\">Camera</span> Adresi</p></body></html>", None))
#if QT_CONFIG(tooltip)
        self.camera_address_bar.setToolTip(QCoreApplication.translate("InitialWindow", u"<html><head/><body><p>Address</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.submit_btn.setText(QCoreApplication.translate("InitialWindow", u"PushButton", None))
    # retranslateUi

