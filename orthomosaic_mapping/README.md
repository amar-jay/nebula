# 🗺️ Orthomosaic Aerial Mapping (No ROS)

We are going to implement a pipeline for generating an **orthomosaic aerial map** from drone-captured images. It is designed to work without ROS or similar frameworks..

---

## 📸 Project Description

An **orthomosaic** is a geometrically corrected image composed of multiple aerial photographs stitched together to form a single, unified, distortion-free, top-down view of a scene.

This project builds such a map from overlapping drone images using Structure-from-Motion (SfM), photogrammetry and SLAM techniques.

---

## 🛠️ Technologies Used

- [OpenCV](https://opencv.org/) – feature detection, image stitching
- [NumPy / SciPy](https://numpy.org/) – matrix operations
- [COLMAP](https://colmap.github.io/) – optional SfM engine
- [Pillow](https://python-pillow.org/) – image IO
- [pyproj / geopy](https://pyproj4.github.io/pyproj/) – geospatial transforms
- [Matplotlib / Open3D / Rasterio] – visualization, georeferencing

---

## 🧠 Pipeline Overview

1. **Image Capture**
   - Capture overlapping drone images with fixed orientation (downward or horizontal).
   - Save GPS/IMU metadata if available.
2. **Image Preprocessing**
   - Resize or normalize images.
   - Lens distortion correction.
   - Metadata extraction.
3. **Feature Detection & Matching**
   - Detect keypoints using ORB/SIFT.
   - Match features between overlapping images.
4. **Pose Estimation / SfM**
   - Estimate relative camera motion (optional: use COLMAP).
   - Generate sparse 3D point cloud.
5. **Image Warping**
   - Compute homographies or projection matrices.
   - Warp images into common map frame.
6. **Mosaicking & Blending**

   - Align and blend warped images.
   - Handle overlaps and exposure differences.

7. **Orthorectification (Optional)**
   - Reproject onto ground plane.
   - Georeference map if GPS is available.
8. **Export**
   - Save high-res PNG/JPEG or GeoTIFF.
   - Optional: tile for web viewing.

---

## ✅ To-Do List

### 📸 1. Data Collection

- [ ] Capture overlapping aerial images with at least 60% forward and side overlap.
- [ ] Ensure camera orientation is fixed (gimbal-locked).
- [ ] Save EXIF data or GPS/IMU metadata.

### 🧼 2. Preprocessing

- [ ] Write script to load and resize images.
- [ ] Calibrate camera and undistort images.
- [ ] Extract GPS info using `piexif` or `exifread`.

### 🧠 3. Feature Detection & Matching

- [ ] Implement ORB/SIFT keypoint detection.
- [ ] Match features using BFMatcher or FLANN.
- [ ] Filter outliers with RANSAC.

### 📐 4. Pose Estimation / SfM

- [ ] Integrate or interface with COLMAP CLI.
- [ ] Parse sparse reconstruction and camera poses.
- [ ] Visualize point cloud and camera positions.

### 🌀 5. Image Warping

- [ ] Compute homographies or projection matrices.
- [ ] Warp images to a shared ground plane.
- [ ] Use feathering/masking for better blending.

### 🧵 6. Blending and Mosaicking

- [ ] Implement multiband or average blending.
- [ ] Stitch overlapping images together.

### 🌍 7. Orthorectification

- [ ] Apply GPS/IMU corrections to map projection.
- [ ] Optionally align to UTM grid or EPSG coordinate system.
- [ ] Export GeoTIFF if georeferenced.

### 🖼️ 8. Visualization & Export

- [ ] Visualize map using Matplotlib/Open3D/Folium.
- [ ] Save as JPEG, PNG, or GeoTIFF.
- [ ] Optional: tile output for web map viewers.

---

## 📦 Installation

```bash
git clone https://github.com/your-username/orthomosaic-mapper.git
cd orthomosaic-mapper
pip install -r requirements.txt
```

---

## References

- [COLMAP](https://colmap.github.io/)
- [Meshroom](https://alicevision.org/)
- [OpenDroneMap](https://www.opendronemap.org/)
- [PyImageSearch tutorials](https://pyimagesearch.com/)
