# Troubleshooting

## Python and Windows

Use Python **3.11, 64-bit**. `setup_windows.bat` calls `py -3.11` explicitly to avoid accidentally using Python 3.14 or another interpreter lacking matching scientific-package wheels. Check installed versions with `py -0p`. If an earlier environment was created with a different interpreter, rename/remove only this project's `.venv` and run setup again.

Errors about building NumPy, Rust or Visual Studio usually indicate that pip could not obtain a compatible wheel. Confirm Python 3.11 64-bit, update pip, and check connectivity to PyPI. Packages are pinned in requirements.txt.

## Page does not open

Keep the server terminal open. Visit `http://127.0.0.1:8000` manually. If that port is in use: `.venv\Scripts\python.exe run.py --port 8001`. Run from the extracted project; scripts use their own directory. If startup reports a missing DLL, install Microsoft's supported Visual C++ runtime for your Python/Windows environment.

## Missing model / YOLO not installed

Run `install_ai.bat`. It deliberately installs CPU PyTorch first, then the optional detector dependencies and model. Proxy/firewall restrictions can block model-provider downloads. If you already have trusted official weights, place the exact `yolov8n.pt` or `yolo11n.pt` file in `models/`. Never rename an unrelated model. Restart the server after installing packages.

Only one OpenCV distribution should own the `cv2` namespace. This package uses `opencv-python`. Do not add `opencv-python-headless` to the same environment; if both were installed, uninstall both and reinstall the requirements.

## Webcam unavailable

Close other camera applications, enable Windows camera permissions for desktop apps, and try indices 0/1/2. The backend computer must have the camera. Remote browser cameras are not captured by this version. A capture failure appears in the UI; reconnect and press Start again.

## RTSP cannot open

Verify the stream in a local media player and confirm that your computer can reach the device. The stream adapter accepts only rtsp/rtsps schemes. FFmpeg-backed support depends on your OpenCV build. Use a video file or webcam if your device needs a custom transport adapter. URLs can contain device credentials; the app does not save them in session metadata or browser storage.

## Video upload fails

Maximum upload size is 200 MB. MP4, AVI, MOV, MKV and WebM extensions are allowed, but decoding depends on installed codecs. Convert unsupported footage to H.264 MP4 or MJPEG AVI. A malformed file is rejected before inference. The bundled synthetic AVI is a pipeline sample, not a natural-image YOLO accuracy benchmark.

## Low FPS or delayed overlays

Select CPU or Auto, use `yolov8n.pt`, reduce width to 640, target 8–12 FPS, or increase detection interval. No fixed FPS is guaranteed. Capture deliberately replaces older frames. The browser runs separately; database recording can reduce processed FPS. Turn off REC to compare. High dropped-frame counts alone are expected if capture is 30 FPS and processing is 12 FPS.

## Replay empty or recording stops

Enable recording before or during the session. The default storage cap is 1,800 frames. A stopped recording does not stop monitoring. Refresh the replay session list to update frame counts. Deleting a session removes its database observations and stored JPEGs, but not original uploaded media.

## Distance is unavailable / unexpected

Real video has metric distance disabled by default. Enable calibration only after measuring focal length for the selected capture resolution. The estimator assumes typical object height and is not reliable for cropped, tilted or distant objects. Unknown classes do not receive range estimates. The displayed uncertainty is a heuristic. GPS/IMU and ground-truth physical speed are not inferred from RGB images.

## 3D page fails

Enable browser hardware acceleration/WebGL or use the local map. The 3D page reports an unavailable-WebGL message instead of stopping the app. GPU inference and browser WebGL are independent.

## Sign-in trouble

Usernames use letters, numbers, dots, underscores or hyphens. Passwords need 10 characters minimum. After repeated failures wait one minute. Reset an account using `scripts/create_user.py NAME --role operator --reset` from the local machine, then restart the server. No default admin password exists.

## Logs / data

`logs/app.log` and `logs/error.log` rotate automatically. User data is in `data/` by default. A read-only folder, full disk, or unavailable database can stop recording/source processing; use a writable path with free disk space. Back up the data directory while the server is stopped. Do not expose the local console directly to the public internet.
