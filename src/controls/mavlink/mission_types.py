import os
import warnings
from typing import Dict, NamedTuple, Tuple

import numpy as np
import yaml


class Waypoint(NamedTuple):
    lat: float
    lon: float
    alt: float
    hold: int
    # relative_to: Tuple[float, float, float] | None
    auto: bool


class FrameData(NamedTuple):
    """Drone data fetched across MAVLink Proxy for image recognition and gps estimation"""

    frame: np.ndarray | None = None
    timestamp: float | None = None
    drone_position: tuple[float, float, float] | None = None
    drone_attitude: tuple[float, float, float] | None = None
    # ground_level: float | None = None
    mode: str = "UNKNOWN"


class ProcessedResult(NamedTuple):
    """Result of frame processing"""

    processed_frame: np.ndarray
    gps_coordinates: Dict[str, Tuple[float, float]]
    pixel_coordinates: Dict[str, Tuple[int, int]]
    timestamp: float


class Config(NamedTuple):
    mavproxy_source: str
    control_address: str
    timeout: float
    video_source: int
    video_output: str
    controller_connection_string: str
    controller_baudrate: int

    def __repr__(self):
        # Collect all attributes and their values
        attrs = [
            ("mavproxy_source", self.mavproxy_source),
            ("control_address", self.control_address),
            ("video_source", self.video_source),
            ("video_output", self.video_output),
            ("controller_connection_string", self.controller_connection_string),
            ("controller_baudrate", self.controller_baudrate),
            ("timeout", self.timeout),
        ]

        # Compute max widths for columns
        col1_width = max(len(name) for name, _ in attrs)
        col2_width = max(len(str(value)) for _, value in attrs)

        # Table header
        table = f"+{'-' * (col1_width + 2)}+{'-' * (col2_width + 2)}+\n"
        table += f"| {'Config'.ljust(col1_width)} | {'Value'.ljust(col2_width)} |\n"
        table += f"+{'-' * (col1_width + 2)}+{'-' * (col2_width + 2)}+\n"

        # Table rows
        for name, value in attrs:
            table += f"| {name.ljust(col1_width)} | {str(value).ljust(col2_width)} |\n"

        # Table footer
        table += f"+{'-' * (col1_width + 2)}+{'-' * (col2_width + 2)}+"

        return table


class GazeboConfig(NamedTuple):
    world: str
    model_name: str
    camera_link: str
    is_simulation: bool

    def __repr__(self):
        return f"GazeboConfig(world={self.world}, model_name={self.model_name}, camera_link={self.camera_link}, is_simulation={self.is_simulation})"


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "config.yaml"
)


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


def get_camera_params():
    # check the config/config.yaml for the camera intrinsics
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except Exception as exc:
        raise ValueError(
            f"Configuration file '{CONFIG_PATH}' is empty or contains no valid YAML content. {exc}"
        ) from exc

    camera_intrinsics = config.get("camera", {})
    if not camera_intrinsics:
        raise ValueError(
            f"Camera configuration not found in YAML config file at '{CONFIG_PATH}'. "
            f"Please add a 'camera:' section with intrinsics and distortion parameters."
        )
    intrinsics = camera_intrinsics.get("intrinsics", None)
    if intrinsics is None:
        raise ValueError(
            f"Missing 'intrinsics' field in camera section of '{CONFIG_PATH}'. "
            f"Please add: camera.intrinsics: [fx, 0, cx, 0, fy, cy, 0, 0, 1] (9 values total)"
        )
    if len(intrinsics) != 9:
        raise ValueError(
            f"Invalid 'camera.intrinsics' in '{CONFIG_PATH}': expected 9 values, got {len(intrinsics)}. "
            f"Format should be: [fx, 0, cx, 0, fy, cy, 0, 0, 1] representing a 3x3 camera matrix"
        )

    distortion = camera_intrinsics.get("distortion", [0, 0, 0, 0, 0])
    if not isinstance(distortion, list) or len(distortion) != 5:
        raise ValueError(
            f"Invalid 'camera.distortion' in '{CONFIG_PATH}': expected list of 5 values, got {distortion}. "
            f"Format should be: [k1, k2, p1, p2, k3] for radial and tangential distortion coefficients"
        )

    return {
        "camera_intrinsics": np.array(intrinsics).reshape(3, 3),
        "distortion": np.array(distortion),
    }


