"""Single-command local launcher; the ZIP includes a prebuilt frontend."""
import argparse, os, sys, threading, webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
parser=argparse.ArgumentParser(description='Launch SpatialLens on this computer.')
parser.add_argument('--port',type=int,default=8000)
parser.add_argument('--no-browser',action='store_true')
args=parser.parse_args()
if not (ROOT/'frontend'/'dist'/'index.html').exists():
    raise SystemExit('Frontend build missing. Run: npm --prefix frontend install && npm --prefix frontend run build')
try: import uvicorn
except ImportError: raise SystemExit('Dependencies missing. Run setup_windows.bat, or pip install -r requirements.txt')
if not args.no_browser:
    timer=threading.Timer(1.5,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}'));timer.daemon=True;timer.start()
uvicorn.run('backend.app.main:app',host='127.0.0.1',port=args.port,log_level='info')
