# DRISHTI — AI-Powered Object Detection & Intelligent Surveillance

<p align="center">
  <strong>SEE · DETECT · PROTECT</strong>
</p>

<p align="center">
  Real-time object detection, face recognition, security-event logging, and Telegram alerts.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/OpenCV-Computer%20Vision-green" alt="OpenCV">
  <img src="https://img.shields.io/badge/YOLO11-Object%20Detection-purple" alt="YOLO11">
  <img src="https://img.shields.io/badge/Flask-Web%20Dashboard-black?logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/SQLite-Database-blue" alt="SQLite">
</p>

---

## Overview

**DRISHTI** is an AI-powered surveillance application that combines computer vision, face recognition, and remote security notifications in a single system.

The application processes video from a connected camera, detects objects using **YOLO11**, and recognizes faces using OpenCV's **YuNet** and **SFace** models. Registered face embeddings are loaded from a local SQLite database.

When an unknown face is detected, DRISHTI records a security event, saves a snapshot, and attempts to send a Telegram notification with event details and an image.

A Flask web dashboard provides access to the camera feed, detection results, system status, and security-event history.

## Features

### Object Detection
- YOLO11 object detection using `yolo11s.pt`
- Detection of multiple objects in camera frames
- Bounding boxes, object labels, and confidence scores
- Configurable detection confidence threshold
- Detection performed every second frame to reduce processing load

### Face Detection & Recognition
- Face detection using OpenCV YuNet
- Face alignment and feature extraction using OpenCV SFace
- Matching against registered face embeddings
- Display of recognized names
- Classification of unmatched faces as unknown

### Security Monitoring
- Automatic logging of authorized and unknown face events
- Timestamped security records
- Snapshot capture for unknown-face events
- Cooldown handling to reduce repeated alerts

### Web Dashboard
- Flask-based dashboard
- Live camera feed
- Face-recognition and object-detection results
- Registered-person information
- System component status
- Security-event history and statistics

### Telegram Notifications
- Text notifications
- Photo notifications with captions
- Security snapshots saved as JPEG images
- Background notification delivery
- Endpoints for testing notification functionality

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| OpenCV | Camera capture and computer vision |
| Ultralytics YOLO11 | Object detection |
| YuNet | Face detection |
| SFace | Face feature extraction and matching |
| NumPy | Numerical operations |
| Flask | Web dashboard and API |
| SQLite | Local database |
| Requests | Telegram Bot API communication |
| HTML, CSS, JavaScript | Dashboard interface |
| KiCad | PCB design |

## System Architecture

```text
                   USB CAMERA
                       |
                       v
               OPENCV VIDEO CAPTURE
                       |
                       v
                   VIDEO FRAME
                  /           \
                 v             v
          YUNET FACE        YOLO11 OBJECT
           DETECTION         DETECTION
                 |             |
                 v             v
          SFACE FEATURES    OBJECT LABELS
                 |          AND BOUNDING BOXES
                 v
       REGISTERED FACE DATABASE
                 |
           +-----+-----+
           |           |
           v           v
      AUTHORIZED     UNKNOWN
           |           |
           v           v
       EVENT LOG    SECURITY EVENT
                         |
                   +-----+-----+
                   |           |
                   v           v
              SQLITE LOG   SAVE SNAPSHOT
                               |
                               v
                      TELEGRAM NOTIFICATION

                    FLASK DASHBOARD
               Live video, detections and events
```

## Repository Structure

```text
DRISHTI-Edge-AI-Security/
│
├── app.py
├── notification_service.py
├── register_face.py
├── face_test.py
├── recognize_test.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── models/
│   ├── face_detection_yunet_2023mar.onnx
│   └── face_recognition_sface_2021dec.onnx
│
├── templates/
│   ├── dashboard.html
│   ├── register.html
│   └── security_events.html
│
├── static/
│
└── docs/
    └── hardware/
```

This is the intended structure. Keep only files that actually exist in your repository.

**Model path:** The current `app.py` expects `yolo11s.pt` in the project root. The YuNet and SFace models are expected inside `models/`.

Do not upload private face data, populated databases, security snapshots, credentials, or your Python virtual environment.

## Installation

### Prerequisites

- Python 3
- Git
- A supported webcam
- Required AI model files
- A Telegram bot and destination chat ID, if notifications are required

### 1. Clone the Repository

```bash
git clone https://github.com/itsmeGaurav07/DRISHTI-Edge-AI-Security.git
cd DRISHTI-Edge-AI-Security
```

### 2. Create a Virtual Environment

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / Raspberry Pi OS**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Ensure `requirements.txt` includes the required packages, including Flask, OpenCV, NumPy, Requests, and Ultralytics.

### 4. Verify the Model Files

```text
yolo11s.pt
models/face_detection_yunet_2023mar.onnx
models/face_recognition_sface_2021dec.onnx
```

Make sure the files exist at the expected paths and are compatible with your installed dependencies.

### 5. Configure Telegram

Configure the Telegram bot token and destination chat ID using environment variables.

**Never hardcode real credentials in your source code or publish them on GitHub.**

### 6. Run the Application

```bash
python app.py
```

Open the dashboard in your browser:

**http://127.0.0.1:5000**

The current application binds to `127.0.0.1`, so it is configured for local access. Access from other devices requires a deliberate network configuration change and appropriate security controls.

## Face Recognition Workflow

DRISHTI loads registered face records from the SQLite `persons` table using the fields `name` and `face_embedding`.

The recognition process follows these steps:

1. YuNet detects a face in the camera frame.
2. SFace aligns the detected face.
3. SFace extracts a numerical face feature.
4. The feature is compared against registered face embeddings.
5. The best matching identity is evaluated against the configured threshold.
6. The face is classified as registered or unknown.
7. The result is displayed on the camera feed.

The current recognition threshold is `0.363`.

A face-matching score is not proof of identity. Recognition should be evaluated under different lighting conditions, camera angles, distances, and environments.

Only register faces with appropriate permission and protect stored biometric information.

## Security Events

The application records two event types:

| Event Type | Meaning |
|---|---|
| `AUTHORIZED` | A registered face matched the configured threshold |
| `UNKNOWN` | A detected face did not match a registered face at the configured threshold |

The `security_events` table stores:

- Event ID
- Person name
- Face-matching score
- Event type
- Timestamp

Event logging uses a 30-second per-event/person cooldown. Telegram notifications have separate cooldown handling.

**Current implementation note:** The supplied `app.py` detects unknown faces and generates alerts. Configurable secured-zone boundaries and physical zone-entry detection are not implemented in that file.

## Telegram Notifications

For an unknown face, the application attempts to:

1. Record the security event.
2. Save a JPEG snapshot in `security_alerts/`.
3. Generate an alert caption containing event details.
4. Include information about other detected objects.
5. Send a photo notification through Telegram.
6. Attempt a text notification if the snapshot cannot be saved.

### Notification Testing

| Endpoint | Purpose |
|---|---|
| `/api/test_telegram` | Test a Telegram text notification |
| `/api/test_telegram_photo` | Test a Telegram photo notification |

For example:

```text
http://127.0.0.1:5000/api/test_telegram
```

These endpoints initiate real notification attempts. Use them only when you intend to send a test message.

## Dashboard & API Endpoints

| Endpoint | Purpose |
|---|---|
| `/` | Main dashboard |
| `/video_feed` | Live MJPEG camera feed |
| `/data` | Current detections and system status |
| `/register` | Face-registration page |
| `/refresh_database` | Reload registered face embeddings |
| `/security_events` | Security-event page |
| `/api/security_events` | Retrieve event history |
| `/api/security_stats` | Retrieve event statistics |
| `/api/status` | Retrieve component status |
| `/api/test_telegram` | Test Telegram text delivery |
| `/api/test_telegram_photo` | Test Telegram photo delivery |
| `/api/clear_security_events` | Clear recorded security events |

The notification-testing endpoints and event-clearing endpoint perform actions. Do not expose them to untrusted networks without appropriate authentication and authorization.

## Hardware & PCB Design

DRISHTI also includes PCB design work using **KiCad**.

Hardware documentation can include:

- PCB layout screenshots
- 3D PCB renders
- Circuit schematics
- Component and connector descriptions
- Bill of Materials
- Gerber fabrication files, if available

Suggested documentation structure:

```text
docs/
└── hardware/
    ├── pcb-layout.png
    ├── pcb-3d-view.png
    └── hardware-notes.md
```

Document the PCB's electrical functions using the actual schematic and tested connections.

## Raspberry Pi Deployment

Raspberry Pi is an intended edge-computing platform for DRISHTI.

Before deployment, verify the complete application on the target hardware:

1. Test the camera independently.
2. Confirm YuNet and SFace initialize correctly.
3. Confirm the YOLO11 model loads.
4. Verify database initialization and face registration.
5. Test face recognition and event logging.
6. Test Telegram notification delivery.
7. Verify dashboard streaming and API responses.
8. Measure processing latency and stability.

Performance depends on the Raspberry Pi model, operating system, model execution, camera settings, and overall processing load. Benchmark the complete pipeline before making real-time performance claims.

## Future Enhancements

- Configurable secured-zone monitoring
- Restricted-area entry alerts
- Improved multi-person tracking
- Event filtering, exports, and reporting
- Dashboard authentication and access controls
- Improved event deduplication
- Raspberry Pi performance optimization
- Automated deployment and service startup
- FPGA-assisted image processing or inference using a compatible PYNQ platform

These are proposed enhancements, not claims about the current implementation.

## Security & Privacy

- Never commit bot tokens, API credentials, passwords, or populated `.env` files.
- Exclude `drishti.db` and private face embeddings.
- Do not publish registered face images or private security recordings.
- Exclude `venv/`, `__pycache__/`, and temporary output files.
- Review model licensing and redistribution terms before publishing model weights.
- Protect dashboard action endpoints with appropriate access controls.
- Obtain appropriate permission before collecting biometric information.
- Revoke and replace any credential that has been exposed.

## Project Information

**Project:** DRISHTI — AI-Powered Object Detection & Intelligent Surveillance

**Domains:** Edge AI · Computer Vision · Embedded Systems · IoT · Intelligent Security

**Developer:** Gaurav Sai V.

**GitHub:** [DRISHTI-Edge-AI-Security](https://github.com/itsmeGaurav07/DRISHTI-Edge-AI-Security)

---

<p align="center">
  <strong>DRISHTI — SEE · DETECT · PROTECT</strong>
</p>
