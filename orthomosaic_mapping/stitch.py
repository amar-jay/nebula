import cv2 as cv
import matplotlib.pyplot as plt
import numpy as np
import cv2 

frame_ids = [10, 20, 40]

img_1 = None
for idx in frame_ids:
    img_2 = cv2.imread(f'frame_{idx}.jpg')
    if img_1 is None:
        img_1 = img_2
        continue

    img1 = cv2.cvtColor(img_1,cv2.COLOR_BGR2GRAY)
    # plt.imshow(img1)
    # plt.show()
    img2 = cv2.cvtColor(img_2,cv2.COLOR_BGR2GRAY)
    # plt.imshow(img2)
    # plt.show()

    sift = cv2.SIFT_create() 
    keypoints_1, descriptors_1 = sift.detectAndCompute(img1,None)
    keypoints_2, descriptors_2 = sift.detectAndCompute(img2,None)

    bf = cv2.BFMatcher()

    matches = bf.knnMatch(descriptors_1,descriptors_2, k=2)

    # ratio test
    good = []
    for m in matches:
        if (m[0].distance < 0.5*m[1].distance):
            good.append(m)
    matches = np.asarray(good)


    if (len(matches[:,0]) >= 4):
        src = np.float32([ keypoints_1[m.queryIdx].pt for m in matches[:,0] ]).reshape(-1,1,2)
        dst = np.float32([ keypoints_2[m.trainIdx].pt for m in matches[:,0] ]).reshape(-1,1,2)
        H, masked = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    else:
        raise AssertionError('Can’t find enough keypoints.')

    img_1 = cv2.warpPerspective(img_1,H,((img_1.shape[1] + img_2.shape[1]), int(1.2*img_2.shape[0]))) #wraped image
    img_1[0:img_2.shape[0], 0:img_2.shape[1]] = img_2 #stitched image

    gray = cv2.cvtColor(img_1, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)

    # Find contours of the non-black region
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # plt.imshow(img_1)
    # plt.show()
    # Find bounding box around the stitched content
    x, y, w, h = cv2.boundingRect(contours[0])

    # print(x, y, w, h)
    # Crop the result
    img_1 = img_1[:, x:x+w]

cv2.imwrite('output3.jpg',img_1)
plt.imshow(img_1)
plt.show()