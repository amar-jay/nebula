import os
import warnings

import numpy as np
import yaml


class Waypoint:
    def __init__(self, lat=0, lon=0, alt=0., hold=3, relative_to=None, auto=True):
        if relative_to is None:
            self.lat = lat
            self.lon = lon
            self.alt = alt
            self.auto = auto
            self.hold = hold
            return
        else:
            self.x = lat - relative_to[0]
            self.y = lon - relative_to[1]
            self.z = alt
            self.hold = hold
            self.auto = auto


def deprecated_method(func):
    """Decorator to mark methods as deprecated"""

    def wrapper(*args, **kwargs):
        warnings.warn(
            f"Call to deprecated method {func.__name__}.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = f"[DEPRECATED] {func.__doc__}"
    return wrapper


def get_camera_intrinsics():
    # check the config/default.yaml for the camera intrinsics
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "config", "default.yaml"
    )
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
        camera_intrinsics = config.get("camera", {})
        if not camera_intrinsics:
            raise ValueError("Camera intrinsics not found in the configuration file.")
        intrinsics = camera_intrinsics.get("intrinsics", None)
        if intrinsics is None:
            raise ValueError("Camera intrinsics not found in the configuration file.")
        if len(intrinsics) != 9:
            raise ValueError("Camera intrinsics should be a list of 9 elements.")
        return {
            "camera_intrinsics": np.array(intrinsics).reshape(3, 3),
            "distortion": np.array(
                camera_intrinsics.get("distortion", [0, 0, 0, 0, 0])
            ),
        }
