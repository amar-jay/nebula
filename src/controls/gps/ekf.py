import numpy as np
from filterpy.kalman import ExtendedKalmanFilter


# -----------------------------
# Define the process (state transition) model
# -----------------------------
def fx(x, dt):
    """
    State transition function for constant velocity model.

    Args:
        x : np.array
            State vector [lat, lon, alt, v_lat, v_lon, v_alt].
        dt : float
            Time step (seconds).

    Returns:
        np.array
            Predicted state after dt seconds.
    """
    # Construct state-transition matrix for constant velocity.
    F = np.array(
        [
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1],
        ]
    )
    return F @ x


def F_jacobian(dt):
    """
    Jacobian of the state transition function.
    This is constant for the simple constant velocity model.
    """
    return np.array(
        [
            [1, 0, 0, dt, 0, 0],
            [0, 1, 0, 0, dt, 0],
            [0, 0, 1, 0, 0, dt],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1],
        ]
    )


# -----------------------------
# Define the measurement model
# -----------------------------
def hx(x, drone_pos=None):
    """
    Measurement function.

    For this example, we assume the measurement is the noisy
    target GPS position computed by your model.

    Args:
        x : np.array
            State vector [lat, lon, alt, v_lat, v_lon, v_alt].
        drone_pos : tuple or None
            Drone's position (lat, lon, alt) if needed; not used in this simple case.

    Returns:
        np.array
            Expected measurement (target GPS position: [lat, lon, alt]).
    """
    # For simplicity, we assume the measurement model extracts the position from the state.
    return x[:3]


def H_jacobian(x):
    """
    Jacobian of the measurement function hx.

    Since hx(x) = [lat, lon, alt] is linear in the state components,
    the Jacobian is simply: [I_3, 0_3].

    Args:
        x : np.array
            Current state vector.

    """

    H = np.zeros((3, 6))
    H[0, 0] = 1
    H[1, 1] = 1
    H[2, 2] = 1
    # print(np.hstack((np.eye(3), np.zeros(shape=(3,3)))))
    return H


# -----------------------------
# Set up the Extended Kalman Filter
# -----------------------------
def setup_ekf(initial_state, process_var, measurement_var):
    """
    Initializes and returns an Extended Kalman Filter.

    Args:
        initial_state : np.array
            Initial state vector [lat, lon, alt, v_lat, v_lon, v_alt].
        process_var : float
            Process noise variance (used for Q).
        measurement_var : float
            Measurement noise variance (used for R).

    Returns:
        ekf : ExtendedKalmanFilter object.
    """
    ekf = ExtendedKalmanFilter(dim_x=6, dim_z=3)

    # Initialize state and covariance
    ekf.x = initial_state.copy()
    ekf.P = np.eye(6) * 1.0  # Adjust initial uncertainty as needed.

    # Process noise covariance Q
    ekf.Q = np.eye(6) * process_var

    # Measurement noise covariance R
    ekf.R = np.eye(3) * measurement_var

    return ekf


def predict_ekf(ekf, dt):
    """
    Perform the EKF prediction step manually.

    Args:
        ekf: ExtendedKalmanFilter object.
        dt: time step.
    """
    # Compute the Jacobian (state transition matrix)
    F = F_jacobian(dt)
    # Update the state using the non-linear transition function
    ekf.x = fx(ekf.x, dt)
    # Propagate the covariance
    ekf.P = F @ ekf.P @ F.T + ekf.Q


class GeoFilter:
    def __init__(self, measurement_var=1e-2, process_var=1e-4, dt=1.0) -> None:
        self.measurement_var = measurement_var
        self.process_var = process_var
        self.dt = dt
        self.initial_state = None
        self.ekf = None

    @property
    def velocity(self):
        if self.ekf is not None:
            return tuple(self.ekf.x[3:])
        return None

    def compute_gps(self, drone_pos, drone_vel=np.zeros(3)):
        # check if the input is a tuple or numpy array
        if isinstance(drone_pos, tuple):
            drone_pos = np.array(drone_pos)
        if isinstance(drone_vel, tuple):
            drone_vel = np.array(drone_vel)

        if len(drone_pos) != 3 or len(drone_vel) != 3:
            raise ValueError(
                f"Input drone_pos={drone_pos} must be (lat, lon, alt), and drone_vel must be (v_lat, v_lon, v_alt)"
            )

        # Initialize EKF on first call
        if self.initial_state is None or self.ekf is None:
            self.initial_state = np.hstack((drone_pos, drone_vel))
            self.ekf = setup_ekf(
                self.initial_state, self.process_var, self.measurement_var
            )

        # Predict step
        predict_ekf(self.ekf, self.dt)

        # Measurement update
        z = np.array(drone_pos)
        self.ekf.update(z, HJacobian=H_jacobian, Hx=hx)

        # Return the estimated position (lat, lon, alt)
        state = self.ekf.x.copy()

        return tuple(state[:3])  # ekf_lat, ekf_lon, ekf_alt
