# Video Streamer

Simple Go video streaming server supporting H264 over RTSP and UDP protocols.

## Quick Start

1. Write to `camera_stream.h264` file using `ffmpeg`:
```bash
python video_writer.py
```

2. Start the server:
```bash
make build
./nebula-video-streamer --help
```

3. Stream the video:
```bash
ffplay -loglevel verbose rtsps://localhost:8554/
```


## Service Management
**Install Service**
```bash
make service-install
```
**Start Service**
```bash
make service-start
```
**Stop Service**
```bash
make service-stop
```
**Check Service Status**
```bash
make service-status
```
**View Service Logs**
```bash
make service-logs
```
