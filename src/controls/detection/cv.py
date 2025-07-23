import cv2
import numpy as np

# NOT USED...


class DetectSpeed:
    def __init__(self) -> None:
        self.orb = cv2.ORB_create()
        self.prev_kp = None
        self.prev_des = None
        pass

    def compute_speed(self, frames, dt=1):
        """
        I assume the color has been converted to COLOR_BGR2GRAY(grayscale)
        """
        if dt < 0:
            raise ValueError("dt must be at greater than 0")
        if not frames or len(frames) == 0:
            raise ValueError(
                "need to capture a number of frames at a particular dt to use."
            )

        x, y = [], []
        for frame in frames:
            # ohh  I can just simply check
            if frame.size(0) != 1:
                raise ValueError(
                    "use gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) to convert image frame to grayscale"
                )

            # ORB on current frame
            kp, des = self.orb.detectAndCompute(frame, None)
            if self.prev_des is None or self.prev_kp is None:
                self.prev_des = des
                self.prev_kp = kp
                continue

            # Match descriptors
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(self.prev_des, des)
            matches = sorted(matches, key=lambda x: x.distance)

            # Compute average pixel displacement
            for m in matches:
                pt1 = self.prev_kp[m.queryIdx].pt
                pt2 = kp[m.trainIdx].pt
                dx = pt2[0] - pt1[0]
                dy = pt2[1] - pt1[1]
                x.append(dx)
                y.append(dy)
            self.prev_des = des
            self.prev_kp = kp

        x_vel = np.mean(x) / dt if x else 0
        y_vel = np.mean(y) / dt if y else 0
        return x_vel, y_vel
