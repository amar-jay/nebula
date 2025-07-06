import os
import sys

from PySide6.QtCore import QLocale, QRect, Qt, QTranslator
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (
    FluentTranslator,
    SplitTitleBar,
    Theme,
    isDarkTheme,
    setTheme,
    setThemeColor,
)

from .Ui_LoginWindow import Ui_Form, get_asset


def isWin11():
    return sys.platform == "win32" and sys.getwindowsversion().build >= 22000


if isWin11():
    from qframelesswindow import AcrylicWindow as Window
else:
    from qframelesswindow import FramelessWindow as Window


class LoginWindow(Window, Ui_Form):
    def __init__(self, mainWindow=Window()):
        super().__init__()
        self.setupUi(self)
        setTheme(Theme.DARK)
        setThemeColor("#28afe9")

        self.setTitleBar(SplitTitleBar(self))
        self.titleBar.raise_()

        self.label.setScaledContents(False)
        self.setWindowTitle("Nebula Control Station")
        self.setWindowIcon(QIcon(get_asset("images/logo.png")))
        self.resize(1000, 650)

        self.windowEffect.setMicaEffect(self.winId(), isDarkMode=isDarkTheme())
        if not isWin11():
            color = QColor(25, 33, 42) if isDarkTheme() else QColor(240, 244, 249)
            self.setStyleSheet(f"LoginWindow{{background: {color.name()}}}")

        self.titleBar.titleLabel.setStyleSheet(
            """
            QLabel{
                background: transparent;
                font: 15px 'Segoe UI';
                padding: 0 4px;
                color: white
            }
        """
        )

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.mainWindow = mainWindow
        # on click on button, change the interface
        self.pushButton.clicked.connect(self.onLoginButtonClicked)

    def onLoginButtonClicked(self):
        """on click on button, change the interface"""
        # check email and password
        email = self.lineEdit_3.text()
        password = self.lineEdit_4.text()
        if email == "admin@nebula.com" and password == "password":
            self.hide()
            self.mainWindow.show()
        else:
            # change line within stylesheet of border: to red
            self.lineEdit_3.setStyleSheet(
                self.lineEdit_3.styleSheet().replace(
                    "border-bottom: 1px solid rgba(0, 0, 0, 100);",
                    "border-bottom: 2px solid red;",
                )
            )
            self.lineEdit_4.setStyleSheet(
                self.lineEdit_4.styleSheet().replace(
                    "border-bottom: 1px solid rgba(0, 0, 0, 100);",
                    "border-bottom: 2px solid red;",
                )
            )

    def resizeEvent(self, e):
        super().resizeEvent(e)
        pixmap = QPixmap(get_asset("images/placeholder.png")).scaled(
            self.label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        self.label.setPixmap(pixmap)

    def systemTitleBarRect(self, size):
        """Returns the system title bar rect, only works for macOS"""
        return QRect(size.width() - 75, 0, 75, size.height())


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Internationalization
    # translator = FluentTranslator(QLocale())
    # app.installTranslator(translator)

    w = LoginWindow()
    w.show()
    app.exec()
