import sys
import os

from PySide6.QtWidgets import QApplication

# Now import and create QApplication
app = QApplication(sys.argv)

# setTheme(Theme.DARK)

from .demo import Window

# app = QApplication(sys.argv)
w = Window()
w.show()
app.exec()
