# SpatialLens — AR Research & Safety Console

A runnable local computer-vision working model inspired by the supplied dark cyan HUD layout. Built with React, TypeScript, Vite, Three.js, FastAPI, OpenCV, WebSockets, and SQLite/SQLAlchemy. This is a civilian observation and research adaptation, with general object categories and no combat classifications or weapon integration.

## Start on Windows

1. Install **64-bit Python 3.11** from https://www.python.org/downloads/ with the Python Launcher enabled.
2. Extract the ZIP fully into a writable folder, such as `C:\Projects\SpatialLens`. Do not run it inside the ZIP viewer.
3. Double-click **`setup_windows.bat`**. Internet is needed to install Python packages.
4. Double-click **`start_demo.bat`**. The dashboard opens at **http://127.0.0.1:8000**.
5. Create your own operator account. There are no shipped credentials.
6. Leave **Synthetic demo** selected and click **Start**.

The prebuilt frontend is included. **Node.js, Docker, GPU, camera, and model weights are not needed for the synthetic demo.** After dependency installation the demo works offline. Start/stop/pause, recording, overlays, selectable tracks, simulated navigation, maps, 3D, replay, and exports are connected to the backend.

The synthetic scene is procedurally generated, and a color-component detector actually analyzes its pixels. Its confidence is a color-match score, **not YOLO accuracy**. A short synthetic video and annotations are included in `datasets/`.

## Real webcam, video, or RTSP with YOLO

1. Stop the server.
2. Run **`install_ai.bat`**. This installs CPU PyTorch, Ultralytics, ByteTrack dependencies, and downloads `models/yolov8n.pt` from the model provider. Downloads require internet and several hundred MB of free space. Model weights are not bundled.
3. Start the app again. In Settings, confirm that the model is available.
4. Choose **Laptop webcam** (index `0` normally), **Uploaded video**, or **RTSP stream**. Upload a supported video if needed, then click **Start**.

Real inputs always use YOLO; missing AI packages or weights produce an actionable error, never silently generated detections. Webcam means the camera attached to the **backend computer**, not a remote browser. Video input is paced at source FPS; frames may be skipped to keep latency low. An uploaded clip ends naturally. Start it again to replay from the beginning with new inference.

The shipped YOLO adapter uses `model.track(..., persist=True)` with ByteTrack or BoT-SORT, followed by temporal smoothing and bounded trajectories. COCO weights detect their trained general categories; **buildings and bridges are not supported COCO classes**. Better/custom detectors can be added behind `cv/interfaces.py`.

## Linux / macOS

```
Username: ssingh64631
Password: Singh@64631X
```

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Linux may need system OpenGL libraries for OpenCV (`libgl1` and `libglib2.0-0`). Use `python run.py --no-browser --port 8001` to choose another port. Run one application process; the local video pipeline is process-owned.

Optional CPU AI installation:

```bash
python -m pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-ai.txt
python scripts/download_models.py
```

For NVIDIA GPU use, install a PyTorch build compatible with your CUDA driver using https://pytorch.org/get-started/locally/, then select `auto` or `cuda` in Settings. `auto` falls back to CPU. Explicit `cuda` reports an error if unavailable. GPU hardware has not been validated by this project.

## Daily workflow

- **Console:** source control, live video, smoothed boxes/trails, source status, current events, sensor availability.
- **Tracks:** select an object to view confidence, pixel velocity, first/last seen, and trajectory history. Track IDs are local to a session.
- **Local map:** simulated route and camera-relative object positions. Add local checkpoints in demo mode. Map/satellite/topographic are **offline drawing styles**, not actual imagery or geographic maps.
- **3D scene:** orbit/pan/zoom, top/front/side views, follow a selected track. Ground, demo buildings, approximate object positions and simulated waypoints are visualized. This is not SLAM.
- **Events:** search and filter the most recent 100 current-session events. The authenticated REST API also queries persisted events. Historical events appear with each replay frame.
- **Research:** actual processing timings, rolling latency/P95, FPS, CPU/RAM when available, dropped capture frames, active track age, CSV/JSON export. Unmeasured metrics remain unavailable.
- **Replay:** choose a recorded session, play/pause, step in either direction, scrub, and change speed. Stored image/state pairs are loaded without inference. Nominal replay speed is capped by local read/decode speed.
- **Settings:** validated persistent configuration. Save, then restart the input source to apply.

