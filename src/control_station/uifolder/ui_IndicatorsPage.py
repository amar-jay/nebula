# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'IndicatorsPage.ui'
##
## Created by: Qt User Interface Compiler version 6.5.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
                            QMetaObject, QObject, QPoint, QRect,
                            QSize, QTime, QUrl, Qt, Property)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
                           QFont, QFontDatabase, QGradient, QIcon,
                           QImage, QKeySequence, QLinearGradient, QPainter,
                           QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QSizePolicy, QVBoxLayout, QWidget)
from . import rc_indicators

class Ui_IndicatorsPage(object):
        def setupUi(self, IndicatorsPage):
                if not IndicatorsPage.objectName():
                        IndicatorsPage.setObjectName(u"IndicatorsPage")
                IndicatorsPage.resize(885, 651)
                IndicatorsPage.setMinimumSize(QSize(700, 650))
                IndicatorsPage.setStyleSheet(u"QFrame{background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.542, y2:0.0283636, stop:0.133663 rgba(30, 33, 31, 255), stop:0.816832 rgba(40, 44, 52, 255));\n"
                                             "border-radius: 20px;\n"
                                             "border: 0px, solid, black;\n"
                                             "color: #ffffff;\n"
                                             "}\n"
                                             "QLabel{background-color: transparent;}")
                self.verticalLayout = QVBoxLayout(IndicatorsPage)
                self.verticalLayout.setObjectName(u"verticalLayout")
                self.widget = QWidget(IndicatorsPage)
                self.widget.setObjectName(u"widget")
                sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                sizePolicy.setHorizontalStretch(0)
                sizePolicy.setVerticalStretch(0)
                sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
                self.widget.setSizePolicy(sizePolicy)
                self.widget.setMinimumSize(QSize(600, 400))
                self.widget.setStyleSheet(u"")
                self.gridLayout = QGridLayout(self.widget)
                self.gridLayout.setObjectName(u"gridLayout")
                self.Vspeedometer = QFrame(self.widget)
                self.Vspeedometer.setObjectName(u"Vspeedometer")
                sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                sizePolicy1.setHorizontalStretch(0)
                sizePolicy1.setVerticalStretch(0)
                sizePolicy1.setHeightForWidth(self.Vspeedometer.sizePolicy().hasHeightForWidth())
                self.Vspeedometer.setSizePolicy(sizePolicy1)
                self.Vspeedometer.setMinimumSize(QSize(272, 272))
                self.Vspeedometer.setMaximumSize(QSize(300, 16777215))
                self.Vspeedometer.setFrameShape(QFrame.StyledPanel)
                self.Vspeedometer.setFrameShadow(QFrame.Raised)
                self.vspeed_label = QLabel(self.Vspeedometer)
                self.vspeed_label.setObjectName(u"vspeed_label")
                self.vspeed_label.setGeometry(QRect(20, 8, 256, 256))
                sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                sizePolicy2.setHorizontalStretch(1)
                sizePolicy2.setVerticalStretch(1)
                sizePolicy2.setHeightForWidth(self.vspeed_label.sizePolicy().hasHeightForWidth())
                self.vspeed_label.setSizePolicy(sizePolicy2)
                self.vspeed_label.setMinimumSize(QSize(256, 256))
                self.vspeed_label.setMaximumSize(QSize(16777215, 16777215))
                self.vspeed_label.setSizeIncrement(QSize(1, 1))
                self.vspeed_label.setMouseTracking(False)
                self.vspeed_label.setFrameShape(QFrame.Box)
                self.vspeed_label.setFrameShadow(QFrame.Plain)
                self.vspeed_label.setMidLineWidth(0)
                self.vspeed_label.setPixmap(QPixmap(u":/meters/assets/Vertical_Speed.png"))
                self.vspeed_label.setScaledContents(True)
                self.vspeed_label.setAlignment(Qt.AlignCenter)
                self.vspeed_label.setIndent(-1)
                self.vspeed_needle = RotatingLabel(u"uifolder/assets/needle.png", self.Vspeedometer)
                self.vspeed_needle.setObjectName(u"vspeed_needle")
                self.vspeed_needle.setGeometry(QRect(20, 8, 256, 256))
                self.vspeed_needle.setStyleSheet(u"background-color: transparent")
                self.vspeed_needle.setPixmap(QPixmap(u":/needles/assets/needle.png"))
                self.vspeed_needle.setScaledContents(False)
                self.vspeed_needle.setAlignment(Qt.AlignCenter)
                self.speed_text_2 = QLabel(self.Vspeedometer)
                self.speed_text_2.setObjectName(u"speed_text_2")
                self.speed_text_2.setGeometry(QRect(118, 160, 60, 30))
                self.speed_text_2.setStyleSheet(u" color: #ffffff; font-family: 'Lato',sans-serif; font-size: 18px; font-weight: bold; text-align: center; text-transform: uppercase;")
                self.speed_text_2.setAlignment(Qt.AlignCenter)

                self.gridLayout.addWidget(self.Vspeedometer, 1, 1, 1, 1)

                self.Altitude = QFrame(self.widget)
                self.Altitude.setObjectName(u"Altitude")
                sizePolicy3 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                sizePolicy3.setHorizontalStretch(0)
                sizePolicy3.setVerticalStretch(0)
                sizePolicy3.setHeightForWidth(self.Altitude.sizePolicy().hasHeightForWidth())
                self.Altitude.setSizePolicy(sizePolicy3)
                self.Altitude.setMinimumSize(QSize(60, 550))
                self.Altitude.setFrameShape(QFrame.StyledPanel)
                self.Altitude.setFrameShadow(QFrame.Raised)
                self.altitude_label = QLabel(self.Altitude)
                self.altitude_label.setObjectName(u"altitude_label")
                self.altitude_label.setGeometry(QRect(5, 24, 50, 501))
                sizePolicy4 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
                sizePolicy4.setHorizontalStretch(0)
                sizePolicy4.setVerticalStretch(0)
                sizePolicy4.setHeightForWidth(self.altitude_label.sizePolicy().hasHeightForWidth())
                self.altitude_label.setSizePolicy(sizePolicy4)
                self.altitude_label.setMinimumSize(QSize(50, 400))
                self.altitude_label.setMaximumSize(QSize(16777215, 512))
                self.altitude_label.setPixmap(QPixmap(u":/meters/assets/Altitude.png"))
                self.altitude_label.setScaledContents(True)
                self.altitude_needle = QLabel(self.Altitude)
                self.altitude_needle.setObjectName(u"altitude_needle")
                self.altitude_needle.setGeometry(QRect(0, 508, 60, 20))
                self.altitude_needle.setStyleSheet(u"background-color: transparent")
                self.altitude_needle.setPixmap(QPixmap(u":/needles/assets/Rectangle.png"))
                self.altitude_needle.setScaledContents(True)

                self.gridLayout.addWidget(self.Altitude, 0, 2, 2, 1)

                self.AttitudeIndicator = QFrame(self.widget)
                self.AttitudeIndicator.setObjectName(u"AttitudeIndicator")
                sizePolicy1.setHeightForWidth(self.AttitudeIndicator.sizePolicy().hasHeightForWidth())
                self.AttitudeIndicator.setSizePolicy(sizePolicy1)
                self.AttitudeIndicator.setMinimumSize(QSize(272, 272))
                self.AttitudeIndicator.setMaximumSize(QSize(300, 16777215))
                self.AttitudeIndicator.setFrameShape(QFrame.StyledPanel)
                self.AttitudeIndicator.setFrameShadow(QFrame.Raised)
                self.attitude_middle = RotatingLabel(u"uifolder/assets/gyrocircle.png", self.AttitudeIndicator)
                self.attitude_middle.setObjectName(u"attitude_middle")
                self.attitude_middle.setGeometry(QRect(55, 41, 187, 187))
                self.attitude_middle.setStyleSheet(u"background-color: transparent")
                self.attitude_middle.setScaledContents(False)
                self.attitude_middle.setAlignment(Qt.AlignCenter)
                self.attitude_middle.setWordWrap(False)
                self.attitude_middle.setMargin(0)
                self.attitude_label = QLabel(self.AttitudeIndicator)
                self.attitude_label.setObjectName(u"attitude_label")
                self.attitude_label.setGeometry(QRect(20, 8, 256, 256))
                sizePolicy.setHeightForWidth(self.attitude_label.sizePolicy().hasHeightForWidth())
                self.attitude_label.setSizePolicy(sizePolicy)
                self.attitude_label.setMinimumSize(QSize(256, 256))
                self.attitude_label.setMaximumSize(QSize(16777215, 16777215))
                self.attitude_label.setStyleSheet(u"")
                self.attitude_label.setFrameShape(QFrame.NoFrame)
                self.attitude_label.setPixmap(QPixmap(u":/meters/assets/Gyroscope.png"))
                self.attitude_label.setScaledContents(True)
                self.attitude_label.setAlignment(Qt.AlignCenter)
                self.attitude_label.setWordWrap(False)
                self.attitude_label.setOpenExternalLinks(False)

                self.gridLayout.addWidget(self.AttitudeIndicator, 0, 1, 1, 1)

                self.Direction = QFrame(self.widget)
                self.Direction.setObjectName(u"Direction")
                sizePolicy3.setHeightForWidth(self.Direction.sizePolicy().hasHeightForWidth())
                self.Direction.setSizePolicy(sizePolicy3)
                self.Direction.setMinimumSize(QSize(272, 272))
                self.Direction.setMaximumSize(QSize(300, 16777215))
                self.Direction.setStyleSheet(u"")
                self.Direction.setFrameShape(QFrame.StyledPanel)
                self.Direction.setFrameShadow(QFrame.Raised)
                self.direction_label = QLabel(self.Direction)
                self.direction_label.setObjectName(u"direction_label")
                self.direction_label.setGeometry(QRect(20, 8, 256, 256))
                sizePolicy2.setHeightForWidth(self.direction_label.sizePolicy().hasHeightForWidth())
                self.direction_label.setSizePolicy(sizePolicy2)
                self.direction_label.setMinimumSize(QSize(256, 256))
                self.direction_label.setMaximumSize(QSize(16777215, 16777215))
                self.direction_label.setSizeIncrement(QSize(1, 1))
                self.direction_label.setMouseTracking(False)
                self.direction_label.setFrameShape(QFrame.Box)
                self.direction_label.setFrameShadow(QFrame.Plain)
                self.direction_label.setMidLineWidth(0)
                self.direction_label.setPixmap(QPixmap(u":/meters/assets/Gyrometre.png"))
                self.direction_label.setScaledContents(True)
                self.direction_label.setAlignment(Qt.AlignCenter)
                self.direction_label.setIndent(-1)
                self.direction_needle = RotatingLabel(u"uifolder/assets/plane.png", self.Direction)
                self.direction_needle.setObjectName(u"direction_needle")
                self.direction_needle.setGeometry(QRect(20, 8, 252, 252))
                self.direction_needle.setStyleSheet(u"background-color: transparent")
                self.direction_needle.setPixmap(QPixmap(u":/needles/assets/plane.png"))
                self.direction_needle.setScaledContents(False)
                self.direction_needle.setAlignment(Qt.AlignCenter)

                self.gridLayout.addWidget(self.Direction, 1, 0, 1, 1)

                self.Speedometer = QFrame(self.widget)
                self.Speedometer.setObjectName(u"Speedometer")
                sizePolicy1.setHeightForWidth(self.Speedometer.sizePolicy().hasHeightForWidth())
                self.Speedometer.setSizePolicy(sizePolicy1)
                self.Speedometer.setMinimumSize(QSize(272, 272))
                self.Speedometer.setMaximumSize(QSize(300, 16777215))
                self.Speedometer.setFrameShape(QFrame.StyledPanel)
                self.Speedometer.setFrameShadow(QFrame.Raised)
                self.speed_label = QLabel(self.Speedometer)
                self.speed_label.setObjectName(u"speed_label")
                self.speed_label.setGeometry(QRect(20, 8, 256, 256))
                sizePolicy2.setHeightForWidth(self.speed_label.sizePolicy().hasHeightForWidth())
                self.speed_label.setSizePolicy(sizePolicy2)
                self.speed_label.setMinimumSize(QSize(256, 256))
                self.speed_label.setMaximumSize(QSize(16777215, 16777215))
                self.speed_label.setSizeIncrement(QSize(1, 1))
                self.speed_label.setMouseTracking(False)
                self.speed_label.setFrameShape(QFrame.Box)
                self.speed_label.setFrameShadow(QFrame.Plain)
                self.speed_label.setMidLineWidth(0)
                self.speed_label.setPixmap(QPixmap(u":/meters/assets/Speedometer.png"))
                self.speed_label.setScaledContents(True)
                self.speed_label.setAlignment(Qt.AlignCenter)
                self.speed_label.setIndent(-1)
                self.speed_needle = RotatingLabel(u"uifolder/assets/needle.png", self.Speedometer)
                self.speed_needle.setObjectName(u"speed_needle")
                self.speed_needle.setGeometry(QRect(20, 8, 256, 256))
                self.speed_needle.setStyleSheet(u"background-color: transparent")
                self.speed_needle.setPixmap(QPixmap(u":/needles/assets/needle.png"))
                self.speed_needle.setScaledContents(False)
                self.speed_needle.setAlignment(Qt.AlignCenter)
                self.speed_text = QLabel(self.Speedometer)
                self.speed_text.setObjectName(u"speed_text")
                self.speed_text.setGeometry(QRect(118, 212, 60, 30))
                self.speed_text.setStyleSheet(u" color: #ffffff; font-family: 'Lato',sans-serif; font-size: 18px; font-weight: bold; text-align: center; text-transform: uppercase;")
                self.speed_text.setAlignment(Qt.AlignCenter)

                self.gridLayout.addWidget(self.Speedometer, 0, 0, 1, 1)


                self.verticalLayout.addWidget(self.widget)

                self.widget_2 = QWidget(IndicatorsPage)
                self.widget_2.setObjectName(u"widget_2")
                self.widget_2.setMinimumSize(QSize(0, 60))
                self.horizontalLayout = QHBoxLayout(self.widget_2)
                self.horizontalLayout.setObjectName(u"horizontalLayout")
                self.xpos = QFrame(self.widget_2)
                self.xpos.setObjectName(u"xpos")
                self.xpos.setMinimumSize(QSize(0, 0))
                self.xpos.setStyleSheet(u" color: #ffffff; font-family: 'Lato',sans-serif; font-size: 18px; font-weight: bold; text-align: center; text-transform: uppercase;")
                self.xpos.setFrameShape(QFrame.StyledPanel)
                self.xpos.setFrameShadow(QFrame.Raised)
                self.xpos_label = QLabel(self.xpos)
                self.xpos_label.setObjectName(u"xpos_label")
                self.xpos_label.setGeometry(QRect(10, 5, 181, 31))

                self.horizontalLayout.addWidget(self.xpos)

                self.ypos = QFrame(self.widget_2)
                self.ypos.setObjectName(u"ypos")
                self.ypos.setStyleSheet(u" color: #ffffff; font-family: 'Lato',sans-serif; font-size: 18px; font-weight: bold; text-align: center; text-transform: uppercase;")
                self.ypos.setFrameShape(QFrame.StyledPanel)
                self.ypos.setFrameShadow(QFrame.Raised)
                self.ypos_label = QLabel(self.ypos)
                self.ypos_label.setObjectName(u"ypos_label")
                self.ypos_label.setGeometry(QRect(10, 5, 181, 31))

                self.horizontalLayout.addWidget(self.ypos)

                self.battery = QFrame(self.widget_2)
                self.battery.setObjectName(u"battery")
                self.battery.setStyleSheet(u" color: #ffffff; font-family: 'Lato',sans-serif; font-size: 14px; font-weight: bold; text-align: center; text-transform: uppercase;")
                self.battery.setFrameShape(QFrame.StyledPanel)
                self.battery.setFrameShadow(QFrame.Raised)
                self.battery_label = QLabel(self.battery)
                self.battery_label.setObjectName(u"battery_label")
                self.battery_label.setGeometry(QRect(10, 5, 181, 31))

                self.horizontalLayout.addWidget(self.battery)

                self.flightmode = QFrame(self.widget_2)
                self.flightmode.setObjectName(u"flightmode")
                self.flightmode.setMinimumSize(QSize(280, 0))
                self.flightmode.setStyleSheet(u" color: #ffffff; font-family: 'Lato',sans-serif; font-size: 14px; font-weight: bold; text-align: center; text-transform: uppercase;")
                self.flightmode.setFrameShape(QFrame.StyledPanel)
                self.flightmode.setFrameShadow(QFrame.Raised)
                self.flight_mode_label = QLabel(self.flightmode)
                self.flight_mode_label.setObjectName(u"flight_mode_label")
                self.flight_mode_label.setGeometry(QRect(10, 5, 181, 31))

                self.horizontalLayout.addWidget(self.flightmode)


                self.verticalLayout.addWidget(self.widget_2)


                self.retranslateUi(IndicatorsPage)

                QMetaObject.connectSlotsByName(IndicatorsPage)
        # setupUi

        def retranslateUi(self, IndicatorsPage):
                IndicatorsPage.setWindowTitle(QCoreApplication.translate("IndicatorsPage", u"Form", None))
                self.vspeed_label.setText("")
                self.vspeed_needle.setText("")
                self.speed_text_2.setText(QCoreApplication.translate("IndicatorsPage", u"00", None))
                self.altitude_label.setText("")
                self.altitude_needle.setText("")
                self.attitude_middle.setText("")
                self.attitude_label.setText("")
                self.direction_label.setText("")
                self.direction_needle.setText("")
                self.speed_label.setText("")
                self.speed_needle.setText("")
                self.speed_text.setText(QCoreApplication.translate("IndicatorsPage", u"00", None))
                self.xpos_label.setText(QCoreApplication.translate("IndicatorsPage", u"X:", None))
                self.ypos_label.setText(QCoreApplication.translate("IndicatorsPage", u"Y:", None))
                self.battery_label.setText(QCoreApplication.translate("IndicatorsPage", u"Battery:", None))
                self.flight_mode_label.setText(QCoreApplication.translate("IndicatorsPage", u"Flight Mode:", None))
        # retranslateUi

class RotatingLabel(QLabel):
        def __init__(self, image, parent=None):
                super().__init__(parent)
                self._angle = 0
                self.image = image

        def getAngle(self):
                return self._angle

        def setAngle(self, angle):
                self._angle = angle
                self.update()

        angle = Property(int, getAngle, setAngle)

        def paintEvent(self, event):
                painter = QPainter(self)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                painter.translate(self.width() / 2, self.height()/2)
                painter.rotate(self._angle)
                pixmap = QPixmap(self.image).scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(-self.width()/2, -self.height()/2, pixmap)

