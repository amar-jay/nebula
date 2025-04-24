# coding:utf-8
import sys

from PyQt5.QtCore import Qt, QEventLoop, QTimer, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication

from qfluentwidgets import SplashScreen
from PyQt5.QtWidgets import QApplication, QHBoxLayout
from qframelesswindow import FramelessWindow, StandardTitleBar
from interfaces.settings_interface import SettingInterface

class Demo(FramelessWindow):
    def __init__(self):
        super().__init__()
        self.resize(700, 600)
        self.setWindowTitle("Matek")
        self.setWindowIcon(QIcon(":/qfluentwidgets/images/logo.png"))

        # create splash screen and show window
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(102, 102))

        # customize the title bar of splash screen
        # titleBar = StandardTitleBar(self.splashScreen)
        # titleBar.setIcon(self.windowIcon())
        # titleBar.setTitle(self.windowTitle())
        # self.splashScreen.setTitleBar(titleBar)

        self.show()

        # create other subinterfaces
        self.createSubInterface()

        # close splash screen
        self.splashScreen.finish()
        self.setTitleBar(StandardTitleBar(self))
		  self.settingInterface = SettingInterface()
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.addWidget(self.settingInterface)

    def createSubInterface(self):
        loop = QEventLoop(self)
        QTimer.singleShot(3000, loop.quit)
        loop.exec()


if __name__ == "__main__":
    # enable dpi scale
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = Demo()
    w.show()
    app.exec_()
