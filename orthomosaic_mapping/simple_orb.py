import cv2
import numpy as np
import os

img = cv2.imread('./simple_image.jpg')
if img is None:
    print("Error: Image not found or path is incorrect.")
    exit()
img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

################ORBSLAM############################

orb = cv2.ORB_create(nfeatures=1000)
keypoints_orb, descriptors = orb.detectAndCompute(img, None)

output_img = cv2.drawKeypoints(img, keypoints_orb, None, color=(255, 0, 255))
cv2.imshow("orb_output", output_img)

#################SIFT###########################

sift = cv2.SIFT_create()

keypoints = sift.detect(img_gray, None)
cv2.imshow("sift_output", cv2.drawKeypoints(img, keypoints, None, (255, 0, 255)))

# TODO: why the error ?? 
# Says so in docs https://docs.opencv.org/3.4/d5/df7/classcv_1_1xfeatures2d_1_1SURF.html
# Traceback (most recent call last):
#   File "<FILE>", line 27, in <module>

#     surf = cv2.xfeatures2d.SURF_create()
# AttributeError: module 'cv2' has no attribute 'xfeatures2d'


##################SURF##########################
# surf = cv2.cv.xfeatures2d.SURF.create()

# keypoints = surf.detect(img_gray, None)
# cv2.imshow("suft_output", cv2.drawKeypoints(img, keypoints, None, (255, 0, 255)))



cv2.waitKey(0)
cv2.destroyAllWindows()

