# Clone and set up ArduPilot repository
if [ -d "$HOME/ardupilot" ]; then
    echo "ArduPilot directory already exists. Skipping clone."
    cd $HOME/ardupilot
else
    git clone https://github.com/ArduPilot/ardupilot $HOME/ardupilot
    cd $HOME/ardupilot
    git checkout "Copter-4.5"
fi
git submodule update --init --recursive
