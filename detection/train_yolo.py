import argparse
import cv2
import torch
from ultralytics import YOLO

def train_model(data, weights, epochs, batch_size, img_size):
    """Train YOLOv8 on a custom dataset."""
    device = "cuda" if torch.cuda.is_available() else "cpu" # TODO: find a less expensive way to do check GPU
    model = YOLO(weights).to(device)
    
    model.train(data=data, epochs=epochs, batch=batch_size, imgsz=img_size)
    print("Training completed! Check the `runs/train/exp/` folder.")

def evaluate_model(model_path, data):
    """Evaluate the trained YOLO model on validation/test set."""
    model = YOLO(model_path)
    metrics = model.val(data=data)
    print(metrics)

def run_inference(model_path, camera_path=0):
    """Run inference on an image using a trained YOLOv8 model."""
    model = YOLO(model_path)

    # Initialize camera (0 for default webcam)
    cap = cv2.VideoCapture(camera_path)  # Change the argument for other cameras if needed

    if not cap.isOpened():
        print("Error: Could not access the camera.")
        exit()

    while True:
        # Read a frame from the camera
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Failed to capture image.")
            break
        
        # Perform inference
        results = model(frame)
        
        # Extract boxes, labels, and confidence
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2, conf, cls = box.xyxy[0]
                label = f"Helipad {conf:.2f}"
                
                # Draw bounding box and label
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
        # Display the resulting frame
        cv2.imshow("Helipad Detection (Press 'q' to exit)", frame)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the capture object and close OpenCV windows
    cap.release()
    cv2.destroyAllWindows()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune & detect YOLOv8 for Helipad & Tank Detection.")
    
    parser.add_argument("--mode", type=str, choices=["train", "infer", "eval"], required=True, 
                        help="Mode: 'train' to fine-tune, 'infer' for detection, 'eval' to evaluate model.")
    parser.add_argument("--data", type=str, default="dataset.yaml", 
                        help="Path to dataset.yaml (used for training and evaluation).")
    parser.add_argument("--epochs", type=int, default=50, 
                        help="Number of training epochs (default: 50).")
    parser.add_argument("--batch", type=int, default=16, 
                        help="Batch size for training (default: 16).")
    parser.add_argument("--img_size", type=int, default=640, 
                        help="Image size for training (default: 640).")
    parser.add_argument("--video", type=int, default=0, 
                        help="Path to an video cam for inference.")
    parser.add_argument("--weights", type=str, 
                        help="Path to a YOLO model weights")

    args = parser.parse_args()

    if not args.weights:
        print("Error: Provide --weights for inference.")
        exit()
    if args.mode == "train":
        train_model(args.data, args.weights, args.epochs, args.batch, args.img_size)
    elif args.mode == "infer":
        run_inference(args.weights, args.video)
    elif args.mode == "eval":
        evaluate_model(args.weights, args.data)

