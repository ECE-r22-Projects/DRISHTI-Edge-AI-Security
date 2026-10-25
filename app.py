import os
import cv2
import time
import sqlite3
import threading
from datetime import datetime

import numpy as np
from flask import Flask, render_template, Response, jsonify
from ultralytics import YOLO


# ============================================================
# DRISHTI
# REAL-TIME OBJECT DETECTION
# + FACE RECOGNITION
# + SECURITY MONITORING
# + TELEGRAM PHOTO ALERTS
# ============================================================

app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

FACE_MODEL = "models/face_detection_yunet_2023mar.onnx"

RECOGNITION_MODEL = (
    "models/face_recognition_sface_2021dec.onnx"
)

OBJECT_MODEL = "yolo11s.pt"

DATABASE = "drishti.db"

CAMERA_INDEX = 0

RECOGNITION_THRESHOLD = 0.363

OBJECT_CONFIDENCE = 0.40

EVENT_COOLDOWN = 30

OBJECT_DETECTION_INTERVAL = 2

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

JPEG_QUALITY = 75

ALERT_DIRECTORY = "security_alerts"

os.makedirs(
    ALERT_DIRECTORY,
    exist_ok=True
)


# ============================================================
# TELEGRAM SERVICE
# ============================================================

try:

    from notification_service import (
        send_telegram_message,
        send_telegram_photo
    )

    NOTIFICATION_SERVICE_AVAILABLE = True

    print(
        "[TELEGRAM] notification_service imported successfully"
    )

except Exception as e:

    NOTIFICATION_SERVICE_AVAILABLE = False

    send_telegram_message = None
    send_telegram_photo = None

    print(
        "[TELEGRAM] notification_service import failed:",
        e
    )


# ============================================================
# GLOBAL VARIABLES
# ============================================================

known_faces = []

current_people = []

current_objects = []

camera_online = False

ai_online = False

object_detection_online = False

database_online = False

telegram_online = False

security_alert = False

security_alert_name = ""

security_alert_time = ""

last_event_times = {}

last_telegram_time = 0

object_frame_counter = 0

camera_lock = threading.Lock()


# ============================================================
# DATABASE
# ============================================================

def get_db():

    db = sqlite3.connect(
        DATABASE,
        timeout=10
    )

    db.row_factory = sqlite3.Row

    return db


