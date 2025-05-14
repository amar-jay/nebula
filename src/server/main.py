import sys
import zmq

def main():
    # Initialize ZeroMQ context
    context = zmq.Context()

    # Initialize communication
    communication = Communication(context)

    # Initialize drone controller
    drone_controller = DroneController(communication)

    # Initialize simulation interfaces
    gazebo_interface = GazeboInterface()
    ardupilot_interface = ArduPilotInterface()

    # Initialize GUI
    gui = GUI(drone_controller, communication)

    # Start the GUI
    gui.run()

if __name__ == "__main__":
    main()