from pathlib import Path
import zipfile
from ..core.config import ROOT
class YoloDetector:
    """Ultralytics detector + ByteTrack/BoT-SORT IDs, loaded only for real inputs."""
    def __init__(self, settings):
        try:
            from ultralytics import YOLO
            import torch
        except ImportError as exc:
            raise RuntimeError('YOLO is not installed. Run install_ai.bat, then download the model.') from exc
        path=ROOT/'models'/settings.model
        if not path.is_file(): raise RuntimeError(f'Model missing: models/{settings.model}. Run python scripts/download_models.py.')
        if not zipfile.is_zipfile(path): raise RuntimeError('The model file is incomplete or invalid. Delete it and rerun scripts/download_models.py.')
        self.model=YOLO(str(path))
        self.device='0' if settings.device in ('auto','cuda') and torch.cuda.is_available() else 'cpu'
        if settings.device=='cuda' and self.device=='cpu': raise RuntimeError('CUDA selected, but CUDA is unavailable. Select CPU or Auto.')
        self.settings=settings
        self.name=f'{settings.model} + {settings.tracker} / {self.device}'
        # Warm up on a blank frame before opening the source.
        import numpy as np
        self.model.predict(np.zeros((320,320,3),dtype=np.uint8),imgsz=320,device=self.device,verbose=False)
    def detect(self,image):
        s=self.settings
        results=self.model.track(image,persist=True,tracker=s.tracker,conf=s.confidence,iou=s.iou,device=self.device,imgsz=min(s.width,640),verbose=False)
        out=[]
        for result in results:
            for box in result.boxes:
                item={'class':result.names[int(box.cls.item())], 'confidence':float(box.conf.item()),'bbox':box.xyxy[0].tolist(),'confidence_kind':'model confidence'}
                if box.id is not None: item['external_id']=int(box.id.item())
                out.append(item)
        return out
