import os
import warnings
from dataclasses import dataclass
from typing import Any, Dict, NamedTuple, Tuple

import numpy as np
import yaml


class Waypoint(NamedTuple):
    lat: float
    lon: float
    alt: float
    hold: int
    # relative_to: Tuple[float, float, float] | None
    auto: bool


@dataclass
class FrameData:
    """Drone data fetched across MAVLink Proxy for image recognition and gps estimation"""

    frame: np.ndarray | None = None
    timestamp: float | None = None
    drone_position: tuple[float, float, float] | None = None
    drone_attitude: tuple[float, float, float] | None = None
    ground_level: float | None = None
    mode: str = "UNKNOWN"


@dataclass
class ProcessedResult:
    """Result of frame processing"""

    processed_frame: np.ndarray
    gps_coordinates: Dict[str, Tuple[float, float]]
    pixel_coordinates: Dict[str, Tuple[int, int]]
    timestamp: float


@dataclass
class ServerConfig:
    mavproxy_source: str
    mavproxy_dest_host: str
    mavproxy_dest_port: int
    control_address: str
    timeout: float
    video_source: int
    sandwich_video_pipe: str
    controller_connection_string: str
    controller_baudrate: int
    """Configuration for the server, including MAVLink source, control address, and video source."""

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self):
        return (
            f"ServerConfig(mavproxy_source={self.mavproxy_source}\n"
            f"\tmavproxy_dest_host={self.mavproxy_dest_host},\n"
            f"\tmavproxy_dest_port={self.mavproxy_dest_port},\n"
            f"\tcontrol_address={self.control_address},\n"
            f"\tsandwich_video_pipe={self.sandwich_video_pipe},\n"
            f"\tcontroller_connection_string={self.controller_connection_string},\n"
            f"\tcontroller_baudrate={self.controller_baudrate},\n"
            f"\ttimeout={self.timeout},\n"
            f"\tvideo_source={self.video_source}\n"
            ")"
        )


@dataclass
class GazeboConfig:
    world: str
    model_name: str
    camera_link: str

    def __repr__(self):
        return f"GazeboConfig(world={self.world}, model_name={self.model_name}, camera_link={self.camera_link})"


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


def get_control_address() -> str:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            server_config = config.get("communication", {})
            if not server_config:
                raise ValueError(
                    f"Server configuration not found in YAML config file at '{CONFIG_PATH}'. "
                    f"Please add a 'communication:' section to your config.yaml file."
                )
            if "control_address" not in server_config:
                raise ValueError(
                    f"Missing 'control_address' field in communication section of '{CONFIG_PATH}'. "
                    f"Please add: communication.control_address: 'tcp://<host>:<port>'"
                )
            return server_config["control_address"]
    except Exception as e:
        raise ValueError(
            f"Configuration file '{CONFIG_PATH}' is empty or contains no valid YAML content. \n{e}"
        ) from e