def initialize_database():

    global database_online

    try:

        db = get_db()

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS security_events
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                person_name TEXT NOT NULL,

                confidence REAL NOT NULL,

                event_type TEXT NOT NULL,

                timestamp TEXT NOT NULL
            )
            """
        )

        db.commit()

        db.close()

        database_online = True

        print(
            "[DATABASE] Database initialized successfully"
        )

    except Exception as e:

        database_online = False

        print(
            "[DATABASE ERROR]",
            e
        )


# ============================================================
# LOAD REGISTERED FACES
# ============================================================

def load_known_faces():

    global known_faces
    global database_online

    try:

        db = get_db()

        rows = db.execute(
            """
            SELECT name, face_embedding
            FROM persons
            """
        ).fetchall()

        db.close()

        loaded_faces = []

        for row in rows:

            name = row["name"]

            embedding = row["face_embedding"]

            if embedding is None:
                continue

            emb = np.frombuffer(
                embedding,
                dtype=np.float32
            )

            loaded_faces.append(
                (
                    name,
                    emb
                )
            )

        known_faces = loaded_faces

        database_online = True

        print(
            "[DATABASE] Registered people:",
            [
                x[0]
                for x in known_faces
            ]
        )

        return True

    except Exception as e:

        known_faces = []

        database_online = False

        print(
            "[DATABASE ERROR]",
            e
        )

        return False


# ============================================================
# TELEGRAM ASYNC MESSAGE
# ============================================================

def send_telegram_async(message):

    global telegram_online

    def worker():

        global telegram_online

        if not NOTIFICATION_SERVICE_AVAILABLE:

            telegram_online = False

            print(
                "[TELEGRAM] Notification service unavailable"
            )

            return

        try:

            result = send_telegram_message(
                message
            )

            if result:

                telegram_online = True

                print(
                    "[TELEGRAM] Text notification sent"
                )

            else:

                telegram_online = False

                print(
                    "[TELEGRAM] Text notification failed"
                )

        except Exception as e:

            telegram_online = False

            print(
                "[TELEGRAM ERROR]",
                e
            )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


# ============================================================
# TELEGRAM PHOTO NOTIFICATION
# ============================================================

def send_telegram_photo_async(
    image_path,
    caption
):

    global telegram_online

    def worker():

        global telegram_online

        if not NOTIFICATION_SERVICE_AVAILABLE:

            telegram_online = False

            print(
                "[TELEGRAM] Notification service unavailable"
            )

            return

        if send_telegram_photo is None:

            telegram_online = False

            print(
                "[TELEGRAM] send_telegram_photo unavailable"
            )

            return

        try:

            result = send_telegram_photo(
                image_path,
                caption
            )

            if result:

                telegram_online = True

                print(
                    "[TELEGRAM] Photo notification sent successfully"
                )

            else:

                telegram_online = False

                print(
                    "[TELEGRAM] Photo notification failed"
                )

        except Exception as e:

            telegram_online = False

            print(
                "[TELEGRAM PHOTO ERROR]",
                e
            )

    threading.Thread(
        target=worker,
        daemon=True
    ).start()


# ============================================================
# SAVE SECURITY SNAPSHOT
# ============================================================

def save_security_snapshot(frame):

    try:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            f"unknown_{timestamp}.jpg"
        )

        image_path = os.path.join(
            ALERT_DIRECTORY,
            filename
        )

        success = cv2.imwrite(
            image_path,
            frame
        )

        if success:

            print(
                "[SECURITY] Alert image saved:",
                image_path
            )

            return image_path

        print(
            "[SECURITY] Could not save alert image"
        )

        return None

    except Exception as e:

        print(
            "[SECURITY IMAGE ERROR]",
            e
        )

        return None


# ============================================================
# OBJECT DESCRIPTION FOR TELEGRAM
# ============================================================

def get_object_description(objects):

    if not objects:

        return "Objects detected: None"

    useful_objects = []

    for obj in objects:

        name = obj.get(
            "name",
            "unknown"
        )

        confidence = obj.get(
            "confidence",
            0
        )

        # YOLO will normally detect the person itself.
        # We don't need "person" in the object list because
        # the security alert already identifies the person.
        if name.lower() == "person":

            continue

        useful_objects.append(
            f"{name} ({confidence:.2f})"
        )

    if not useful_objects:

        return "Objects detected: None"

    return (
        "Objects detected: "
        +
        ", ".join(
            useful_objects
        )
    )


# ============================================================
# SECURITY EVENT LOGGER
# ============================================================

def log_security_event(
    person_name,
    confidence,
    event_type,
    frame=None,
    objects=None
):

    global last_event_times

    global last_telegram_time

    global security_alert

    global security_alert_name

    global security_alert_time

    try:

        event_key = (
            event_type
            +
            "_"
            +
            person_name
        )

        current_time = time.time()

        # ----------------------------------------------------
        # EVENT COOLDOWN
        # ----------------------------------------------------

        if event_key in last_event_times:

            elapsed = (
                current_time
                -
                last_event_times[event_key]
            )

            if elapsed < EVENT_COOLDOWN:

                return

        last_event_times[event_key] = current_time

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----------------------------------------------------
        # SAVE EVENT TO DATABASE
        # ----------------------------------------------------

        db = get_db()

        db.execute(
            """
            INSERT INTO security_events
            (
                person_name,
                confidence,
                event_type,
                timestamp
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                person_name,
                float(confidence),
                event_type,
                timestamp
            )
        )

        db.commit()

        db.close()

        # ====================================================
        # UNKNOWN PERSON
        # ====================================================

        if event_type == "UNKNOWN":

            security_alert = True

            security_alert_name = person_name

            security_alert_time = timestamp

            print()
            print(
                "=========================================="
            )
            print(
                "🚨 UNKNOWN PERSON DETECTED"
            )
            print(
                "=========================================="
            )
            print(
                "Confidence:",
                round(
                    float(confidence),
                    2
                )
            )

            # ------------------------------------------------
            # SAVE IMAGE
            # ------------------------------------------------

            image_path = None

            if frame is not None:

                image_path = (
                    save_security_snapshot(
                        frame
                    )
                )

            # ------------------------------------------------
            # TELEGRAM COOLDOWN
            # ------------------------------------------------

            telegram_now = time.time()

            if (
                telegram_now
                -
                last_telegram_time
                >=
                EVENT_COOLDOWN
            ):

                last_telegram_time = (
                    telegram_now
                )

                object_text = (
                    get_object_description(
                        objects or []
                    )
                )

                # --------------------------------------------
                # PHOTO CAPTION
                # --------------------------------------------

                caption = (
                    "🚨 DRISHTI SECURITY ALERT 🚨\n\n"
                    "⚠️ Unauthorized person detected.\n\n"
                    f"👤 Person: Unknown\n"
                    f"🎯 Face confidence: "
                    f"{float(confidence):.2f}\n"
                    f"🕒 Time: {timestamp}\n\n"
                    f"🔎 {object_text}\n\n"
                    "Please check the DRISHTI dashboard."
                )

                # --------------------------------------------
                # SEND PHOTO
                # --------------------------------------------

                if image_path is not None:

                    print(
                        "[TELEGRAM] Sending security photo..."
                    )

                    send_telegram_photo_async(
                        image_path,
                        caption
                    )

                else:

                    # If image saving failed,
                    # at least send text.
                    print(
                        "[TELEGRAM] Image unavailable. "
                        "Sending text alert."
                    )

                    send_telegram_async(
                        caption
                    )

            else:

                print(
                    "[TELEGRAM] Alert cooldown active"
                )

            print(
                "=========================================="
            )
            print()

        # ====================================================
        # AUTHORIZED PERSON
        # ====================================================

        else:

            print(
                f"[SECURITY EVENT] "
                f"{event_type} | "
                f"{person_name} | "
                f"{float(confidence):.2f}"
            )

    except Exception as e:

        print(
            "[EVENT ERROR]",
            e
        )


