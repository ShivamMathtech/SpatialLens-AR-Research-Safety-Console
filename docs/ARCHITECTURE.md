# Architecture

## Runtime

Browser → authenticated REST + WebSocket → FastAPI → one source/inference worker.

Capture runs in its own daemon thread and writes a queue with **capacity one**. When full it replaces the old frame and increments the dropped-frame counter. The inference worker performs detection every configured N processed frames, updates track state, estimates optional camera-relative distance, analyzes brightness, emits events, encodes a JPEG, and publishes the latest state. The browser reads the latest packet and draws interpolated overlays with requestAnimationFrame (about 30 updates/second). Network throughput, inference, and browser rendering have different rates.

Capture and inference never run on FastAPI's async event loop. Blocking REST actions are ordinary synchronous FastAPI routes. WebSocket send operations are time-limited and each client polls one latest snapshot; there is no queued backlog of outgoing historical frames. A large frame/state packet is intended for local use, not a bandwidth-constrained public service.

## Modules

| Path | Responsibility |
|---|---|
| backend/app/core/config.py | Validated settings and persisted overrides |
| backend/app/core/db.py | SQLAlchemy schema and SQLite WAL configuration |
| backend/app/core/security.py | scrypt passwords, in-memory expiring sessions, roles |
| backend/app/cv/interfaces.py | Replaceable detector/tracker/depth/segmenter/pose contracts |
| backend/app/cv/synthetic.py | Deterministic images and color-component detection |
| backend/app/cv/yolo.py | Lazy model loading, CPU/CUDA selection, ByteTrack/BoT-SORT |
| backend/app/cv/tracking.py | Association, bounded history, interpolation state |
| backend/app/cv/spatial.py | Approximate range, coordinate transform, scene heuristics, display filters |
| backend/app/services/pipeline.py | Source lifecycle, capture/inference, persistence |
| backend/app/services/navigation.py | Simulated local coordinates and checkpoints |
| backend/app/services/events.py | Lifecycle event generation and bounded recent timeline |
| backend/app/services/telemetry.py | Best-effort measurements with explicit unavailable values |
| frontend/src/stores | Separate live, view preference, and configuration stores |
| frontend/src/components | Connected viewport, map/panels, Three.js, replay, settings |

## Coordinate conventions

Image coordinates: x right, y down, pixels. Camera-relative coordinates: x right, y up, z forward, approximate metres. Local simulated ground: x right/east, z forward/north; Three.js displays forward as negative z. `camera_to_world` implements a yaw transform plus translation, ready for a future trusted pose adapter. Current live camera input does not claim a world position.

The estimator uses `Z = f_pixels × assumed_object_height / observed_box_height`. Truncation, orientation, camera tilt, class-size variation and detector errors can dominate. It requires opt-in calibration on real sources. The displayed ±40% is a warning-scale heuristic, not measured statistical coverage. Unknown class heights yield no estimate.

## Tracking

The demo detector does not return identity: IoU association preserves IDs across moving image components. For actual camera/video input, Ultralytics returns tracker IDs. A separate smoothing layer retains these IDs and limits trajectory history. Prediction covers short intervals only; tracks expire after configured missed detections or three seconds. Pixel speed is derived from image displacement, not converted into km/h.

## Persistence and replay

Sessions record metadata. Recording persists JPEG + a JSON analysis state in the same inference iteration, with normalized snapshots in frames, tracks, track_points, detections, scenes, sensor_status, system_metrics, and waypoints. Events persist whether or not frame recording is enabled. Frame state is authoritative for replay, including event history, navigation, scene, sensors, tracks and metric values. Replay never calls a detector.

The default per-session limit is 1,800 frames (about 150 seconds at 12 FPS). At that limit frame persistence stops, an event is emitted, and the live pipeline continues. Disk usage varies with resolution and frame content. There is no automatic global recording purge; delete old sessions explicitly. SQLite uses WAL and short transactions. File/database writes are not crash-atomic together: abrupt machine failure may leave an orphan JPEG. Missing replay images return HTTP 410.

## Failure behavior

Model imports are lazy; demo startup never requires PyTorch. Missing models, invalid videos, or disconnected cameras become explicit error states/events. Network stream opening/reading has timeouts. WebSocket clients reconnect after transient disconnection. Source reconnect is a user action; network capture does not silently loop indefinitely. CPU telemetry failure produces null values and does not stop inference. General database/capture exceptions stop the affected session with an error, leaving APIs and frontend running where possible.

## Scope and evolution

One process and one live source at a time. No distributed source coordination, multiple camera fusion, semantic segmentation, dense depth network, SLAM, geospatial mapping, real environment sensors, sensor battery measurement, or ground-truth evaluation is included. Add these via the documented interfaces and maintain provenance in each result. Postgres schema compatibility is provided but requires deployment testing.
