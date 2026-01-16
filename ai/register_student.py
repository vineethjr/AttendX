import cv2
import os
import sys
import time

if len(sys.argv) < 3:
    print("Usage: python register_student.py <name> <roll>")
    sys.exit(1)

name = sys.argv[1]
roll = sys.argv[2]

folder_path = f"data/students/{roll}_{name}"

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

cap = cv2.VideoCapture(0)  # Use default camera (0)
count = 0
start_time = time.time()

print("Starting face capture...")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        face = frame[y:y+h, x:x+w]
        count += 1
        file_name = f"{folder_path}/face_{count}.jpg"
        cv2.imwrite(file_name, face)
        print(f"Face {count} captured")

    # Capture for 10 seconds or 20 faces
    if count >= 20 or (time.time() - start_time) > 10:
        break

cap.release()
cv2.destroyAllWindows()

print("Registration completed")