Snapshot saves the displayed frame with overlays. Recording stores JPEG frames and analysis in `data/recordings` and SQLite; it does not produce an MP4 container. Original uploaded video is retained under `data/uploads`. Delete sessions from Replay to free recordings. Remove old uploaded files manually when they are no longer needed.

## Honest capability boundaries

| Area          | Working implementation                                                              | Not represented as available                                                   |
| ------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Detection     | Synthetic component detector; optional pretrained YOLO adapter                      | No custom military/terrain/object-intent model                                 |
| Tracking      | Demo IoU association; real-input ByteTrack/BoT-SORT; smoothing and short prediction | Cross-camera identity or guaranteed ID consistency                             |
| Depth         | Explicitly enabled pinhole / assumed-object-height approximation                    | Learned dense depth, measured range, SLAM, GPS-grade coordinates               |
| Distance      | Camera-relative estimate with ±40% heuristic uncertainty                            | Empirically calibrated confidence intervals or physical object speed           |
| Navigation    | Simulated local pose, checkpoints and breadcrumb history                            | Real GPS/IMU navigation or route planning                                      |
| Sensors       | Truthful online/offline/simulated status                                            | Hardware thermal, depth, environmental and radio measurements                  |
| Thermal/night | Clearly labeled RGB pseudocolor / contrast filters                                  | Thermal or infrared sensing                                                    |
| Scene         | Measured brightness and simple density/scene-change heuristics                      | Semantic segmentation, terrain/visibility/weather classification               |
| Research      | Runtime metrics and exports                                                         | Accuracy benchmarks, ground-truth ID switches, evaluated trajectory smoothness |
| Deployment    | Local single-operator pipeline; viewer accounts; SQLite                             | Production HA, distributed/multi-camera service, security certification        |

The `Segmenter`, `PoseEstimator`, and environment interfaces are extension points. They are not pretrained models hidden behind a demo label. The implementation does not claim to satisfy unimplemented advanced research modules from the broader brief.

## Developer commands

```bash
# API including interactive docs
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# http://127.0.0.1:8000/docs

# Only needed when modifying the frontend; Node.js 20.19+ or current LTS
npm --prefix frontend ci
npm --prefix frontend run dev
npm --prefix frontend run build

# Automated checks
python -m pytest
npm --prefix frontend test

# Optional browser regression suite (starts its own server; port 8000 must be free)
cd frontend
npx playwright install chromium
npx playwright test
```

Browser checks use a dedicated `data-browser-test` folder and a test-only account. Never point this test data path at a real workspace. For the optional actual-model test, set `SPATIALLENS_TEST_AI=1` and run `python -m pytest tests/test_optional_yolo.py` after AI setup.

`start_backend.bat` and `start_frontend.bat` support separate development servers. The Vite proxy keeps API/WS calls on the same browser origin.

## Configuration & persistence

Defaults live in `config/*.yaml`. Settings saved through the app go to `data/settings.yaml` and override defaults. `.env.example` documents optional environment values. `SPATIAL_DATA_DIR` relocates all user recordings, uploads, accounts and database storage. Do not commit `data/`, `.env`, or credentials.

SQLite initializes on first launch. Alembic migration `0001` is supplied:

```bash
python -m alembic upgrade head
```

For PostgreSQL, install `psycopg[binary]`, set `DATABASE_URL`, and run the migration. PostgreSQL compatibility is designed into the SQLAlchemy schema but has not been integration-tested against a server.

Create a viewer or reset a local account from a terminal:

```bash
python scripts/create_user.py colleague --role viewer
python scripts/create_user.py yourname --role operator --reset
```

Passwords are entered interactively and hashed with scrypt. Restart the server after a password reset to revoke existing in-memory sessions. Operator accounts control sources/settings/deletion; viewers can inspect and export recordings. The server binds to localhost. Remote use requires your own HTTPS reverse proxy, allowed-host configuration, and deployment review.

## Documentation

- `docs/ARCHITECTURE.md` — modules, data flow, persistence and extension points
- `docs/API.md` — authentication, REST, WebSockets and replay
- `docs/TROUBLESHOOTING.md` — Windows, camera, models and dependencies
- `docs/VALIDATION.md` — checks actually performed and remaining test limits
- `docs/THIRD_PARTY.md` — model/package license notes and official references

This deliverable is a tested working model, not a claim of production certification or validated safety-critical performance.
