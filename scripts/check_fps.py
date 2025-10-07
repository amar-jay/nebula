import time

import cv2
import numpy as np

from src.controls.mavlink import gz

is_sim = input("Is it a simulation test (y/N)?")

if is_sim == "y" or is_sim == "Y":
    cap = gz.GazeboVideoCapture()
else:
    cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Failed to open stream! Check sender or pipeline.")
    exit()

list_of_frames = []
frames_per_second = 0
print("Wait might take a while")
now = time.time()
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame. Is the stream active?")
        break

    frames_per_second += 1
    if time.time() - now > 1:
        list_of_frames.append(frames_per_second)
        frames_per_second = 0
        now = time.time()
    if len(list_of_frames) == 20:
        mean = np.array(list_of_frames).mean()
        print("The average fps is ", mean)
        break
    cv2.imshow("Stream", frame)
    if 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
