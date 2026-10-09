# API

All routes are under `/api`. Interactive OpenAPI: `/docs`; JSON schema: `/openapi.json`.

## Authentication

- `GET /api/health`: public status and whether first-run setup is required.
- `POST /api/auth/setup`: `{ "username": "yourname", "password": "your-long-password" }`; available only before any account exists.
- `POST /api/auth/login`: same body; sets HttpOnly, SameSite=Strict cookie `spatial_session` (eight-hour expiry).
- `GET /api/auth/me`: current username and role.
- `POST /api/auth/logout`: revoke session.

Cookies are used for REST and WebSockets; no credentials go into stream URLs. Browser Origin and Host are checked. Use the browser login page before `/docs`, or retain the cookie in your API client. Passwords must be 10–128 characters. Five login attempts per username per minute are permitted. Restarting the server invalidates all login sessions.

## Main resources

| Method | Path | Role | Result |
|---|---|---|---|
| GET/PUT | `/api/config` | reader/operator | Validated settings; PUT applies next session |
| GET | `/api/models` | reader | Installed runtime and allowed model availability |
| POST | `/api/upload` | operator | Multipart `file`, 200 MB maximum, returned file_id |
| POST | `/api/sessions` | operator | Start source; `{kind: demo/video/webcam/rtsp, value: string}` |
| GET | `/api/sessions` | reader | Latest 100 sessions and stored frame counts |
| DELETE | `/api/sessions/{id}` | operator | Delete inactive session and recording files |
| POST | `/api/control` | operator | `{action: pause/resume/stop/record_on/record_off}` |
| GET | `/api/state` | reader | Latest analysis without JPEG |
| GET | `/api/snapshot` | reader | JPEG of current displayed frame without browser overlays |
| GET | `/api/tracks?session_id=…` | reader | Latest live or persisted session track states |
| GET | `/api/events` | reader | Filter by session_id, q, severity, track, limit (max 500) |
| GET | `/api/scenes?session_id=…` | reader | Live summary or recorded samples |
| POST | `/api/waypoints` | operator | `{name,x,z}` for current simulated session |
| GET | `/api/replay/{id}` | reader | Ordered `{seq,timestamp}` frame index |
| GET | `/api/replay/{id}/{seq}` | reader | Exact saved `{state,image}` (JPEG base64) |
| GET | `/api/export/{id}?format=csv` | reader | Recorded periodic metric samples (or format=json) |

Source examples: demo value empty; webcam value `"0"`; uploaded video value returned file_id; RTSP value `"rtsp://host/path"`. Starting a source asynchronously returns a session ID while models load. Observe status and errors through `/api/state` or the socket.

## WebSockets

`/ws/live` sends `{state,image}`. `image` is base64 JPEG or null. Each state carries a `session_id`, `seq`, capture timestamp, source-frame index, width/height, tracks, sensor status, scene, recent events, navigation, recording status and runtime metrics.

`/ws/tracks`, `/ws/events`, and `/ws/system` expose the corresponding lightweight state sections. Authentication uses the same browser cookie. Expired sessions close with code 1008. Clients should retry transient failures with backoff, but return to login after 1008.

## Semantics

- Track IDs are scoped to a session. `confidence_kind` distinguishes model scores from synthetic color matching.
- `position` is null unless approximate ranging is possible/enabled.
- Missing sensor readings and unmeasured metrics are null/unavailable, not zero.
- `frame_note` labels synthetic or RGB pseudocolor imagery.
- Replay snapshots reproduce recorded analysis; timestamps may be irregular due to dropped capture frames.
- Events use IDs, Unix timestamps, type, severity, description, and optional related_track_id.