def get_server_config() -> ServerConfig:
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
    if "control_address" not in server_config:
        raise ValueError(
            f"Missing 'control_address' field in communication section of '{CONFIG_PATH}'. "
            f"Please add: communication.control_address: 'tcp://<host>:<port>'"
        )
    if not server_config["control_address"].startswith("tcp://"):
        raise ValueError(
            f"Invalid 'control_address' format in '{CONFIG_PATH}': '{server_config['control_address']}'. "
            f"Must start with 'tcp://', e.g., 'tcp://0.0.0.0:5556'"
        )

    mavproxy_dest = server_config.get("mavproxy_destination", "")
    if not mavproxy_dest or len(mavproxy_dest.split(":")) != 2:
        raise ValueError(
            f"Invalid or missing 'mavproxy_destination' in '{CONFIG_PATH}': '{mavproxy_dest}'. "
            f"Must be in format '<host>:<port>', e.g., '0.0.0.0:16550'"
        )

    mavproxy_src = server_config.get("mavproxy_source", "")
    if not mavproxy_src or len(mavproxy_src.split(":")) < 2:
        print(
            f"Warning: Invalid or missing 'mavproxy_source' in '{CONFIG_PATH}': '{mavproxy_src}'. "
            f"Should be in format 'udp:<host>:<port>' or 'tcp:<host>:<port>' or '/dev/tty*'. "
            f"Using default value 'udp:localhost:14550'."
        )

    # print config for debugging
    video_source = server_config.get("video_source", 0)
    if isinstance(video_source, str):
        if video_source.startswith("rtsp://") or video_source.startswith("rtsps://"):
            # If video source is a string, it might be an RTSP URL
            video_source = video_source.strip()
            if not video_source or len(video_source) < 10:  # Basic validation
                raise ValueError(
                    f"Invalid RTSP URL in 'communication.video_source' at '{CONFIG_PATH}': '{video_source}'. "
                    f"Must be a valid RTSP URL, e.g., 'rtsp://localhost:8554/stream'"
                )
        else:
            raise ValueError(
                f"Invalid string format for 'communication.video_source' in '{CONFIG_PATH}': '{video_source}'. "
                f"String values must be RTSP URLs starting with 'rtsp://', or use integer device ID (0, 1, 2, etc.)"
            )
    elif isinstance(video_source, int):
        # If video source is an integer, it might be a device ID
        if video_source < 0:
            raise ValueError(
                f"Invalid device ID for 'communication.video_source' in '{CONFIG_PATH}': {video_source}. "
                f"Device ID must be a non-negative integer (0, 1, 2, etc.)"
            )
    else:
        try:
            video_source = int(video_source)
            if video_source < 0:
                raise ValueError(
                    f"Invalid device ID for 'communication.video_source' in '{CONFIG_PATH}': {video_source}. "
                    f"Device ID must be a non-negative integer (0, 1, 2, etc.)"
                )
        except Exception as e:
            raise ValueError(
                f"Invalid 'communication.video_source' in '{CONFIG_PATH}': '{video_source}' (type: {type(video_source).__name__}). "
                f"Must be either an integer device ID (0, 1, 2, etc.) or an RTSP URL string"
            ) from e

    # get controller connection string and baudrate
    controller_connection_string = server_config.get(
        "controller_connection_string", None
    )
    controller_baudrate = server_config.get("controller_baudrate", 9600)
    if controller_connection_string is None:
        print(
            f"Warning: 'controller_connection_string' not defined in '{CONFIG_PATH}' under communication section.\n"
            f"Controller will not be used. To enable, add: communication.controller_connection_string: '/dev/tty*'"
        )
    elif not controller_connection_string.startswith("/dev/tty"):
        raise ValueError(
            f"Invalid 'controller_connection_string' in '{CONFIG_PATH}': '{controller_connection_string}'. "
            f"Must start with '/dev/tty' (for serial)"
            f"Examples: '/dev/ttyUSB0', '/dev/ttyACM0'"
        )

    # get controller baudrate
    if not isinstance(controller_baudrate, int) or controller_baudrate <= 0:
        raise ValueError(
            f"Invalid 'controller_baudrate' in '{CONFIG_PATH}': '{controller_baudrate}'. "
            f"Must be a positive integer (common values: 9600, 57600, 115200). "
            f"Current value type: {type(controller_baudrate).__name__}"
        )

    # Validate timeout value
    timeout = server_config.get("zmq_timeout", 1000)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError(
            f"Invalid 'communication.zmq_timeout' in '{CONFIG_PATH}': '{timeout}' (type: {type(timeout).__name__}). "
            f"Must be a positive number (milliseconds), e.g., 1000"
        )

    return ServerConfig(
        mavproxy_source=server_config.get("mavproxy_source", "udp:localhost:14550"),
        mavproxy_dest_host=server_config.get("mavproxy_destination", "").split(":")[0],
        mavproxy_dest_port=int(
            server_config.get("mavproxy_destination", "").split(":")[1]
        ),
        control_address=server_config.get("control_address", ""),
        timeout=timeout,
        video_source=video_source,
        sandwich_video_pipe=server_config.get(
            "sandwich_video_pipe", "/tmp/camera_stream"
        ),
        controller_connection_string=controller_connection_string,
        controller_baudrate=controller_baudrate,
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
    )


def get_video_urls():
    """Get video URLs from the configuration file."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except Exception as e:
        raise ValueError(
            f"Configuration file not found at '{CONFIG_PATH}'. "
            f"Please create a config.yaml file with video URLs."
        ) from e

    video_urls = config.get("video", {})
    if not video_urls:
        raise ValueError(
            f"No video URLs found in '{CONFIG_PATH}'. "
            f"Please add a 'video_urls:' section with the required URLs."
        )

    raw_video_url = video_urls.get("raw_url")
    processed_video_url = video_urls.get("processed_url")

    # Check if URLs are valid (either RTSP URLs or numeric device IDs)
    def is_valid_video_source(url):
        if isinstance(url, (int, float)):
            return url >= 0
        if isinstance(url, str):
            return (
                url.startswith("rtsp://")
                or url.startswith("rtsps://")
                or (url.isdigit() and int(url) >= 0)
            )
        return False

    if not is_valid_video_source(raw_video_url) or not is_valid_video_source(
        processed_video_url
    ):
        raise ValueError(
            f"Invalid video URLs in '{CONFIG_PATH}': "
            f"Both 'raw_url' and 'processed_url' must be either RTSP URLs (starting with 'rtsp://' or 'rtsps://') "
            f"or numeric device IDs (0, 1, 2, etc.). "
            f"Current values: raw_url='{raw_video_url}', processed_url='{processed_video_url}'"
        )

    return video_urls
