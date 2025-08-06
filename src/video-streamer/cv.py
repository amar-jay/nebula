import cv2
import time

rtsp_url = "rtsps://127.0.0.1:8554/stream"

cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
	print("❌ Failed to open RTSP stream")
	exit(1)

paused = False
recording = False
writer = None
print("✅ Stream opened. Press 'p' to pause/resume, 'r' to record, 'q' to quit.")

while True:
	if not paused:
		ret, frame = cap.read()
		if not ret:
			print("⚠️ Failed to read frame")
			break

		cv2.imshow("RTSP Stream", frame)

		# Write to file if recording
		if recording:
			writer.write(frame)

	key = cv2.waitKey(1) & 0xFF

	if key == ord("p"):
		paused = not paused
		print("⏸️ Paused" if paused else "▶️ Resumed")

	elif key == ord("r"):
		recording = not recording
		if recording:
			print("⏺️ Started recording")
			fourcc = cv2.VideoWriter_fourcc(*"avc1")  # fallback from X264
			writer = cv2.VideoWriter(
				f"recording_{int(time.time())}.mp4",
				fourcc,
				30.0,
				(frame.shape[1], frame.shape[0]),
			)
		else:
			print("⏹️ Stopped recording")
			writer.release()
			writer = None

	elif key == ord("q"):
		print("👋 Quitting")
		break

cap.release()
if writer:
	writer.release()
cv2.destroyAllWindows()