# ============================================================
# LOAD YUNET
# ============================================================

try:

    detector = cv2.FaceDetectorYN.create(
        FACE_MODEL,
        "",
        (320, 320),
        0.6,
        0.3,
        5000
    )

    print(
        "[AI] YuNet face detector loaded"
    )

except Exception as e:

    detector = None

    print(
        "[AI ERROR] Face detector:",
        e
    )


# ============================================================
# LOAD SFACE
# ============================================================

try:

    recognizer = cv2.FaceRecognizerSF.create(
        RECOGNITION_MODEL,
        ""
    )

    print(
        "[AI] SFace face recognizer loaded"
    )

except Exception as e:

    recognizer = None

    print(
        "[AI ERROR] Face recognizer:",
        e
    )


# ============================================================
# LOAD YOLO11
# ============================================================

try:

    object_model = YOLO(
        OBJECT_MODEL
    )

    object_detection_online = True

    print(
        "[AI] YOLO11 loaded:",
        OBJECT_MODEL
    )

except Exception as e:

    object_model = None

    object_detection_online = False

    print(
        "[AI ERROR] YOLO11:",
        e
    )


# ============================================================
# CAMERA
# ============================================================

camera = cv2.VideoCapture(
    CAMERA_INDEX
)

camera.set(
    cv2.CAP_PROP_BUFFERSIZE,
    1
)

camera.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    FRAME_WIDTH
)

camera.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    FRAME_HEIGHT
)

camera.set(
    cv2.CAP_PROP_FPS,
    30
)


if camera.isOpened():

    camera_online = True

    print(
        "[CAMERA] Camera opened successfully"
    )

else:

    camera_online = False

    print(
        "[CAMERA ERROR] Camera could not be opened"
    )


# ============================================================
# DATABASE SETUP
# ============================================================

initialize_database()

load_known_faces()


# ============================================================
# OBJECT DETECTION
# ============================================================

