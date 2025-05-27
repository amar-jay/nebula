import cv2
import numpy as np
from typing import Optional, Tuple

class FrameStabilizer:
    def __init__(self, smoothing_radius: int = 50):
        """
        Initialize the frame stabilizer.
        
        Args:
            smoothing_radius: Number of frames to use for trajectory smoothing
        """
        self.smoothing_radius = smoothing_radius
        self.prev_gray = None
        self.prev_pts = None
        self.transforms = []
        self.trajectory = []
        self.smoothed_trajectory = []
        
        # Parameters for corner detection
        self.feature_params = dict(
            maxCorners=200,
            qualityLevel=0.01,
            minDistance=30,
            blockSize=3
        )
        
        # Parameters for Lucas-Kanade optical flow
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
    
    def stabilize_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Stabilize a single frame based on previous frames.
        
        Args:
            frame: Input frame as numpy array (BGR format)
            
        Returns:
            Stabilized frame or None if stabilization fails
        """
        if frame is None:
            return None
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame.shape[:2]
        
        # For the first frame, just detect features and return original
        if self.prev_gray is None:
            self.prev_pts = cv2.goodFeaturesToTrack(gray, **self.feature_params)
            self.prev_gray = gray.copy()
            return frame
        
        # Track features using optical flow
        if self.prev_pts is not None and len(self.prev_pts) > 0:
            curr_pts, status, error = cv2.calcOpticalFlowPyrLK(
                self.prev_gray, gray, self.prev_pts, None, **self.lk_params
            )
            
            # Filter good points
            good_new = curr_pts[status == 1]
            good_old = self.prev_pts[status == 1]
            
            # Need at least 10 points for reliable transformation
            if len(good_new) < 10:
                # Re-detect features if we lost too many
                self.prev_pts = cv2.goodFeaturesToTrack(gray, **self.feature_params)
                self.prev_gray = gray.copy()
                return frame
            
            # Estimate transformation matrix
            transform_matrix, mask = cv2.estimateAffinePartial2D(
                good_old, good_new, method=cv2.RANSAC
            )
            
            if transform_matrix is not None:
                # Extract transformation parameters
                dx = transform_matrix[0, 2]
                dy = transform_matrix[1, 2]
                da = np.arctan2(transform_matrix[1, 0], transform_matrix[0, 0])
                
                # Store transform
                self.transforms.append([dx, dy, da])
                
                # Calculate trajectory (cumulative transforms)
                if len(self.trajectory) == 0:
                    self.trajectory.append([dx, dy, da])
                else:
                    prev_traj = self.trajectory[-1]
                    self.trajectory.append([
                        prev_traj[0] + dx,
                        prev_traj[1] + dy,
                        prev_traj[2] + da
                    ])
                
                # Smooth trajectory using moving average
                smoothed_traj = self._smooth_trajectory()
                self.smoothed_trajectory.append(smoothed_traj)
                
                # Calculate stabilizing transform
                if len(self.smoothed_trajectory) > 0:
                    curr_traj = self.trajectory[-1]
                    smooth_traj = self.smoothed_trajectory[-1]
                    
                    diff_x = smooth_traj[0] - curr_traj[0]
                    diff_y = smooth_traj[1] - curr_traj[1]
                    diff_a = smooth_traj[2] - curr_traj[2]
                    
                    # Create stabilizing transformation matrix
                    stabilize_transform = np.array([
                        [np.cos(diff_a), -np.sin(diff_a), diff_x],
                        [np.sin(diff_a), np.cos(diff_a), diff_y]
                    ], dtype=np.float32)
                    
                    # Apply transformation to stabilize frame
                    stabilized_frame = cv2.warpAffine(
                        frame, stabilize_transform, (w, h)
                    )
                    
                    # Crop borders to remove black edges (optional)
                    stabilized_frame = self._crop_borders(stabilized_frame, crop_ratio=0.1)
                    
                else:
                    stabilized_frame = frame
            else:
                stabilized_frame = frame
        else:
            stabilized_frame = frame
        
        # Update for next frame
        self.prev_gray = gray.copy()
        self.prev_pts = cv2.goodFeaturesToTrack(gray, **self.feature_params)
        
        return stabilized_frame
    
    def _smooth_trajectory(self) -> list:
        """Apply moving average smoothing to trajectory."""
        if len(self.trajectory) == 0:
            return [0, 0, 0]
        
        # Determine the range for averaging
        start_idx = max(0, len(self.trajectory) - self.smoothing_radius)
        end_idx = min(len(self.trajectory), start_idx + self.smoothing_radius)
        
        # Calculate moving average
        trajectory_segment = self.trajectory[start_idx:end_idx]
        if len(trajectory_segment) == 0:
            return [0, 0, 0]
        
        smoothed = [
            sum(t[0] for t in trajectory_segment) / len(trajectory_segment),
            sum(t[1] for t in trajectory_segment) / len(trajectory_segment),
            sum(t[2] for t in trajectory_segment) / len(trajectory_segment)
        ]
        
        return smoothed
    
    def _crop_borders(self, frame: np.ndarray, crop_ratio: float = 0.1) -> np.ndarray:
        """Crop borders to remove black edges from stabilization."""
        h, w = frame.shape[:2]
        crop_h = int(h * crop_ratio)
        crop_w = int(w * crop_ratio)
        
        return frame[crop_h:h-crop_h, crop_w:w-crop_w]


# Simplified function interface
def stabilize_frame(frame: np.ndarray, stabilizer: FrameStabilizer = None) -> Tuple[np.ndarray, FrameStabilizer]:
    """
    Stabilize a single frame. For use in video processing loops.
    
    Args:
        frame: Input frame as numpy array (BGR format)
        stabilizer: FrameStabilizer instance (will create new one if None)
        
    Returns:
        Tuple of (stabilized_frame, stabilizer_instance)
    """
    if stabilizer is None:
        stabilizer = FrameStabilizer()
    
    stabilized = stabilizer.stabilize_frame(frame)
    return stabilized if stabilized is not None else frame, stabilizer


# Example usage for video stabilization
def stabilize_video(input_path: str, output_path: str):
    """
    Stabilize an entire video file.
    
    Args:
        input_path: Path to input video
        output_path: Path to save stabilized video
    """
    cap = cv2.VideoCapture(input_path)
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    stabilizer = FrameStabilizer(smoothing_radius=30)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        stabilized_frame = stabilizer.stabilize_frame(frame)
        if stabilized_frame is not None:
            # Resize back to original dimensions if cropped
            if stabilized_frame.shape[:2] != (height, width):
                stabilized_frame = cv2.resize(stabilized_frame, (width, height))
            out.write(stabilized_frame)
        else:
            out.write(frame)
    
    cap.release()
    out.release()
    cv2.destroyAllWindows()


# Example usage:
if __name__ == "__main__":
    # For single frame processing
    stabilizer = FrameStabilizer()
    
    # Process frames in a loop
    cap = cv2.VideoCapture(0)  # Or video file path
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        stabilized = stabilizer.stabilize_frame(frame)
        
        if stabilized is not None:
            cv2.imshow('Original', frame)
            cv2.imshow('Stabilized', stabilized)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()

