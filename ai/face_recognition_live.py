import sys
import os
import cv2
import face_recognition
import warnings

# 🔹 Add project root to Python path (IMPORTANT)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from logic.mark_attendance import mark_scan

# Optional: hide harmless warnings
warnings.filterwarnings("ignore", category=UserWarning)

KNOWN_FACES_DIR = "../data/students"

known_encodings = []
known_names = []

print("Loading student face data...")

# ---------------- LOAD STORED FACE DATA ----------------
for folder in os.listdir(KNOWN_FACES_DIR):
    folder_path = os.path.join(KNOWN_FACES_DIR, folder)

    if not os.path.isdir(folder_path):
        continue

    name = folder  # roll number is folder name

    for image_name in os.listdir(folder_path):
        if not image_name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        image_path = os.path.join(folder_path, image_name)
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)

        if encodings:
            known_encodings.append(encodings[0])
            known_names.append(name)

print("Face data loaded successfully")

# ---------------- ATTENDANCE SETTINGS ----------------
SCAN_NO = 1                 # Simulating scan 1
marked_today = set()        # Prevent duplicate DB inserts

# ---------------- CAMERA ----------------
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Camera not accessible")
    exit()

# ---------------- LIVE RECOGNITION ----------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):

        matches = face_recognition.compare_faces(
            known_encodings, face_encoding, tolerance=0.5
        )

        name = "Unknown"

        if True in matches:
            matched_index = matches.index(True)
            name = known_names[matched_index]

            # 🔗 INTEGRATION STEP (ATTENDANCE INSERT)
            if name not in marked_today:
                mark_scan(
                    roll_no=name,
                    subject_name="Demo Subject",
                    scan_no=SCAN_NO,
                    status=1
                )
                marked_today.add(name)
                print(f"Scan {SCAN_NO}: attendance recorded for {name}")

        # ✅ DRAW RECTANGLE AND NAME (INSIDE LOOP)
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

    cv2.imshow("AttendX | Face Recognition (Press Q to Exit)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
