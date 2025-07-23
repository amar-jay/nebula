from .mavlink.ardupilot import Waypoint


def create_mission(lat, lon, alt, hold=5):
    mission_coords = [
        # 📦 Scenario 1: Precision Box Scan
        [lat + 0.00004, lon + 0.00004, 25],
        [lat + 0.00004, lon - 0.00004, 25],
        [lat - 0.00004, lon - 0.00004, 20],
        [lat - 0.00004, lon + 0.00004, 20],
        [lat + 0.00003, lon + 0.00003, 15],
        [lat - 0.00003, lon - 0.00003, 15],
        [lat + 0.00001, lon, 10],
        [lat, lon, 5],
        [lat, lon, alt + 10],
        # 🌀 Scenario 2: Spiral Inward Descent
        [lat + 0.00006, lon + 0.00006, 30],
        [lat + 0.00004, lon + 0.00002, 25],
        [lat + 0.00001, lon - 0.00002, 20],
        [lat - 0.00002, lon - 0.00004, 15],
        [lat - 0.00003, lon - 0.00001, 10],
        [lat - 0.00001, lon + 0.00001, 5],
        [lat, lon, 3],
        [lat, lon, alt + 10],
        # 🎯 Scenario 3: Linear Glide Path
        [lat + 0.0001, lon, 40],
        [lat + 0.00007, lon, 30],
        [lat + 0.00004, lon, 20],
        [lat + 0.00002, lon, 10],
        [lat + 0.000005, lon, 5],
        [lat, lon, 2],
        [lat, lon, alt + 10],
        # 🔁 Scenario 4: Yaw Scan Hold
        [lat, lon + 0.00004, 15],
        [lat + 0.00003, lon + 0.00003, 15],
        [lat + 0.00004, lon, 15],
        [lat + 0.00003, lon - 0.00003, 15],
        [lat, lon - 0.00004, 15],
        [lat - 0.00003, lon - 0.00003, 15],
        [lat - 0.00004, lon, 15],
        [lat - 0.00003, lon + 0.00003, 15],
        [lat, lon, 10],
        [lat, lon, alt + 10],
        # 📡 Scenario 5: Gimbal-centric Radial Scan
        [lat, lon + 0.00006, 20],
        [lat + 0.00004, lon + 0.00004, 20],
        [lat + 0.00006, lon, 20],
        [lat + 0.00004, lon - 0.00004, 20],
        [lat, lon - 0.00006, 20],
        [lat - 0.00004, lon - 0.00004, 20],
        [lat - 0.00006, lon, 20],
        [lat - 0.00004, lon + 0.00004, 20],
        [lat, lon, 10],
        [lat, lon, alt + 10],
    ]

    return [Waypoint(lat, lon, alt, hold) for lat, lon, alt in mission_coords]
