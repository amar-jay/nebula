# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'HomePage.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
	QCoreApplication,
	QDate,
	QDateTime,
	QLocale,
	QMetaObject,
	QObject,
	QPoint,
	QRect,
	QSize,
	QTime,
	QUrl,
	Qt,
)
from PySide6.QtGui import (
	QBrush,
	QColor,
	QConicalGradient,
	QCursor,
	QFont,
	QFontDatabase,
	QGradient,
	QIcon,
	QImage,
	QKeySequence,
	QLinearGradient,
	QPainter,
	QPalette,
	QPixmap,
	QRadialGradient,
	QTransform,
)
from PySide6.QtWidgets import (
	QApplication,
	QComboBox,
	QFrame,
	QGridLayout,
	QHBoxLayout,
	QPushButton,
	QSizePolicy,
	QTabWidget,
	QTextBrowser,
	QVBoxLayout,
	QWidget,
)


class Ui_HomePage(object):
	def setupUi(self, HomePage):
		if not HomePage.objectName():
			HomePage.setObjectName("HomePage")
		HomePage.resize(1097, 620)
		HomePage.setStyleSheet("")
		self.gridLayout_2 = QGridLayout(HomePage)
		self.gridLayout_2.setObjectName("gridLayout_2")
		self.frame_right = QFrame(HomePage)
		self.frame_right.setObjectName("frame_right")
		self.frame_right.setStyleSheet("QFrame{border: None;}")
		self.frame_right.setFrameShape(QFrame.StyledPanel)
		self.frame_right.setFrameShadow(QFrame.Raised)
		self.verticalLayout = QVBoxLayout(self.frame_right)
		self.verticalLayout.setObjectName("verticalLayout")
		self.cameraFrame = QWidget(self.frame_right)
		self.cameraFrame.setObjectName("cameraFrame")
		self.cameraFrame.setStyleSheet("")
		self.horizontalLayout_3 = QHBoxLayout(self.cameraFrame)
		self.horizontalLayout_3.setObjectName("horizontalLayout_3")

		self.verticalLayout.addWidget(self.cameraFrame)

		self.frame_2 = QFrame(self.frame_right)
		self.frame_2.setObjectName("frame_2")
		self.frame_2.setStyleSheet("")
		self.frame_2.setFrameShape(QFrame.StyledPanel)
		self.frame_2.setFrameShadow(QFrame.Raised)
		self.verticalLayout_2 = QVBoxLayout(self.frame_2)
		self.verticalLayout_2.setSpacing(0)
		self.verticalLayout_2.setObjectName("verticalLayout_2")
		self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
		self.tabWidget = QTabWidget(self.frame_2)
		self.tabWidget.setObjectName("tabWidget")
		self.mission = QWidget()
		self.mission.setObjectName("mission")
		self.verticalLayout_3 = QVBoxLayout(self.mission)
		self.verticalLayout_3.setObjectName("verticalLayout_3")
		self.frame = QFrame(self.mission)
		self.frame.setObjectName("frame")
		self.frame.setFrameShape(QFrame.StyledPanel)
		self.frame.setFrameShadow(QFrame.Raised)
		self.verticalLayout_4 = QVBoxLayout(self.frame)
		self.verticalLayout_4.setObjectName("verticalLayout_4")
		self.widget = QWidget(self.frame)
		self.widget.setObjectName("widget")
		self.horizontalLayout = QHBoxLayout(self.widget)
		self.horizontalLayout.setObjectName("horizontalLayout")
		self.modes_comboBox = QComboBox(self.widget)
		self.modes_comboBox.addItem("")
		self.modes_comboBox.addItem("")
		self.modes_comboBox.addItem("")
		self.modes_comboBox.addItem("")
		self.modes_comboBox.setObjectName("modes_comboBox")

		self.horizontalLayout.addWidget(self.modes_comboBox)

		self.btn_chooseMode = QPushButton(self.widget)
		self.btn_chooseMode.setObjectName("btn_chooseMode")

		self.horizontalLayout.addWidget(self.btn_chooseMode)

		self.horizontalLayout.setStretch(0, 3)
		self.horizontalLayout.setStretch(1, 1)

		self.verticalLayout_4.addWidget(self.widget)

		self.btn_setMission = QPushButton(self.frame)
		self.btn_setMission.setObjectName("btn_setMission")

		self.verticalLayout_4.addWidget(self.btn_setMission)

		self.btn_undo = QPushButton(self.frame)
		self.btn_undo.setObjectName("btn_undo")

		self.verticalLayout_4.addWidget(self.btn_undo)

		self.btn_clearAll = QPushButton(self.frame)
		self.btn_clearAll.setObjectName("btn_clearAll")

		self.verticalLayout_4.addWidget(self.btn_clearAll)

		self.verticalLayout_3.addWidget(self.frame)

		self.btn_antenna = QPushButton(self.mission)
		self.btn_antenna.setObjectName("btn_antenna")
		self.btn_antenna.setStyleSheet(
			"QPushButton{\n"
			"	border-radius: 4px;\n"
			"	\n"
			"	background-color: qlineargradient(spread:pad, x1:0.139, y1:0.862773, x2:1, y2:0.017, stop:0.159204 rgba(99, 18, 24, 255), stop:1 rgba(165, 29, 45, 252));\n"
			"}\n"
			"QPushButton:hover{ \n"
			"	background-color:qlineargradient(spread:pad, x1:0.139, y1:0.862773, x2:1, y2:0.017, stop:0.0646766 rgba(89, 22, 27, 255), stop:0.527363 rgba(165, 29, 45, 252))\n"
			"}\n"
			"QPushButton:pressed{\n"
			"  padding-left: 5px;\n"
			"	padding-top: 5px;\n"
			"	background-color: qlineargradient(spread:pad, x1:0.139, y1:0.862773, x2:1, y2:0.017, stop:0.159204 rgba(99, 18, 24, 200), stop:1 rgba(165, 29, 45, 200));\n"
			"}\n"
			"QPushButton:disabled{ \n"
			"	background-color: qlineargradient(spread:pad, x1:0.139, y1:0.862773, x2:1, y2:0.017, stop:0.159204 rgba(14, 74, 89, 255), stop:1 rgba(77, 149, 47, 255));\n"
			"}"
		)

		self.verticalLayout_3.addWidget(self.btn_antenna)

		self.frame_3 = QFrame(self.mission)
		self.frame_3.setObjectName("frame_3")
		self.frame_3.setFrameShape(QFrame.StyledPanel)
		self.frame_3.setFrameShadow(QFrame.Raised)
		self.verticalLayout_5 = QVBoxLayout(self.frame_3)
		self.verticalLayout_5.setObjectName("verticalLayout_5")
		self.btn_startMission = QPushButton(self.frame_3)
		self.btn_startMission.setObjectName("btn_startMission")

		self.verticalLayout_5.addWidget(self.btn_startMission)

		self.btn_abort = QPushButton(self.frame_3)
		self.btn_abort.setObjectName("btn_abort")

		self.verticalLayout_5.addWidget(self.btn_abort)

		self.btn_rtl = QPushButton(self.frame_3)
		self.btn_rtl.setObjectName("btn_rtl")

		self.verticalLayout_5.addWidget(self.btn_rtl)

		self.verticalLayout_3.addWidget(self.frame_3)

		self.tabWidget.addTab(self.mission, "")
		self.guided = QWidget()
		self.guided.setObjectName("guided")
		self.verticalLayout_6 = QVBoxLayout(self.guided)
		self.verticalLayout_6.setObjectName("verticalLayout_6")
		self.widget_3 = QWidget(self.guided)
		self.widget_3.setObjectName("widget_3")
		self.verticalLayout_9 = QVBoxLayout(self.widget_3)
		self.verticalLayout_9.setObjectName("verticalLayout_9")
		self.btn_takeoff = QPushButton(self.widget_3)
		self.btn_takeoff.setObjectName("btn_takeoff")

		self.verticalLayout_9.addWidget(self.btn_takeoff)

		self.btn_move = QPushButton(self.widget_3)
		self.btn_move.setObjectName("btn_move")

		self.verticalLayout_9.addWidget(self.btn_move)

		self.btn_track_all = QPushButton(self.widget_3)
		self.btn_track_all.setObjectName("btn_track_all")

		self.verticalLayout_9.addWidget(self.btn_track_all)

		self.btn_land = QPushButton(self.widget_3)
		self.btn_land.setObjectName("btn_land")

		self.verticalLayout_9.addWidget(self.btn_land)

		self.btn_rtl_2 = QPushButton(self.widget_3)
		self.btn_rtl_2.setObjectName("btn_rtl_2")

		self.verticalLayout_9.addWidget(self.btn_rtl_2)

		self.verticalLayout_6.addWidget(self.widget_3)

		self.widget_2 = QWidget(self.guided)
		self.widget_2.setObjectName("widget_2")
		self.verticalLayout_8 = QVBoxLayout(self.widget_2)
		self.verticalLayout_8.setObjectName("verticalLayout_8")
		self.btn_set_roi = QPushButton(self.widget_2)
		self.btn_set_roi.setObjectName("btn_set_roi")

		self.verticalLayout_8.addWidget(self.btn_set_roi)

		self.btn_cancel_roi = QPushButton(self.widget_2)
		self.btn_cancel_roi.setObjectName("btn_cancel_roi")

		self.verticalLayout_8.addWidget(self.btn_cancel_roi)

		self.verticalLayout_6.addWidget(self.widget_2)

		self.tabWidget.addTab(self.guided, "")
		self.Console = QWidget()
		self.Console.setObjectName("Console")
		self.verticalLayout_7 = QVBoxLayout(self.Console)
		self.verticalLayout_7.setObjectName("verticalLayout_7")
		self.textBrowser = QTextBrowser(self.Console)
		self.textBrowser.setObjectName("textBrowser")

		self.verticalLayout_7.addWidget(self.textBrowser)

		self.tabWidget.addTab(self.Console, "")

		self.verticalLayout_2.addWidget(self.tabWidget)

		self.verticalLayout.addWidget(self.frame_2)

		self.verticalLayout.setStretch(0, 1)
		self.verticalLayout.setStretch(1, 1)

		self.gridLayout_2.addWidget(self.frame_right, 0, 1, 1, 1)

		self.mapFrame = QWidget(HomePage)
		self.mapFrame.setObjectName("mapFrame")
		self.mapFrame.setMinimumSize(QSize(650, 0))
		self.mapFrame.setStyleSheet("")
		self.horizontalLayout_2 = QHBoxLayout(self.mapFrame)
		self.horizontalLayout_2.setObjectName("horizontalLayout_2")

		self.gridLayout_2.addWidget(self.mapFrame, 0, 0, 1, 1)

		self.retranslateUi(HomePage)

		self.tabWidget.setCurrentIndex(1)

		QMetaObject.connectSlotsByName(HomePage)

	# setupUi

	def retranslateUi(self, HomePage):
		HomePage.setWindowTitle(QCoreApplication.translate("HomePage", "Form", None))
		self.modes_comboBox.setItemText(
			0, QCoreApplication.translate("HomePage", "Harita Modu Se\u00e7", None)
		)
		self.modes_comboBox.setItemText(
			1,
			QCoreApplication.translate(
				"HomePage", "\u0130\u015faret\u00e7i Modu", None
			),
		)
		self.modes_comboBox.setItemText(
			2, QCoreApplication.translate("HomePage", "Alan Se\u00e7imi Modu", None)
		)
		self.modes_comboBox.setItemText(
			3, QCoreApplication.translate("HomePage", "Waypoint Modu", None)
		)

		self.btn_chooseMode.setText(
			QCoreApplication.translate("HomePage", "Modu Se\u00e7", None)
		)
		self.btn_setMission.setText(
			QCoreApplication.translate("HomePage", "G\u00f6revi Tan\u0131mla", None)
		)
		self.btn_undo.setText(QCoreApplication.translate("HomePage", "Geri Al", None))
		self.btn_clearAll.setText(
			QCoreApplication.translate("HomePage", "Hepsini Temizle", None)
		)
		self.btn_antenna.setText(
			QCoreApplication.translate("HomePage", "Anten Takibi", None)
		)
		self.btn_startMission.setText(
			QCoreApplication.translate("HomePage", "G\u00f6reve Ba\u015fla", None)
		)
		self.btn_abort.setText(
			QCoreApplication.translate("HomePage", "Takibi B\u0131rak", None)
		)
		self.btn_rtl.setText(
			QCoreApplication.translate("HomePage", "Eve D\u00f6n", None)
		)
		self.tabWidget.setTabText(
			self.tabWidget.indexOf(self.mission),
			QCoreApplication.translate("HomePage", "Mission", None),
		)
		self.btn_takeoff.setText(QCoreApplication.translate("HomePage", "Kalk", None))
		self.btn_move.setText(
			QCoreApplication.translate("HomePage", "Noktaya Git", None)
		)
		self.btn_track_all.setText(
			QCoreApplication.translate(
				"HomePage", "G\u00f6rd\u00fc\u011f\u00fcn\u00fc Takip Et", None
			)
		)
		self.btn_land.setText(
			QCoreApplication.translate("HomePage", "\u0130ni\u015f Yap", None)
		)
		self.btn_rtl_2.setText(
			QCoreApplication.translate("HomePage", "Eve D\u00f6n", None)
		)
		self.btn_set_roi.setText(
			QCoreApplication.translate("HomePage", "ROI ayarla", None)
		)
		self.btn_cancel_roi.setText(
			QCoreApplication.translate("HomePage", "ROI iptal", None)
		)
		self.tabWidget.setTabText(
			self.tabWidget.indexOf(self.guided),
			QCoreApplication.translate("HomePage", "Guided", None),
		)
		self.tabWidget.setTabText(
			self.tabWidget.indexOf(self.Console),
			QCoreApplication.translate("HomePage", "Konsol", None),
		)

	# retranslateUi
