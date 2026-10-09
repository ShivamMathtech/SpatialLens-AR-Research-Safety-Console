"""Opt-in official model download, atomically published after archive validation."""
from pathlib import Path
import argparse, urllib.request, zipfile, shutil
parser=argparse.ArgumentParser()
parser.add_argument('--model',choices=['yolov8n.pt','yolo11n.pt'],default='yolov8n.pt')
args=parser.parse_args()
try: from ultralytics import YOLO
except ImportError: raise SystemExit('Install optional AI packages first: pip install -r requirements-ai.txt')
folder=Path(__file__).resolve().parents[1]/'models';folder.mkdir(exist_ok=True)
path=folder/args.model
if not path.exists() or not zipfile.is_zipfile(path):
    temp=folder/(args.model+'.download')
    url='https://github.com/ultralytics/assets/releases/download/v8.3.0/'+args.model
    try:
        print('Downloading official model:',args.model)
        with urllib.request.urlopen(url,timeout=60) as response, temp.open('wb') as output:
            length=response.headers.get('Content-Length')
            shutil.copyfileobj(response,output)
        if length and temp.stat().st_size!=int(length): raise RuntimeError('Incomplete download; please retry.')
        if not zipfile.is_zipfile(temp): raise RuntimeError('Invalid model archive; download was blocked or truncated.')
        with zipfile.ZipFile(temp) as archive:
            if archive.testzip() is not None: raise RuntimeError('Model archive checksum failed.')
        temp.replace(path)
    except Exception as exc:
        temp.unlink(missing_ok=True)
        raise SystemExit(f'Model download failed: {exc}')
try: YOLO(str(path))
except Exception as exc: raise SystemExit(f'Model validation failed. Remove {path.name} and retry. Details: {exc}')
print('Validated model ready:',path)
