import cv2
import sqlite3
import numpy as np
import sys
import os

DETECTOR_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = "models/face_recognition_sface_2021dec.onnx"
DB_PATH = "drishti.db"


def register_person(name, image_path):

    # Check image
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        return

    image = cv2.imread(image_path)

    if image is None:
        print("ERROR: Could not read image.")
        return

    # Load models
    detector = cv2.FaceDetectorYN.create(
        DETECTOR_MODEL,
        "",
        (320, 320),
        0.6,
        0.3,
        5000
    )

    recognizer = cv2.FaceRecognizerSF.create(
        RECOGNIZER_MODEL,
        ""
    )

    # Set detector input size
    h, w = image.shape[:2]
    detector.setInputSize((w, h))

    # Detect faces
    _, faces = detector.detect(image)

    if faces is None or len(faces) == 0:
        print("ERROR: No face detected.")
        return

    if len(faces) > 1:
        print(f"ERROR: {len(faces)} faces detected.")
        print("Please use a photo containing only one person.")
        return

    face = faces[0]

    # Align and crop face
    aligned_face = recognizer.alignCrop(image, face)

    # Generate face embedding
    feature = recognizer.feature(aligned_face)

    # Convert embedding to bytes
    embedding_bytes = feature.astype(np.float32).tobytes()

    # Save to database
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO persons (name, face_embedding)
        VALUES (?, ?)
        """,
        (name, embedding_bytes)
    )

    conn.commit()
    conn.close()

    print()
    print("================================")
    print("PERSON REGISTERED SUCCESSFULLY")
    print("================================")
    print(f"Name : {name}")
    print(f"Image: {image_path}")
    print("Face embedding saved to database.")
    print()


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print()
        print("Usage:")
        print('python register_face.py "Name" "image_path"')
        print()
        print("Example:")
        print('python register_face.py "Gaurav" "faces/gaurav.jpg"')
        print()
        sys.exit(1)

    name = sys.argv[1]
    image_path = sys.argv[2]

    register_person(name, image_path)