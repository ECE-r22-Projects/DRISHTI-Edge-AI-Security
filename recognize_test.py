import cv2
import numpy as np
import sqlite3

FACE_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNITION_MODEL = "models/face_recognition_sface_2021dec.onnx"

# Load registered faces
db = sqlite3.connect("drishti.db")
rows = db.execute("SELECT name, face_embedding FROM persons").fetchall()
db.close()

known_faces = []

for name, embedding in rows:
    emb = np.frombuffer(embedding, dtype=np.float32)
    known_faces.append((name, emb))

print("Registered people:", [x[0] for x in known_faces])

# Face detector
detector = cv2.FaceDetectorYN.create(
    FACE_MODEL,
    "",
    (320, 320),
    0.6,
    0.3,
    5000
)

# Face recognizer
recognizer = cv2.FaceRecognizerSF.create(
    RECOGNITION_MODEL,
    ""
)

# Camera
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not be opened")
    exit()

print("FACE RECOGNITION CAMERA STARTED")
print("Press Q to quit.")

while True:

    ret, frame = camera.read()

    if not ret:
        print("Camera frame failed")
        break

    h, w = frame.shape[:2]
    detector.setInputSize((w, h))

    _, faces = detector.detect(frame)

    if faces is not None:

        for face in faces:

            # Draw face box
            x, y, fw, fh = face[:4].astype(int)

            face_crop = recognizer.alignCrop(frame, face)

            feature = recognizer.feature(face_crop)

            best_name = "Unknown"
            best_score = 0

            for name, known_feature in known_faces:

                score = recognizer.match(
                    feature,
                    known_feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                )

                if score > best_score:
                    best_score = score
                    best_name = name

            # Recognition threshold
            if best_score < 0.363:
                best_name = "Unknown"

            cv2.rectangle(
                frame,
                (x, y),
                (x + fw, y + fh),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"{best_name} {best_score:.2f}",
                (x, max(y - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    cv2.imshow("DRISHTI - Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()