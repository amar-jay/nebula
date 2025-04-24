# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'splash_screenMZHvKW.ui'
##
## Created by: Qt User Interface Compiler version 5.15.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_SplashScreen(object):
    def setupUi(self, SplashScreen):
        if not SplashScreen.objectName():
            SplashScreen.setObjectName("SplashScreen")
        SplashScreen.resize(680, 400)
        self.centralwidget = QWidget(SplashScreen)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.dropShadowFrame = QFrame(self.centralwidget)
        self.dropShadowFrame.setObjectName("dropShadowFrame")
        self.dropShadowFrame.setStyleSheet(
            "QFrame {	\n"
            "	background-color: rgb(56, 58, 89);	\n"
            "	color: rgb(220, 220, 220);\n"
            "	border-radius: 10px;\n"
            "}"
        )
        self.dropShadowFrame.setFrameShape(QFrame.StyledPanel)
        self.dropShadowFrame.setFrameShadow(QFrame.Raised)
        self.label_title = QLabel(self.dropShadowFrame)
        self.label_title.setObjectName("label_title")
        self.label_title.setGeometry(QRect(0, 180, 661, 61))
        font = QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(40)
        self.label_title.setFont(font)
        self.label_title.setStyleSheet("color: rgb(254, 121, 199);")
        self.label_title.setAlignment(Qt.AlignCenter)
        self.label_description = QLabel(self.dropShadowFrame)
        self.label_description.setObjectName("label_description")
        self.label_description.setGeometry(QRect(0, 240, 661, 31))
        font1 = QFont()
        font1.setFamily("Abyssinica SIL")
        font1.setPointSize(11)
        font1.setBold(False)
        font1.setItalic(False)
        font1.setWeight(50)
        self.label_description.setFont(font1)
        self.label_description.setStyleSheet(
            'color: rgb(98, 114, 164);\nfont: 11pt "Abyssinica SIL";'
        )
        self.label_description.setAlignment(Qt.AlignCenter)
        self.progressBar = QProgressBar(self.dropShadowFrame)
        self.progressBar.setObjectName("progressBar")
        self.progressBar.setGeometry(QRect(50, 300, 561, 23))
        self.progressBar.setStyleSheet(
            "QProgressBar {\n"
            "	\n"
            "	background-color: rgb(98, 114, 164);\n"
            "	color: rgb(200, 200, 200);\n"
            "	border-style: none;\n"
            "	border-radius: 10px;\n"
            "	text-align: center;\n"
            "}\n"
            "QProgressBar::chunk{\n"
            "	border-radius: 10px;\n"
            "	background-color: qlineargradient(spread:pad, x1:0, y1:0.511364, x2:1, y2:0.523, stop:0 rgba(254, 121, 199, 255), stop:1 rgba(170, 85, 255, 255));\n"
            "}"
        )
        self.progressBar.setValue(24)
        self.label_loading = QLabel(self.dropShadowFrame)
        self.label_loading.setObjectName("label_loading")
        self.label_loading.setGeometry(QRect(0, 330, 661, 21))
        font2 = QFont()
        font2.setFamily("Segoe UI")
        font2.setPointSize(12)
        self.label_loading.setFont(font2)
        self.label_loading.setStyleSheet("color: rgb(98, 114, 164);")
        self.label_loading.setAlignment(Qt.AlignCenter)
        self.label_credits = QLabel(self.dropShadowFrame)
        self.label_credits.setObjectName("label_credits")
        self.label_credits.setGeometry(QRect(20, 350, 621, 21))
        font3 = QFont()
        font3.setFamily("Segoe UI")
        font3.setPointSize(10)
        self.label_credits.setFont(font3)
        self.label_credits.setStyleSheet("color: rgb(98, 114, 164);")
        self.label_credits.setAlignment(
            Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter
        )
        self.logo = QFrame(self.dropShadowFrame)
        self.logo.setObjectName("logo")
        self.logo.setGeometry(QRect(250, 60, 120, 80))
        self.logo.setStyleSheet("")
        self.logo.setFrameShape(QFrame.StyledPanel)
        self.logo.setFrameShadow(QFrame.Raised)

        self.verticalLayout.addWidget(self.dropShadowFrame)

        SplashScreen.setCentralWidget(self.centralwidget)

        self.retranslateUi(SplashScreen)

        QMetaObject.connectSlotsByName(SplashScreen)

    # setupUi

    def retranslateUi(self, SplashScreen):
        SplashScreen.setWindowTitle(
            QCoreApplication.translate("SplashScreen", "MainWindow", None)
        )
        self.label_title.setText(
            QCoreApplication.translate(
                "SplashScreen",
                "<html><head/><body><p>M A T E K</p></body></html>",
                None,
            )
        )
        self.label_description.setText(
            QCoreApplication.translate(
                "SplashScreen",
                '<html><head/><body><p align="center"><span style=" font-size:14pt;">Control Station</span></p></body></html>',
                None,
            )
        )
        self.label_loading.setText(
            QCoreApplication.translate("SplashScreen", "loading...", None)
        )
        self.label_credits.setText(
            QCoreApplication.translate(
                "SplashScreen",
                '<html><head/><body><p><span style=" font-weight:600;">MATEK</span> Teknofest Team</p></body></html>',
                None,
            )
        )

    # retranslateUi
