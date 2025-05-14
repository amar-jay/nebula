Can you build a ZeroMQ-based server for a drone system that uses pymavlink? The server should manage the following components:

1. Camera Stream Management

- Stream the raw camera feed frames through a ZeroMQ publisher.
- Stream the processed camera feed through a ZeroMQ publisher.


2. Hook Controller System (for package delivery)

- Implement a drop hook command (to release payload) 
- a raise hook command (to retract the hook).
- Both commands should be ZeroMQ-triggered and acknowledged with telemetry data from the drone.

3. MAVLink Communication Relay

Bridge MAVLink messages from the drone’s serial port into the ZeroMQ message bus.

Forward relevant commands from ZeroMQ clients back into the drone using pymavlink.



4. Mission Command Interface

Include a mission command (e.g., "kamikaze") to send the drone to a specified GPS coordinate at high priority.

Command should be ZeroMQ-triggered and acknowledged with drone telemetry via the same system.




Everything should be modular and asynchronous, with clear message routing and logging.