# def get_control_address() -> str:
#     try:
#         with open(CONFIG_PATH, "r", encoding="utf-8") as file:
#             config = yaml.safe_load(file)
#             server_config = config.get("communication", {})
#             if not server_config:
#                 raise ValueError(
#                     f"Server configuration not found in YAML config file at '{CONFIG_PATH}'. "
#                     f"Please add a 'communication:' section to your config.yaml file."
#                 )
#             if "control_address" not in server_config:
#                 raise ValueError(
#                     f"Missing 'control_address' field in communication section of '{CONFIG_PATH}'. "
#                     f"Please add: communication.control_address: 'tcp://<host>:<port>'"
#                 )
#             return server_config["control_address"]
#     except Exception as e:
#         raise ValueError(
#             f"Configuration file '{CONFIG_PATH}' is empty or contains no valid YAML content. \n{e}"
#         ) from e


def get_config() -> Config:
    # check the config/default.yaml for the server configuration
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except Exception as e:
        raise ValueError(
            f"Configuration file '{CONFIG_PATH}' is empty or contains no valid YAML content. \n{e}"
        ) from e

    server_config = config.get("communication", {})
    if not server_config:
        raise ValueError(
            f"Server configuration not found in YAML config file at '{CONFIG_PATH}'. "
            f"Please add a 'communication:' section to your config.yaml file."
        )
    if "control_address" not in server_config or not server_config[
        "control_address"
    ].startswith("tcp://"):
        raise ValueError(
            f"Missing or invalid 'control_address' field in communication section of '{CONFIG_PATH}'. "
            f"Please add: communication.control_address: 'tcp://<host>:<port>'"
        )

    if (
        "mavproxy_source" not in server_config
        or len(server_config["mavproxy_source"].split(":")) < 2
    ):
        print(
            f"Warning: Invalid or missing 'mavproxy_source' in '{CONFIG_PATH}': '{server_config['mavproxy_source']}'. "
            f"Should be in format 'udp:<host>:<port>' or 'tcp:<host>:<port>' or '/dev/tty*'. "
            f"Using default value 'udp:localhost:14550'."
        )

    # print config for debugging
    if "video_source" in server_config:
        if isinstance(server_config["video_source"], str):
            if not (
                server_config["video_source"].startswith("rtsp://")
                or server_config["video_source"].startswith("rtsps://")
            ):
                raise ValueError(
                    f"Invalid string format for 'communication.video_source' in '{CONFIG_PATH}': '{server_config['video_source']}'. "
                    f"String values must be RTSP URLs starting with 'rtsp://', or use integer device ID (0, 1, 2, etc.)"
                )
        elif isinstance(server_config["video_source"], int):
            pass
        else:
            raise ValueError(
                f"Invalid type of 'communication.video_source' in '{CONFIG_PATH}': '{server_config['video_source']}' (type: {type(server_config['video_source']).__name__}). "
                f"Must be either an integer device ID (0, 1, 2, etc.) or rtsp://<host>:<port>"
            )
    else:
        raise ValueError(
            f"Invalid 'communication.video_source' in '{CONFIG_PATH}': '{server_config['video_source']}' (type: {type(server_config['video_source']).__name__}). "
            f"Must be either an integer device ID (0, 1, 2, etc.) or rtsp://<host>:<port>"
        )

    if "video_output" in server_config:
        if not (
            server_config["video_output"].startswith("rtsp://")
            or server_config["video_output"].startswith("rtsps://")
            or server_config["video_output"].startswith("tcp://")
            or server_config["video_output"].startswith("ipc://")
        ):
            raise ValueError(
                f"Invalid string format for 'communication.video_output' in '{CONFIG_PATH}': '{server_config['video_output']}'. "
                f"Value must be RTSP URLs starting with 'rtsp://' or 'rtsps://' or 'tcp://' or 'ipc://'."
            )
    else:
        raise ValueError(
            f"Invalid type of 'communication.video_output' in '{CONFIG_PATH}': '{server_config['video_output']}' (type: {type(server_config['video_output']).__name__}). "
            f"Value must be RTSP URLs starting with 'rtsp://' or 'rtsps://' or 'tcp://' or 'ipc://'."
        )

    # get controller connection string and baudrate
    if "controller_connection_string" not in server_config:
        print(
            f"Warning: 'controller_connection_string' not defined in '{CONFIG_PATH}' under communication section.\n"
            f"Controller will not be used. To enable, add: communication.controller_connection_string: '/dev/tty*'"
        )
    elif not server_config["controller_connection_string"].startswith("/dev/tty"):
        raise ValueError(
            f"Invalid 'communication.controller_connection_string' in '{CONFIG_PATH}': '{server_config['controller_connection_string']}'. "
            f"Must start with '/dev/tty' (for serial)"
            f"Examples: '/dev/ttyUSB0', '/dev/ttyACM0'"
        )

    # Validate timeout value
    timeout = server_config.get("zmq_timeout", 1000)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError(
            f"Invalid 'communication.zmq_timeout' in '{CONFIG_PATH}': '{timeout}' (type: {type(timeout).__name__}). "
            f"Must be a positive number (milliseconds), e.g., 1000"
        )

    return Config(
        mavproxy_source=server_config["mavproxy_source"],
        control_address=server_config["control_address"],
        timeout=timeout,
        video_source=server_config["video_source"],
        video_output=server_config["video_output"],
        controller_connection_string=server_config.get("controller_connection_string"),
        controller_baudrate=server_config.get("controller_baudrate", 9600),
    )


