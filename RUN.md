THIS IS THE RUN SEQUENCE FOR THE PROJECT DURING THE TEKNOFEST 2025 COMPETITION

## 1. ON THE DRONE
1. SSH into the drone
```
ssh -X nebula@192.168.144.12
```

2.
	a. Start the telemetry proxy (This will open a console window as well. Leave it open. It proxies from /dev/ttyACM0 to a local udp:127.0.0.1:14550) `mavproxy.py --master=/dev/ttyACM0 --baudrate=57600 --console --out=udp:127.0.0.1:14550`

	b. Start remote server (regularly logs into terminal. If hangs, ctrl+c and re-run) `make remote_server`

Both are started in a tmux session. To run and attach to the session, run the command below. Just go to each window and run the respective commands.

```
make remote
```

## 2. LOCALLY

1. 
a. Start the ground control station (GCS) application

b. Start the telemetry receiver (It does so for three different channels(main drone(), tank, mini drone). This will open a console window as well. Leave it open.)

c. Start the local server (regularly logs into terminal. If hangs, ctrl+c and re-run)

All are started in a tmux session. To run and attach to the session, run the command below. Just go to each window and run the respective commands.

```
make local
```
