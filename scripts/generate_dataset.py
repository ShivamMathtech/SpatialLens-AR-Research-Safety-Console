"""Reproducible moving-object synthetic input plus generated reference annotations."""
import json, sys
from pathlib import Path
import cv2
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.cv.synthetic import SyntheticSource,SyntheticDetector
root=Path(__file__).resolve().parents[1]/'datasets';root.mkdir(exist_ok=True)
source=SyntheticSource(640);detector=SyntheticDetector()
writer=cv2.VideoWriter(str(root/'synthetic_walkthrough.avi'),cv2.VideoWriter_fourcc(*'MJPG'),15,(640,360))
if not writer.isOpened(): raise SystemExit('MJPEG writer unavailable.')
labels=[]
for frame in range(120):
    image=source.frame(frame/15);writer.write(image)
    labels.append({'frame':frame,'timestamp':frame/15,'detections':detector.detect(image)})
writer.release()
(root/'synthetic_annotations.json').write_text(json.dumps({'note':'Synthetic color-component annotations, not a natural-image benchmark.','frames':labels},indent=2))
print('Dataset created: 8 seconds, 120 frames, 640x360.')
