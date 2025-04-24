In feature detection mainly using OpenCV, upon detection, two components are given the keypoints and the description the keypoint are significant features are easily distinguisable. This is used in detection of movement across frames. and this movement of these keypoints is what is what is classified as movement. In the case below we are using ORBSLAM, it is a framework primarirly in image recognition and robotics with support for monocular cameras as well in detecting position by relative motion as explained.

```python
import cv2
import numpy as np
import os

print("Current working directory:", os.getcwd())

cv2.namedWindow("output", cv2.WINDOW_NORMAL)

img_1 = cv2.imread('./simple_image.jpg')
if img_1 is None:
    print("Error: Image not found or path is incorrect.")
    exit()

orb = cv2.ORB_create(nfeatures=1000)
keypoints_orb, descriptors = orb.detectAndCompute(img_1, None)

output_img = cv2.drawKeypoints(img_1, keypoints_orb, None, color=(255, 0, 255))
cv2.imshow("output", output_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
``` 


Another alternative is SIFT. SIFT is a much more robust variant of doing so. Unlike ORBSLAM which is a whole SLAM module on its own SIFT is focused on feature matching.

```python
import cv2
import numpy as np
import os

print("Current working directory:", os.getcwd())

cv2.namedWindow("output", cv2.WINDOW_NORMAL)

img = cv2.imread('./simple_image.jpg')
if img_1 is None:
    print("Error: Image not found or path is incorrect.")
    exit()


img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


sift = cv2.SIFT_create()

keypoints = sift.detect(img_gray, None)
cv2.imshow("output", cv2.drawKeypoints(img, keypoints, None, (255, 0, 255)))
cv2.waitKey(0)
cv2.destroyAllWindows()
```

Another alternative too is SUFT but couldn't run it.

The cool thing about these are that they can detect these points even if the images are rotated, scaled, or transformed in some way. So, no matter how the images are aligned, these will still find reliable features.


#### Stictching images

Great! Now let's move on to the stitching images. Imagine you have two images that you want to combine into one larger image, like stitching together two halves of a panorama. How is that done?

As we've see in both SIFT and ORBSLAM, keypoints are generated for unique features within the image. Using these,we can match features between two consecutive images using K-neearest neighbor and filter it based on a lowe's ratio. okay what is lowe's ratio test??

$$
\text{lowe's ratio} = \frac {\text{best closest match}} {\text{second best closest match}} 
$$

Essentially, what the algorithm does is it looks for features in the first image and tries to find similar features in the second image. This is done by comparing the descriptors of the keypoints. Descriptors are like unique fingerprints for each keypoint, capturing the surrounding area’s visual pattern. Matching keypoints is important because you’re trying to find pairs of points that should align in the final stitched image. Not all matches between keypoints are good, though. Some may be misleading due to noise or repetitive patterns in the images. To filter out bad matches, the algorithm uses something called the “ratio test.” based on the lowe's ratio. In simple terms, it compares the best match for a keypoint to the second-best match. If the best match is significantly better (in terms of distance) than the second-best match, the match is considered reliable and is kept. This helps to avoid matching wrong features that could distort the final result.

After filtering the keypoints, we create a projective transformation matrix also called the homography matrix. that is a function to project the first keypoint onto the second frame. The relationship between a point $(x_1, y_1)$ in the first image and the corresponding point $(x_2, y_2)$ in the second image can be expressed as:

$$
\begin{bmatrix} x_2 \\ y_2 \\ 1 \end{bmatrix} = H \cdot \begin{bmatrix} x_1 \\ y_1 \\ 1 \end{bmatrix}
$$

This Homography matrix tells you how to map the keypoints from the first image to their corresponding points in the second image. Essentially, it’s like finding out how to “stretch” or “shift” the first image so that it fits perfectly with the second image. This is done by solving a set of equations that use the matched keypoints to figure out how to best align the two images.

Once you have the homography, the next step is to apply it. This is done using a process called perspective warping. When you apply the homography, you're transforming the first image into a new version where its keypoints now align with the keypoints in the second image. This is where the magic happens – the first image is warped to fit together with the second image, creating a seamless transition.

Finally, once the first image is warped, you need to combine it with the second image. This is done by placing the warped image onto a larger canvas that can fit both images side by side. The second image is then added where it fits, creating a smooth stitching effect.

and that is it, you've created your own ___"panorama"___ by stitching images based on thier common features.


```python
import cv2
import matplotlib.pyplot as plt
import numpy as np

img_1 = cv2.imread('image_1.JPG')
img_2 = cv2.imread('image_2.JPG')


img1 = cv2.cvtColor(img_1,cv2.COLOR_BGR2GRAY)
plt.imshow(img1)
plt.show()
img2 = cv2.cvtColor(img_2,cv2.COLOR_BGR2GRAY)
plt.imshow(img2)
plt.show()

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

dst = cv2.warpPerspective(img_1,H,((img_1.shape[1] + img_2.shape[1]), img_2.shape[0])) #wraped image
dst[0:img_2.shape[0], 0:img_2.shape[1]] = img_2 #stitched image
cv2.imwrite('output.jpg',dst)
plt.imshow(dst)
plt.show()
```