def get_gazebo_config() -> GazeboConfig:
    # check the config/default.yaml for the gazebo configuration
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except Exception as e:
        raise ValueError(
            f"Configuration file '{CONFIG_PATH}' error or contains no valid YAML content that could be loaded. {e}"
        ) from e

    gazebo_config = config.get("simulation", {})
    if not gazebo_config:
        raise ValueError(
            f"Simulation configuration not found in YAML config file at '{CONFIG_PATH}'. "
            f"Please add a 'simulation:' section with world, model_name, and camera_link parameters."
        )

    world = gazebo_config.get("world", "delivery_runway")
    model_name = gazebo_config.get("model_name", "iris_with_stationary_gimbal")
    camera_link = gazebo_config.get("camera_link", "tilt_link")
    is_simulation = gazebo_config.get("enabled", False)

    # Validate that required fields are strings and not empty
    if not isinstance(world, str) or not world.strip():
        raise ValueError(
            f"Invalid 'simulation.world' in '{CONFIG_PATH}': '{world}'. "
            f"Must be a non-empty string, e.g., 'delivery_runway'"
        )

    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError(
            f"Invalid 'simulation.model_name' in '{CONFIG_PATH}': '{model_name}'. "
            f"Must be a non-empty string, e.g., 'iris_with_stationary_gimbal'"
        )

    if not isinstance(camera_link, str) or not camera_link.strip():
        raise ValueError(
            f"Invalid 'simulation.camera_link' in '{CONFIG_PATH}': '{camera_link}'. "
            f"Must be a non-empty string, e.g., 'tilt_link'"
        )

    return GazeboConfig(
        world=world.strip(),
        model_name=model_name.strip(),
        camera_link=camera_link.strip(),
        is_simulation=is_simulation,
    )
