import io, sys

from PySide6 import QtWebEngineWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import QApplication, QPushButton
import folium
from folium.plugins import MousePosition

# Make Icon
from PIL import Image
import base64


def image_to_base64(image_path, size=(100, 100)):
	with Image.open(image_path) as img:
		img = img.resize(size)
		if img.mode == "RGBA":
			img = img.convert("RGB")
		buffered = io.BytesIO()
		img.save(buffered, format="JPEG")
		return base64.b64encode(buffered.getvalue()).decode()


def icon_to_base64(image_path):
	with open(image_path, "rb") as image_file:
		return base64.b64encode(image_file.read()).decode()


uav_icon_base64 = icon_to_base64("src/control_station/uifolder/assets/icons/uav.png")
mobileuser_marker_base64 = icon_to_base64(
	"src/control_station/uifolder/assets/icons/mobileuser.png"
)
target_marker_base64 = icon_to_base64(
	"src/control_station/uifolder/assets/icons/target.png"
)
home_icon_base64 = icon_to_base64(
	"src/control_station/uifolder/assets/icons/antenna.png"
)


def custom_code(location, map_variable_name):
	with open("./map_script.js", "r", encoding="utf-8") as f:
		script_file = f.read()
	return script_file % (
		map_variable_name,
		uav_icon_base64,
		target_marker_base64,
		mobileuser_marker_base64,
		home_icon_base64,
		f"{location[0]},{location[1]}",
	)


class MapWidget(QtWebEngineWidgets.QWebEngineView):
	mission = []

	def __init__(self, center_coord, starting_zoom=13):
		super().__init__()
		MapWidget.marker_coord = center_coord
		self.fmap = folium.Map(location=center_coord, zoom_start=starting_zoom)

		# Show mouse position in bottom right
		MousePosition().add_to(self.fmap)

		# store the map to a file
		data = io.BytesIO()
		self.fmap.save("map.html")
		self.fmap.save(data, close_file=False)

		# reading the folium file
		html = data.getvalue().decode()

		# find variable names
		self.map_variable_name = self.find_variable_name(html, "map_")

		# determine scripts indices
		endi = html.rfind("</script>")

		# inject code
		html = (
			html[: endi - 1]
			+ custom_code(center_coord, self.map_variable_name)
			+ html[endi:]
		)
		data.seek(0)
		data.write(html.encode())

		# To Get Java Script Console Messages
		self.map_page = self.WebEnginePage()
		self.setPage(self.map_page)

		# To Display the Map
		self.resize(800, 600)
		self.setHtml(data.getvalue().decode())

		# A variable that holds if the widget is child of the main window or not
		self.isAttached = True

		# self.loadFinished.connect(self.onLoadFinished)

	def resizeEvent(self, event):
		super().resizeEvent(event)

	class WebEnginePage(QWebEnginePage):
		def __init__(self):
			super().__init__()
			self.markers_pos = []

		def javaScriptConsoleMessage(self, level, msg, line, sourceID):
			if msg[0] == "m":
				MapWidget.mission = []
				pairs = msg[1:].split("&")
				for pair in pairs:
					MapWidget.mission.append(list(map(float, pair.split(","))))
				print("mission: ", MapWidget.mission)
			else:
				self.markers_pos = msg.split(",")
				print(msg)

	def find_variable_name(self, html, name_start):
		variable_pattern = "var "
		pattern = variable_pattern + name_start

		starting_index = html.find(pattern) + len(variable_pattern)
		tmp_html = html[starting_index:]
		ending_index = tmp_html.find(" =") + starting_index

		return html[starting_index:ending_index]


if __name__ == "__main__":
	# create variables
	istanbulhavalimani = [41.27442, 28.727317]

	# Display the Window
	app = QApplication([])
	widget = MapWidget(istanbulhavalimani)
	widget.show()

	sys.exit(app.exec())
