# Synthetic input

`synthetic_walkthrough.avi` contains 120 generated frames (8 seconds, 15 FPS, 640×360). `synthetic_annotations.json` contains color-component observations. Reproduce them using `python scripts/generate_dataset.py`.

The live Synthetic demo uses lossless generated frames and does not read this AVI. The sample video can exercise upload/decoding; YOLO need not recognize stylized synthetic shapes. It is not an accuracy benchmark or evidence of real-world model quality.
