from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QTimer
import cv2
import sys


class CameraDisplay(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Camera Display")

		self.scale = 0.5  # Scale factor for display

		# Get camera dimensions
		self.capture = cv2.VideoCapture(0)
		ret, frame = self.capture.read()
		if ret:
			self.orig_height, self.orig_width, self.channels = frame.shape
		else:
			self.orig_width, self.orig_height, self.channels = 1280, 720, 3  # Default

		# Calculate display dimensions
		self.disp_width = int(self.orig_width * self.scale)
		self.disp_height = int(self.orig_height * self.scale)

		# Set window size
		self.setGeometry(100, 100, self.disp_width, self.disp_height)

		# Create and position the label that will hold the video
		self.label = QLabel(self)
		self.label.setGeometry(0, 0, self.disp_width, self.disp_height)

		# Start the timer to update frames
		self.timer = QTimer()
		self.timer.timeout.connect(self.update_frame)
		self.timer.start(30)  # Update frame every 30 ms

		self.show()

	def update_frame(self):
		ret, frame = self.capture.read()
		if ret:
			# First convert color space
			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

			# Then resize the frame
			frame = cv2.resize(frame, (self.disp_width, self.disp_height))

			# Calculate bytes per line based on the resized image
			bytes_per_line = self.channels * self.disp_width

			# Create QImage with the resized data
			q_img = QImage(
				frame.data,
				self.disp_width,
				self.disp_height,
				bytes_per_line,
				QImage.Format_RGB888,
			)

			self.label.setPixmap(QPixmap.fromImage(q_img))

	# def closeEvent(self, event):
	#     self.capture.release()
	#     event.accept()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = CameraDisplay()
	sys.exit(app.exec())
