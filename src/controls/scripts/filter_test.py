import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from detection.angular import compute_angles, compute_target_gps
from gps.ekf import GeoFilter

# Drone GPS position
X = 0  # Latitude
Y = 0  # Longitude
Z = 120  # Altitude in meters

# Example image parameters
image_shape = (720, 1280)  # height, width
focal_length_px = 800  # assume known or computed

# Target pixel (x, y) -- e.g., from object detection
target_pixel = (900, 400)

azimuth, elevation = compute_angles(target_pixel, image_shape, focal_length_px)

# Compute red box position
red_lat, red_lon = compute_target_gps((X, Y), Z, elevation, azimuth)

filter = GeoFilter()

lat, lon, alt = filter.compute_gps(np.array([red_lat, red_lon, 0]))

scale = 1e-10
for _ in range(10000):
    lat += scale * 1e-5 * np.random.randint(0, int(1e5))
    lon += scale * 1e-5 * np.random.randint(0, int(1e5))
    alt += scale * 1e-5 * np.random.randint(0, int(1e5))
    lat, lon, alt = filter.compute_gps(np.array([lat, lon, alt]))

print(
    f"Drone: {X=}, {Y=}, {Z=}\nAngles: {azimuth=} {elevation=}\nTarget: Latitude = {red_lat}, Longitude = {red_lon}\nEstimate: Latitude = {lat}, Longitude = {lon} Altitude={alt}\n"
)