def detect_objects(frame):

    global object_detection_online

    detected_objects = []

    if object_model is None:

        object_detection_online = False

        return detected_objects

    try:

        results = object_model.predict(
            source=frame,
            conf=OBJECT_CONFIDENCE,
            verbose=False,
            imgsz=640
        )

        if not results:

            return detected_objects

        result = results[0]

        boxes = result.boxes

        if boxes is None:

            object_detection_online = True

            return detected_objects

        names = result.names

        for box in boxes:

            confidence = float(
                box.conf[0]
            )

            class_id = int(
                box.cls[0]
            )

            object_name = names[
                class_id
            ]

            x1, y1, x2, y2 = (
                box.xyxy[0]
                .cpu()
                .numpy()
                .astype(int)
            )

            detected_objects.append(
                {
                    "name":
                        object_name,

                    "confidence":
                        round(
                            confidence,
                            2
                        ),

                    "x1":
                        int(x1),

                    "y1":
                        int(y1),

                    "x2":
                        int(x2),

                    "y2":
                        int(y2)
                }
            )

        object_detection_online = True

        return detected_objects

    except Exception as e:

        object_detection_online = False

        print(
            "[OBJECT DETECTION ERROR]",
            e
        )

        return []


# ============================================================
# DRAW OBJECTS
# ============================================================

