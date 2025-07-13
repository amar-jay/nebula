import base64
import io
import sys
import time

import folium
from folium.plugins import MousePosition

# Make Icon
from PIL import Image
from PySide6 import QtWebEngineWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import QApplication, QPushButton


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


uav_icon_base64 = icon_to_base64("src/new_control_station/assets/images/drone.png")
mobileuser_marker_base64 = icon_to_base64(
    "src/new_control_station/assets/images/mobileuser.png"
)
target_marker_base64 = icon_to_base64(
    "src/new_control_station/assets/images/target.png"
)
home_icon_base64 = icon_to_base64("src/new_control_station/assets/images/home.png")
kamikaze_icon_base64 = icon_to_base64("src/new_control_station/assets/images/kamikaze.png")


def custom_code(location, map_variable_name):
    with open(
        "src/new_control_station/src/map/map_script.js", "r", encoding="utf-8"
    ) as f:
        script_file = f.read()
    return script_file % (
        map_variable_name,
        uav_icon_base64,
        target_marker_base64,
        mobileuser_marker_base64,
        kamikaze_icon_base64,
        home_icon_base64,
        f"{location[0]},{location[1]}",
    )


class WebEnginePage(QWebEnginePage):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def javaScriptConsoleMessage(self, level, msg, line, sourceID):
        if msg[0] == "m":
            self.parent.clear_mission_fn()
            pairs = msg[1:].split("&")
            for i, pair in enumerate(pairs):
                waypoint = list(map(float, pair.split(",")))
                self.parent.update_mission_fn(i + 1, waypoint[0], waypoint[1], 10)
                # self.parent.mission.append(list(map(float, pair.split(","))))
        if msg[0] == "p":  # single marker point
            markers_pos = msg[1:].split(",")
            self.parent.markers_pos = list(map(float, markers_pos))
            self.parent.update_pos_fn(
                self.parent.markers_pos[0], self.parent.markers_pos[1]
            )
            print(msg)
        else:
            print("JavaScript Console Message(Error):", msg)


class MapWidget(QtWebEngineWidgets.QWebEngineView):
    def __init__(self, center_coord, starting_zoom=20):
        super().__init__()
        MAPBOX_TOKEN = "sk.eyJ1IjoiYW1hcmpheSIsImEiOiJjbWI1bzVkcnkwMGlqMmtzMnBrcmJvb2thIn0.Y0JIq8H_w522Dh4H_gWj0Q"
        # NOTE: WHILE HARDCODING ENVIRONMENT VARIABLES IS NOT RECOMMENDED, IT IS
        # DONE HERE FOR CONVENIENCE SO THAT MY PEERS CAN RUN THE CODE WITHOUT HASSLE.

        mapbox_tiles = (
            f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/512/{{z}}/{{x}}/{{y}}@2x"
            f"?access_token={MAPBOX_TOKEN}"
        )
        satellite_tiles = (
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/"
            "tile/{z}/{y}/{x}"
        )

        self.fmap = folium.Map(
            location=[41.27442, 28.727317],  # center_coord,
            tiles=mapbox_tiles,
            attr="Mapbox Satellite",
            # attr="Esri",
            max_zoom=22,
            zoom_start=starting_zoom,
            # scrollWheelZoom=True,
            # tiles='OpenStreetMap'
        )
        self.zoom_start = starting_zoom

        # Show mouse position in bottom right
        MousePosition().add_to(self.fmap)

        # store the map to a file
        data = io.BytesIO()
        self.fmap.save("map.html")
        self.fmap.save(data, close_file=False)

        self.markers_pos = []
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
        self.map_page = WebEnginePage(parent=self)
        self.setPage(self.map_page)

        # To Display the Map
        self.resize(800, 600)
        self.setHtml(data.getvalue().decode())

        # A variable that holds if the widget is child of the main window or not
        self.isAttached = True
        self.update_mission_fn = None
        self.clear_mission_fn = None
        self.update_pos_fn = None

        # self.loadFinished.connect(self.onLoadFinished)

    def __del__(self):
        del self.map_page

    def addMissionCallback(self, fn):
        self.update_mission_fn = fn

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def clearMissionCallback(self, fn):
        self.clear_mission_fn = fn

    def addPositionCallback(self, fn):
        self.update_pos_fn = fn

    def set_marker(self, lat, lon):
        return self.page().runJavaScript(
            f"var homeMarker = L.marker({[lat + 1, lon + 1]}).addTo(map); map.setView({[lat, lon]}, {self.zoom_start});"
        )

    def set_drone_marker(self, lat, lon):
        return self.page().runJavaScript(f"updateUavMarker({[lat, lon]});")

    def set_kamikaze_marker(
        self, lat, lon
    ):  # TODO: set the kamikaze marker later for now it is same as drone marker
        return self.page().runJavaScript(f"updateKamikazeMarker({[lat, lon]});")

    def set_target_marker(self, lat, lon):
        return self.page().runJavaScript(f"updateTargetMarker({[lat, lon]});")

    def set_home_marker(self, lat, lon):
        print(f"Setting home marker at: {lat}, {lon}")
        return self.page().runJavaScript(
            f"var homeMarker = L.marker({[lat, lon]},{{icon: homeIcon,}},).addTo(map); map.setView({[lat, lon]}, {self.zoom_start});"
        )

    def get_markers_pos(self):
        def process_result(_):
            return self.markers_pos

        return self.page().runJavaScript("setMission('ddd')", process_result)

    def get_mission(self):
        return self.page().runJavaScript("setMission('ddd')")

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
