from pymavlink import mavutil
from src.controls.mavlink.ardupilot import ArdupilotConnection

# Connect to the TCP bridge
connection = ArdupilotConnection(
	"tcp:127.0.0.1:16550"
)
# connection = mavutil.mavlink_connection("tcp:127.0.0.1:16550")

# Now you can send/receive MAVLink messages as usual
# print("Waiting for heartbeat...")
# connection.wait_heartbeat()
print("Heartbeat received!")

# Example: Request vehicle parameters
# connection.mav.param_request_list_send(
#     connection.target_system, connection.target_component
# )

connection.arm()
connection.takeoff(10)
lat, lon, alt = connection.get_current_gps_location()
print(f"Current GPS Location: lat={lat}, lon={lon}, alt={alt}")
# Read and print parameters
# while True:
#     msg = connection.recv_match(type='PARAM_VALUE', blocking=True)
#     if msg:
#         print(f"Parameter: {msg.param_id} = {msg.param_value}")