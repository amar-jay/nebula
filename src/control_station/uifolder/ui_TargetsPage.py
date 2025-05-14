# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'TargetsPage.ui'
##
## Created by: Qt User Interface Compiler version 6.5.3
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
	QHBoxLayout,
	QLabel,
	QScrollArea,
	QSizePolicy,
	QVBoxLayout,
	QWidget,
)


class Ui_TargetsPage(object):
	def setupUi(self, TargetsPage):
		if not TargetsPage.objectName():
			TargetsPage.setObjectName("TargetsPage")
		TargetsPage.resize(806, 597)
		self.horizontalLayout_2 = QHBoxLayout(TargetsPage)
		self.horizontalLayout_2.setSpacing(50)
		self.horizontalLayout_2.setObjectName("horizontalLayout_2")
		self.horizontalLayout_2.setContentsMargins(30, -1, 30, -1)
		self.verticalLayout = QVBoxLayout()
		self.verticalLayout.setSpacing(5)
		self.verticalLayout.setObjectName("verticalLayout")
		self.label = QLabel(TargetsPage)
		self.label.setObjectName("label")

		self.verticalLayout.addWidget(self.label)

		self.targets_scrollarea = QScrollArea(TargetsPage)
		self.targets_scrollarea.setObjectName("targets_scrollarea")
		self.targets_scrollarea.setWidgetResizable(True)
		self.scrollAreaWidgetContents_3 = QWidget()
		self.scrollAreaWidgetContents_3.setObjectName("scrollAreaWidgetContents_3")
		self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 498, 553))
		self.targets_scrollarea.setWidget(self.scrollAreaWidgetContents_3)

		self.verticalLayout.addWidget(self.targets_scrollarea)

		self.horizontalLayout_2.addLayout(self.verticalLayout)

		self.verticalLayout_2 = QVBoxLayout()
		self.verticalLayout_2.setSpacing(5)
		self.verticalLayout_2.setObjectName("verticalLayout_2")
		self.label_2 = QLabel(TargetsPage)
		self.label_2.setObjectName("label_2")

		self.verticalLayout_2.addWidget(self.label_2)

		self.users_scrollarea = QScrollArea(TargetsPage)
		self.users_scrollarea.setObjectName("users_scrollarea")
		self.users_scrollarea.setWidgetResizable(True)
		self.scrollAreaWidgetContents_4 = QWidget()
		self.scrollAreaWidgetContents_4.setObjectName("scrollAreaWidgetContents_4")
		self.scrollAreaWidgetContents_4.setGeometry(QRect(0, 0, 190, 553))
		self.users_scrollarea.setWidget(self.scrollAreaWidgetContents_4)

		self.verticalLayout_2.addWidget(self.users_scrollarea)

		self.verticalLayout_2.setStretch(1, 4)

		self.horizontalLayout_2.addLayout(self.verticalLayout_2)

		self.horizontalLayout_2.setStretch(0, 4)

		self.retranslateUi(TargetsPage)

		QMetaObject.connectSlotsByName(TargetsPage)

	# setupUi

	def retranslateUi(self, TargetsPage):
		TargetsPage.setWindowTitle(
			QCoreApplication.translate("TargetsPage", "Form", None)
		)
		self.label.setText(
			QCoreApplication.translate("TargetsPage", "Tespit Edilen Hedefler", None)
		)
		self.label_2.setText(
			QCoreApplication.translate(
				"TargetsPage", "Mobil Uygulama Ba\u011flant\u0131lar\u0131", None
			)
		)

	# retranslateUi
