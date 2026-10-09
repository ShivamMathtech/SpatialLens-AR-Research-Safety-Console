"""Validated local configuration. Runtime changes apply to the next session."""
import os
from pathlib import Path
from typing import Literal
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / '.env')
DATA = Path(os.getenv('SPATIAL_DATA_DIR', str(ROOT / 'data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
for name in ('uploads', 'recordings', 'snapshots'):
    (DATA / name).mkdir(exist_ok=True)

class Settings(BaseModel):
    confidence: float = Field(.4, ge=.1, le=.95)
    iou: float = Field(.5, ge=.1, le=.9)
    width: int = Field(960, ge=320, le=1280)
    processing_fps: int = Field(12, ge=1, le=30)
    detection_interval: int = Field(1, ge=1, le=10)
    device: Literal['cpu', 'auto', 'cuda'] = 'cpu'
    model: Literal['yolov8n.pt', 'yolo11n.pt'] = 'yolov8n.pt'
    tracker: Literal['bytetrack.yaml', 'botsort.yaml'] = 'bytetrack.yaml'
    history: int = Field(45, ge=5, le=120)
    max_missed: int = Field(15, ge=1, le=90)
    smoothing: float = Field(.55, ge=.1, le=1)
    jpeg_quality: int = Field(75, ge=40, le=90)
    calibration_enabled: bool = False
    focal_px: float = Field(800, ge=50, le=5000)
    reference_width: int = Field(960, ge=320, le=4096)
    max_recorded_frames: int = Field(1800, ge=30, le=7200)
    record: bool = True
    view_mode: Literal['normal', 'thermal', 'night'] = 'normal'


def load_settings():
    merged = {}
    for filename in ('app', 'models', 'camera', 'tracking', 'performance'):
        path = ROOT / 'config' / f'{filename}.yaml'
        if path.exists():
            merged.update(yaml.safe_load(path.read_text()) or {})
    path = DATA / 'settings.yaml'
    if path.exists():
        merged.update(yaml.safe_load(path.read_text()) or {})
    return Settings(**merged)

def save_settings(settings):
    path = DATA / 'settings.yaml'
    temp = path.with_suffix('.tmp')
    temp.write_text(yaml.safe_dump(settings.model_dump()), encoding='utf-8')
    temp.replace(path)