def draw_objects(
    frame,
    objects
):

    color = (
        255,
        180,
        0
    )

    for obj in objects:

        x1 = obj["x1"]
        y1 = obj["y1"]

        x2 = obj["x2"]
        y2 = obj["y2"]

        label = (
            f'{obj["name"]} '
            f'{obj["confidence"]:.2f}'
        )

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        cv2.putText(
            frame,
            label,
            (
                x1,
                max(
                    y1 - 10,
                    20
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2
        )


# ============================================================
# FACE RECOGNITION
# ============================================================

def process_faces(frame):

    global current_people

    global ai_online

    detected_people = []

    if (
        detector is None
        or
        recognizer is None
    ):

        current_people = []

        ai_online = False

        return frame

    try:

        h, w = frame.shape[:2]

        detector.setInputSize(
            (w, h)
        )

        _, faces = detector.detect(
            frame
        )

        if faces is not None:

            for face in faces:

                x, y, fw, fh = (
                    face[:4]
                    .astype(int)
                )

                x = max(
                    0,
                    x
                )

                y = max(
                    0,
                    y
                )

                fw = min(
                    fw,
                    w - x
                )

                fh = min(
                    fh,
                    h - y
                )

                if (
                    fw <= 0
                    or
                    fh <= 0
                ):

                    continue

                # --------------------------------------------
                # ALIGN FACE
                # --------------------------------------------

                face_crop = (
                    recognizer.alignCrop(
                        frame,
                        face
                    )
                )

                # --------------------------------------------
                # EXTRACT FEATURE
                # --------------------------------------------

                feature = (
                    recognizer.feature(
                        face_crop
                    )
                )

                best_name = "Unknown"

                best_score = -1.0

                # --------------------------------------------
                # MATCH REGISTERED PEOPLE
                # --------------------------------------------

                for (
                    name,
                    known_feature
                ) in known_faces:

                    try:

                        score = (
                            recognizer.match(
                                feature,
                                known_feature,
                                cv2.FaceRecognizerSF_FR_COSINE
                            )
                        )

                        score = float(
                            score
                        )

                        if (
                            score
                            >
                            best_score
                        ):

                            best_score = score

                            best_name = name

                    except Exception as e:

                        print(
                            "[MATCH ERROR]",
                            e
                        )

                # --------------------------------------------
                # APPLY THRESHOLD
                # --------------------------------------------

                if (
                    best_score
                    <
                    RECOGNITION_THRESHOLD
                ):

                    best_name = "Unknown"

                display_score = max(
                    best_score,
                    0.0
                )

                # --------------------------------------------
                # LIVE DATA
                # --------------------------------------------

                detected_people.append(
                    {
                        "name":
                            best_name,

                        "confidence":
                            round(
                                display_score,
                                2
                            )
                    }
                )

                # --------------------------------------------
                # DRAW FACE BOX
                # --------------------------------------------

                if best_name == "Unknown":

                    box_color = (
                        0,
                        0,
                        255
                    )

                else:

                    box_color = (
                        0,
                        255,
                        0
                    )

                cv2.rectangle(
                    frame,
                    (x, y),
                    (
                        x + fw,
                        y + fh
                    ),
                    box_color,
                    2
                )

                label = (
                    f"{best_name} "
                    f"{display_score:.2f}"
                )

                cv2.putText(
                    frame,
                    label,
                    (
                        x,
                        max(
                            y - 10,
                            20
                        )
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    box_color,
                    2
                )

        current_people = detected_people

        ai_online = True

        return frame

    except Exception as e:

        print(
            "[FACE PROCESSING ERROR]",
            e
        )

        ai_online = False

        current_people = []

        return frame


# ============================================================
# PROCESS FRAME
# ============================================================

def process_frame(frame):

    global current_objects

    global object_frame_counter

    object_frame_counter += 1

    # --------------------------------------------------------
    # FACE RECOGNITION
    # --------------------------------------------------------

    frame = process_faces(
        frame
    )

    # --------------------------------------------------------
    # OBJECT DETECTION
    # --------------------------------------------------------

    if (
        object_frame_counter
        %
        OBJECT_DETECTION_INTERVAL
        ==
        0
    ):

        current_objects = (
            detect_objects(
                frame
            )
        )

    # --------------------------------------------------------
    # DRAW OBJECTS
    # --------------------------------------------------------

    draw_objects(
        frame,
        current_objects
    )

    # --------------------------------------------------------
    # DRISHTI LABEL
    # --------------------------------------------------------

    cv2.putText(
        frame,
        "DRISHTI",
        (15, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (40, 255, 156),
        2
    )

    # ========================================================
    # SECURITY ALERT
    # ========================================================

    unknown_people = []

    for person in current_people:

        if (
            person["name"]
            ==
            "Unknown"
        ):

            unknown_people.append(
                person
            )

    # --------------------------------------------------------
    # UNKNOWN PERSON FOUND
    # --------------------------------------------------------

    if unknown_people:

        person = unknown_people[0]

        # The frame already contains:
        # face box + object boxes + labels

        log_security_event(
            "Unknown",
            person["confidence"],
            "UNKNOWN",
            frame.copy(),
            current_objects.copy()
        )

    # --------------------------------------------------------
    # AUTHORIZED PEOPLE
    # --------------------------------------------------------

    else:

        for person in current_people:

            if (
                person["name"]
                !=
                "Unknown"
            ):

                log_security_event(
                    person["name"],
                    person["confidence"],
                    "AUTHORIZED"
                )

    return frame


# ============================================================
# CAMERA STREAM
# ============================================================

def generate_frames():

    global camera_online

    while True:

        try:

            with camera_lock:

                success, frame = (
                    camera.read()
                )

            if not success:

                camera_online = False

                print(
                    "[CAMERA] Frame read failed"
                )

                time.sleep(
                    0.1
                )

                continue

            camera_online = True

            frame = process_frame(
                frame
            )

            success, buffer = (
                cv2.imencode(
                    ".jpg",
                    frame,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        JPEG_QUALITY
                    ]
                )
            )

            if not success:

                continue

            frame_bytes = (
                buffer.tobytes()
            )

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                +
                frame_bytes
                +
                b"\r\n"
            )

        except GeneratorExit:

            break

        except Exception as e:

            print(
                "[STREAM ERROR]",
                e
            )

            time.sleep(
                0.1
            )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    return render_template(
        "dashboard.html"
    )


# ============================================================
# LIVE VIDEO
# ============================================================

@app.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype=(
            "multipart/x-mixed-replace;"
            " boundary=frame"
        )
    )


# ============================================================
# LIVE DATA
# ============================================================

@app.route("/data")
def data():

    return jsonify(
        {
            "success":
                True,

            "people":
                current_people,

            "objects":
                current_objects,

            "registered":
                [
                    x[0]
                    for x in known_faces
                ],

            "camera_online":
                camera_online,

            "ai_online":
                ai_online,

            "object_detection_online":
                object_detection_online,

            "database_online":
                database_online,

            "telegram_online":
                telegram_online,

            "security_alert":
                security_alert,

            "security_alert_name":
                security_alert_name,

            "security_alert_time":
                security_alert_time
        }
    )


# ============================================================
# REFRESH DATABASE
# ============================================================

@app.route("/refresh_database")
def refresh_database():

    success = (
        load_known_faces()
    )

    return jsonify(
        {
            "success":
                success,

            "registered":
                [
                    x[0]
                    for x in known_faces
                ]
        }
    )


# ============================================================
# REGISTER PAGE
# ============================================================

@app.route("/register")
def register():

    return render_template(
        "register.html"
    )


# ============================================================
# SECURITY EVENTS PAGE
# ============================================================

@app.route("/security_events")
def security_events_page():

    return render_template(
        "security_events.html"
    )


# ============================================================
# SECURITY EVENTS API
# ============================================================

@app.route("/api/security_events")
def security_events_api():

    try:

        db = get_db()

        rows = db.execute(
            """
            SELECT
                id,
                person_name,
                confidence,
                event_type,
                timestamp
            FROM security_events
            ORDER BY id DESC
            """
        ).fetchall()

        db.close()

        events = []

        for row in rows:

            events.append(
                {
                    "id":
                        row["id"],

                    "person_name":
                        row["person_name"],

                    "confidence":
                        round(
                            float(
                                row["confidence"]
                            ),
                            2
                        ),

                    "event_type":
                        row["event_type"],

                    "timestamp":
                        row["timestamp"]
                }
            )

        return jsonify(
            {
                "success":
                    True,

                "events":
                    events
            }
        )

    except Exception as e:

        print(
            "[SECURITY EVENTS ERROR]",
            e
        )

        return jsonify(
            {
                "success":
                    False,

                "events":
                    [],

                "error":
                    str(e)
            }
        ), 500


# ============================================================
# SECURITY STATISTICS
# ============================================================

@app.route("/api/security_stats")
def security_stats():

    try:

        db = get_db()

        total = db.execute(
            """
            SELECT COUNT(*)
            FROM security_events
            """
        ).fetchone()[0]

        authorized = db.execute(
            """
            SELECT COUNT(*)
            FROM security_events
            WHERE event_type = 'AUTHORIZED'
            """
        ).fetchone()[0]

        unknown = db.execute(
            """
            SELECT COUNT(*)
            FROM security_events
            WHERE event_type = 'UNKNOWN'
            """
        ).fetchone()[0]

        db.close()

        return jsonify(
            {
                "success":
                    True,

                "total":
                    total,

                "authorized":
                    authorized,

                "unknown":
                    unknown
            }
        )

    except Exception as e:

        print(
            "[STATS ERROR]",
            e
        )

        return jsonify(
            {
                "success":
                    False,

                "total":
                    0,

                "authorized":
                    0,

                "unknown":
                    0,

                "error":
                    str(e)
            }
        ), 500


# ============================================================
# CLEAR SECURITY EVENTS
# ============================================================

@app.route(
    "/api/clear_security_events",
    methods=["POST"]
)
def clear_security_events():

    try:

        db = get_db()

        db.execute(
            "DELETE FROM security_events"
        )

        db.commit()

        db.close()

        return jsonify(
            {
                "success":
                    True,

                "message":
                    "Security events cleared"
            }
        )

    except Exception as e:

        print(
            "[CLEAR EVENTS ERROR]",
            e
        )

        return jsonify(
            {
                "success":
                    False,

                "message":
                    str(e)
            }
        ), 500


# ============================================================
# SYSTEM STATUS
# ============================================================

@app.route("/api/status")
def system_status():

    return jsonify(
        {
            "camera":
                "ONLINE"
                if camera_online
                else "OFFLINE",

            "ai":
                "ONLINE"
                if ai_online
                else "OFFLINE",

            "object_detection":
                "ONLINE"
                if object_detection_online
                else "OFFLINE",

            "database":
                "ONLINE"
                if database_online
                else "OFFLINE",

            "telegram":
                "ONLINE"
                if telegram_online
                else "OFFLINE",

            "registered_people":
                len(
                    known_faces
                ),

            "current_face_detections":
                len(
                    current_people
                ),

            "current_object_detections":
                len(
                    current_objects
                )
        }
    )


# ============================================================
# TELEGRAM TEXT TEST
# ============================================================

@app.route("/api/test_telegram")
def test_telegram():

    if not NOTIFICATION_SERVICE_AVAILABLE:

        return jsonify(
            {
                "success":
                    False,

                "telegram_online":
                    False,

                "error":
                    "notification_service.py unavailable"
            }
        ), 500

    try:

        result = send_telegram_message(
            "🚨 DRISHTI TEST ALERT 🚨\n\n"
            "Telegram notification system is connected successfully."
        )

        success = (
            result is True
        )

        return jsonify(
            {
                "success":
                    success,

                "telegram_online":
                    success
            }
        )

    except Exception as e:

        print(
            "[TELEGRAM TEST ERROR]",
            e
        )

        return jsonify(
            {
                "success":
                    False,

                "telegram_online":
                    False,

                "error":
                    str(e)
            }
        ), 500


# ============================================================
# TELEGRAM PHOTO TEST
# ============================================================

@app.route("/api/test_telegram_photo")
def test_telegram_photo():

    if not NOTIFICATION_SERVICE_AVAILABLE:

        return jsonify(
            {
                "success":
                    False,

                "telegram_online":
                    False,

                "error":
                    "notification_service.py unavailable"
            }
        ), 500

    try:

        # ----------------------------------------------------
        # Capture a fresh camera frame
        # ----------------------------------------------------

        with camera_lock:

            success, frame = camera.read()

        if not success:

            return jsonify(
                {
                    "success":
                        False,

                    "telegram_online":
                        False,

                    "error":
                        "Could not capture camera frame"
                }
            ), 500

        # ----------------------------------------------------
        # Save test image
        # ----------------------------------------------------

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        image_path = os.path.join(
            ALERT_DIRECTORY,
            f"telegram_test_{timestamp}.jpg"
        )

        saved = cv2.imwrite(
            image_path,
            frame
        )

        if not saved:

            return jsonify(
                {
                    "success":
                        False,

                    "telegram_online":
                        False,

                    "error":
                        "Could not save test image"
                }
            ), 500

        # ----------------------------------------------------
        # Send test photo
        # ----------------------------------------------------

        result = send_telegram_photo(
            image_path,
            "🚨 DRISHTI PHOTO TEST 🚨\n\n"
            "Telegram photo notification system "
            "is connected successfully."
        )

        success = (
            result is True
        )

        global telegram_online

        telegram_online = success

        return jsonify(
            {
                "success":
                    success,

                "telegram_online":
                    success,

                "image":
                    image_path
            }
        )

    except Exception as e:

        print(
            "[TELEGRAM PHOTO TEST ERROR]",
            e
        )

        return jsonify(
            {
                "success":
                    False,

                "telegram_online":
                    False,

                "error":
                    str(e)
            }
        ), 500


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print()

    print(
        "=========================================="
    )

    print(
        "        DRISHTI SECURITY SYSTEM"
    )

    print(
        "=========================================="
    )

    print()

    print(
        "Dashboard:"
    )

    print(
        "http://127.0.0.1:5000/"
    )

    print()

    print(
        "Security Events:"
    )

    print(
        "http://127.0.0.1:5000/security_events"
    )

    print()

    print(
        "Telegram Text Test:"
    )

    print(
        "http://127.0.0.1:5000/api/test_telegram"
    )

    print()

    print(
        "Telegram Photo Test:"
    )

    print(
        "http://127.0.0.1:5000/api/test_telegram_photo"
    )

    print()

    print(
        "Object Model:",
        OBJECT_MODEL
    )

    print()

    print(
        "Registered people:",
        [
            x[0]
            for x in known_faces
        ]
    )

    print()

    print(
        "Telegram service:",
        "AVAILABLE"
        if NOTIFICATION_SERVICE_AVAILABLE
        else "UNAVAILABLE"
    )

    print()

    print(
        "=========================================="
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )