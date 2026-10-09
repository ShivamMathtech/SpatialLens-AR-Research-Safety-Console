# Validation record

Validated in a Linux execution environment using Python 3.12, Node.js 24.19.0, and Chromium 134. The Windows scripts target Python 3.11 but have **not** been executed on physical Windows hardware.

## Completed checks

| Check | Outcome |
|---|---|
| Python compile/import | Passed |
| FastAPI/OpenAPI app startup | Passed |
| Python suite, including optional real YOLO model test | **9 passed** |
| Frontend unit checks | **2 passed** |
| TypeScript + Vite production build | Passed; prebuilt dist included |
| Chromium connected end-to-end test | **1 passed** |
| Desktop and 390px mobile screenshots | Rendered and visually inspected |
| Initial Alembic migration on fresh SQLite database | Passed |

The nine Python tests cover generated-image detection with stable IDs; calibration gating and coordinate transforms; track expiration/event generation; authentication and Origin validation; live demo, pause/resume, WebSocket JPEGs, snapshot, recording, saved replay state, metric export, deletion; recording limits; viewer access control; invalid video rejection; and actual CPU YOLO inference/tracker IDs.

The browser test creates a test-only operator account, starts the demo, observes four tracks, pauses/resumes, opens track details, adds a waypoint, switches map styles, opens the Three.js scene, uses its view controls, opens research metrics, saves settings, stops capture, loads replay, steps/plays/pauses, and verifies no page-wide horizontal overflow at 390 pixels. No uncaught browser JavaScript errors were reported.

## Actual detector smoke test

Tested **Ultralytics 8.3.203**, **PyTorch 2.6.0+cpu**, **torchvision 0.21.0+cpu**, official **yolov8n.pt**, and ByteTrack on the upstream Ultralytics bus sample. The adapter returned four observations in the person/bus categories, with IDs `[1,2,3,4]` maintained over two identical frames. This checks model integration only; it is not an accuracy benchmark or evaluation on the user's footage. The sample image and weights are not bundled.

The model download path now validates the ZIP-format checkpoint and its internal archive checksums before reporting success. A truncated download during development was detected and replaced before running the smoke test.

## Pinned runtime checked

- FastAPI 0.116.1 / Starlette 0.47.3
- NumPy 2.2.6 / OpenCV 4.11.0.86
- SQLAlchemy 2.0.43
- Python dependencies in `requirements.txt`
- Frontend exact dependency graph in `frontend/package-lock.json`

An upstream AnyIO deprecation warning occurs in the test client; it did not fail the suite. Process-level telemetry is unavailable in this execution environment and correctly renders as unavailable. Synthetic processing in the inspected desktop run followed the configured 12 FPS target; this is not a performance guarantee on another computer.

## Not validated here

Physical Windows installation, real webcam/RTSP devices, NVIDIA GPU, PostgreSQL server, Docker runtime, real GPS/IMU/depth/thermal/environmental hardware, prolonged multi-hour operation, adversarial security assessment, learned dense depth, segmentation, SLAM, object accuracy/ID-switch benchmarks, or safety-critical operation.

This is a working local research model with explicit extensions/limitations, not a certified production or navigation system.
