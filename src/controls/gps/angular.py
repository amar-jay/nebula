import math


def compute_angles(target_pixel, image_shape, focal_length_px):
    """
    target_pixel: (x, y) pixel coordinates of target
    image_shape: (height, width) of the image
    focal_length_px: focal length in pixels
    """
    height, width = image_shape
    cx = width / 2
    cy = height / 2

    # Offset from the image center
    dx = target_pixel[0] - cx
    dy = cy - target_pixel[1]  # Flip y to get positive elevation upwards

    # Calculate angles in radians
    azimuth_rad = math.atan2(dx, focal_length_px)
    elevation_rad = math.atan2(dy, focal_length_px)

    # Convert to degrees
    azimuth_deg = math.degrees(azimuth_rad)
    elevation_deg = math.degrees(elevation_rad)

    return azimuth_deg, elevation_deg


def compute_target_gps(
    drone_gps, drone_altitude, elevation_angle_deg, azimuth_angle_deg
):
    """
    Compute the GPS location (latitude, longitude) of a ground target.

    Parameters:
      drone_gps (tuple): (latitude, longitude) in degrees of the drone.
      drone_altitude (float): Altitude of the drone above ground, in meters.
      elevation_angle_deg (float): Elevation angle from the drone to target, in degrees.
                                   (Negative if target is below the horizon, which is typical for ground targets.)
      azimuth_angle_deg (float): Azimuth angle from the drone to target, in degrees.
                                 (Measured clockwise from north.)

    Assumptions:
      - The target is on the ground (altitude 0).
      - The elevation angle is such that the target lies on the ground.
      - Flat Earth approximations are valid for small distances.
    """
    # Convert angles from degrees to radians
    elevation_rad = math.radians(elevation_angle_deg)
    azimuth_rad = math.radians(azimuth_angle_deg)

    # When the target is on the ground, the horizontal distance (d) from drone's vertical projection to the target is:
    # tan(|elevation|) = drone_altitude / horizontal_distance  => horizontal_distance = drone_altitude / tan(|elevation|)
    # Here we assume elevation_angle_deg is negative for ground targets, so use -elevation_rad.
    if elevation_rad >= 0:
        raise ValueError(
            "For ground targets the elevation angle should be negative (target below horizontal)."
        )

    horizontal_distance = drone_altitude / math.tan(-elevation_rad)

    # Compute north and east offsets using the azimuth angle.
    north_offset = horizontal_distance * math.cos(azimuth_rad)
    east_offset = horizontal_distance * math.sin(azimuth_rad)

    # Approximate conversion factors (meters per degree):
    # why this computation for latitude?
    # Longitude rarely changes that much, however latitude changes relative to its longitude. For better visualization due to the
    # uneven spherical nature of the earth, the latitude differs slightly, however in this context, this fixed constant though not perfect.
    # Its an approximations that fixes that.

    meters_per_deg_lat = 111320  # Roughly meters per degree latitude.
    # Meters per degree longitude vary with latitude:
    current_lat_rad = math.radians(drone_gps[0])
    meters_per_deg_lon = 111320 * math.cos(current_lat_rad)

    # Calculate the new target GPS coordinates.
    target_lat = drone_gps[0] + north_offset / meters_per_deg_lat
    target_lon = drone_gps[1] + east_offset / meters_per_deg_lon

    return (target_lat, target_lon)
