"""Opt-in actual model smoke test; does not claim detector accuracy."""
import os
from pathlib import Path
import pytest
pytestmark=pytest.mark.skipif(os.getenv('SPATIALLENS_TEST_AI')!='1',reason='Set SPATIALLENS_TEST_AI=1 after installing AI dependencies and weights.')

def test_official_model_cpu_detection_and_tracker():
    cv2=pytest.importorskip('cv2')
    pytest.importorskip('ultralytics')
    from ultralytics.utils import ASSETS
    from backend.app.core.config import Settings,ROOT
    from backend.app.cv.yolo import YoloDetector
    assert (ROOT/'models'/'yolov8n.pt').exists(), 'Download the model first.'
    source=cv2.imread(str(ASSETS/'bus.jpg'))
    assert source is not None
    detector=YoloDetector(Settings(device='cpu',width=640))
    first=detector.detect(source); second=detector.detect(source)
    assert any(d['class']=='bus' for d in first)
    assert any(d['class']=='person' for d in first)
    assert {d.get('external_id') for d in first}=={d.get('external_id') for d in second}
    assert all(0<=d['confidence']<=1 for d in second)
