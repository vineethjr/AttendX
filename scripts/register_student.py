import cv2
import os

name = input("Enter Student Name: ")
roll = input("Enter Roll Number: ")

folder_path = f"data/students/{roll}_{name}"

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

cap = cv2.VideoCapture(1)  # change if needed
count = 0

print("Press 's' to save face, 'q' to quit")

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
        cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)

    cv2.imshow("Student Registration", frame)

    key = cv2.waitKey(1)
    if key & 0xFF == ord('s'):
        print("Face captured")
    elif key & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

print("Registration completed")
