import argparse
import cv2
import logging
from datetime import datetime
import time
from collections import deque
from model import Model
import os  

# Log file name
log_filename = 'detection_log.txt'

# If the log file already exists, delete it
if os.path.exists(log_filename):
    os.remove(log_filename)

# Configure logging with the same filename (it will create a new one)
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(message)s')

# Settings for violence detection alert
# adjust threshold and time window as per batch size
#deon
# DETECTION_THRESHOLD = 50  # Number of detections
# TIME_WINDOW = 3  # Time window in seconds
# ALERT_COOLDOWN = 10  # Cooldown period in seconds before another alert is allowed
# BATCH_SIZE = 9 
DETECTION_THRESHOLD = 40  # Number of detections
TIME_WINDOW = 3  # Time window in seconds
ALERT_COOLDOWN = 10  # Cooldown period in seconds before another alert is allowed
BATCH_SIZE = 9  # Number of frames to process in a batch 

def argument_parser():
    parser = argparse.ArgumentParser(description="Violence detection in images, videos, and webcam feed")
    parser.add_argument('--input-path', type=str, help='Path to your image or video file (leave empty for webcam)')
    args = parser.parse_args()
    return args

def log_label(label):
    """Log the detected label with the current timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f'{timestamp} - Detected label: {label}')

def check_for_alert(detection_times, last_alert_time):
    current_time = time.time()
    
    # Remove timestamps older than TIME_WINDOW seconds from the buffer
    while detection_times and current_time - detection_times[0] > TIME_WINDOW:
        detection_times.popleft()

    # If we have DETECTION_THRESHOLD or more detections in the last TIME_WINDOW seconds, trigger alert
    if len(detection_times) >= DETECTION_THRESHOLD:
        # Trigger alert only if ALERT_COOLDOWN has passed since the last alert
        if current_time - last_alert_time >= ALERT_COOLDOWN:
            print("Alert: Violence detected!")
            logging.info("Alert: Violence detected!")
            return current_time  # Update last_alert_time
    
    return last_alert_time

#IMAGE PROCESSING

def process_image(model, image_path):
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not read image from {image_path}")
        return
    label = model.predict(image=image)['label']
    log_label(label)
    print(f'Predicted label for image: {label}')
    cv2.imshow('Violence Detection', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

#VIDEO PROCESSING

def process_video(model, video_path):
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        print(f"Error: Could not open video from {video_path}")
        return

    last_log_time = time.time()
    detection_times = deque()  # Buffer to store violence detection timestamps
    last_alert_time = 0  # Store the time of the last alert
    frame_batch = []  # Batch of frames

    label_to_display = ""  # This will store the current label to display

    while True:
        ret, frame = video.read()
        if not ret:
            break  # End of video
        
        # Add frame to batch
        frame_batch.append(frame)
        
        # If batch is full, process it
        if len(frame_batch) == BATCH_SIZE:
            labels = model.predict_batch(frame_batch)
            
            for label_dict in labels:
                label = label_dict['label']
                
                # If a new label is detected, reset the display counter
                if label != label_to_display and 'violence'in label:
                    label_to_display = label

                current_time = time.time()
                if current_time - last_log_time >= 0.5:  
                    log_label(label)
                    last_log_time = current_time
                
                # If violence is detected (partial match), store the current timestamp
                if 'violence' in label_to_display.lower():
                    detection_times.append(time.time())
                    last_alert_time = check_for_alert(detection_times, last_alert_time)
                else:
                    # Reset detection buffer if no violence detected in current frame
                    detection_times.clear()

            # Reset batch
            frame_batch = []


        cv2.putText(frame, f'{label_to_display}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        
        # Show the frame in the same window
        cv2.imshow('Violence Detection', frame)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture and close windows
    video.release()
    cv2.destroyAllWindows()

#REAL_TIME PROCESSING

def process_webcam(model):
    video = cv2.VideoCapture(0)  # Capture from the default webcam
    if not video.isOpened():
        print("Error: Could not access webcam.")
        return

    last_log_time = time.time()
    detection_times = deque()  # Buffer to store violence detection timestamps
    last_alert_time = 0  # Store the time of the last alert
    frame_batch = []  # Batch of frames

    label_to_display = ""  # This will store the current label to display

    while True:
        ret, frame = video.read()
        if not ret:
            print("Error: Could not read frame from webcam.")
            break
        
        # Add frame to batch
        frame_batch.append(frame)
        
        # If batch is full, process it
        if len(frame_batch) == BATCH_SIZE:
            labels = model.predict_batch(frame_batch)

            for label_dict in labels:
                label = label_dict['label']

                # If a new label is detected, reset the display counter
                if label != label_to_display and 'violence'in label:
                    label_to_display = label
                
                # Log the label every 1 s
                current_time = time.time()
                if current_time - last_log_time >= .5: 
                    log_label(label)
                    last_log_time = current_time

                # If violence is detected (partial match), store the current timestamp 
                if 'violence' in label_to_display.lower() :
                    detection_times.append(time.time())
                    last_alert_time = check_for_alert(detection_times, last_alert_time)
                else:
                    # Reset detection buffer if no violence detected in current frame
                    detection_times.clear()

            # Reset batch
            frame_batch = []


        cv2.putText(frame, f'Label: {label_to_display}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        # Show the frame in the same window
        cv2.imshow('Violence Detection', frame)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the webcam and close windows
    video.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    args = argument_parser()
    model = Model()
    input_path = args.input_path
    if input_path is None:
        process_webcam(model)
    elif input_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
        process_image(model, input_path)
    elif input_path.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv')):
        process_video(model, input_path)
    else:
        print("Error: Unsupported file format. Please provide a valid image or video file, or leave empty for webcam.")
