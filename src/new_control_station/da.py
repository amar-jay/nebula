# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'designertEKwkC.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
	QAbstractButton,
	QApplication,
	QDialog,
	QDialogButtonBox,
	QSizePolicy,
	QWidget,
)

from qfluentwidgets import (
	BreadcrumbBar,
	CalendarPicker,
	CompactSpinBox,
	IconWidget,
	LineEdit,
	PasswordLineEdit,
	PillPushButton,
	PrimaryDropDownPushButton,
	PrimaryPushButton,
	PrimaryToolButton,
	PushButton,
	ToggleButton,
	ToolButton,
)


class Ui_Dialog(object):
	def setupUi(self, Dialog):
		if not Dialog.objectName():
			Dialog.setObjectName("Dialog")
		Dialog.resize(400, 300)
		self.buttonBox = QDialogButtonBox(Dialog)
		self.buttonBox.setObjectName("buttonBox")
		self.buttonBox.setGeometry(QRect(30, 240, 341, 32))
		self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
		self.buttonBox.setStandardButtons(
			QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
		)
		self.CalendarPicker = CalendarPicker(Dialog)
		self.CalendarPicker.setObjectName("CalendarPicker")
		self.CalendarPicker.setGeometry(QRect(80, 180, 123, 30))
		self.BreadcrumbBar = BreadcrumbBar(Dialog)
		self.BreadcrumbBar.setObjectName("BreadcrumbBar")
		self.BreadcrumbBar.setGeometry(QRect(100, 120, 16, 16))
		self.PrimaryToolButton = PrimaryToolButton(Dialog)
		self.PrimaryToolButton.setObjectName("PrimaryToolButton")
		self.PrimaryToolButton.setGeometry(QRect(280, 50, 38, 32))
		self.PasswordLineEdit = PasswordLineEdit(Dialog)
		self.PasswordLineEdit.setObjectName("PasswordLineEdit")
		self.PasswordLineEdit.setGeometry(QRect(40, 90, 192, 33))
		self.CompactSpinBox = CompactSpinBox(Dialog)
		self.CompactSpinBox.setObjectName("CompactSpinBox")
		self.CompactSpinBox.setGeometry(QRect(70, 140, 68, 33))
		self.PrimaryDropDownPushButton = PrimaryDropDownPushButton(Dialog)
		self.PrimaryDropDownPushButton.setObjectName("PrimaryDropDownPushButton")
		self.PrimaryDropDownPushButton.setGeometry(QRect(130, 150, 267, 30))
		self.PillPushButton = PillPushButton(Dialog)
		self.PillPushButton.setObjectName("PillPushButton")
		self.PillPushButton.setGeometry(QRect(50, 20, 133, 28))
		self.IconWidget = IconWidget(Dialog)
		self.IconWidget.setObjectName("IconWidget")
		self.IconWidget.setGeometry(QRect(30, 60, 16, 16))

		self.retranslateUi(Dialog)
		self.buttonBox.accepted.connect(Dialog.accept)
		self.buttonBox.rejected.connect(Dialog.reject)

		QMetaObject.connectSlotsByName(Dialog)

	# setupUi

	def retranslateUi(self, Dialog):
		Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "Dialog", None))
		self.PrimaryDropDownPushButton.setText(
			QCoreApplication.translate("Dialog", "Primary drop down push button", None)
		)
		self.PillPushButton.setText(
			QCoreApplication.translate("Dialog", "Pill push button", None)
		)

	# retranslateUi


if __name__ == "__main__":
	import sys

	app = QApplication(sys.argv)
	Dialog = QDialog()
	ui = Ui_Dialog()
	ui.setupUi(Dialog)
	Dialog.show()
	sys.exit(app.exec())
