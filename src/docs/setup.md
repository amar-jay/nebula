# Setup Instructions for Drone Control System

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- Python 3.7 or higher
- pip (Python package installer)
- ZeroMQ
- Gazebo
- ArduPilot
- OpenCV (for machine learning functionalities)
- NumPy
- SciPy
- scikit-learn (for machine learning functionalities)

## Installation Steps

1. **Clone the Repository**

   Clone the project repository from GitHub:

   ```
   git clone https://github.com/yourusername/drone-control-system.git
   cd drone-control-system
   ```

2. **Create a Virtual Environment**

   It is recommended to create a virtual environment to manage dependencies:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**

   Install the required Python packages using pip:

   ```
   pip install -r requirements.txt
   ```

4. **Setup Gazebo and ArduPilot**

   Follow the official documentation for [Gazebo](http://gazebosim.org/) and [ArduPilot](https://ardupilot.org/) to install and configure them on your system.

5. **Configure the Application**

   Modify the configuration files located in the `config` directory as needed. The `default.yaml` file contains general settings, while `simulation.yaml` is specific to the simulation environment.

6. **Run the Application**

   To start the control station, run the following command:

   ```
   python src/main.py
   ```

7. **Testing**

   You can run the unit tests to ensure everything is working correctly:

   ```
   python -m unittest discover -s tests
   ```

## Additional Notes

- Ensure that the necessary permissions are granted for accessing hardware components if you are using a real drone.
- For machine learning functionalities, you may need to train the models using the `training.py` script in the `ml` directory.
- Refer to the `docs/api.md` for detailed API documentation and usage examples.

## Troubleshooting

If you encounter any issues during setup, please check the following:

- Ensure all dependencies are installed correctly.
- Verify that Gazebo and ArduPilot are configured properly.
- Check the logs for any error messages that may indicate what went wrong.

For further assistance, consider reaching out to the community or checking the project's GitHub issues page.