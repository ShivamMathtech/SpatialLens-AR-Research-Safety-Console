import asyncio, base64, csv, io, json, logging, os, secrets, time, uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from logging.handlers import RotatingFileHandler
import cv2
from fastapi import FastAPI, HTTPException, Depends, Request, Response, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy import select, func, delete
from .core.config import ROOT, DATA, Settings, load_settings, save_settings
from .core.db import Base, engine, DB, User, Session, Frame, Track, Event, Scene, SystemMetric, TrackPoint, Detection, SensorStatus, Waypoint
from .core import security as auth
from .services.pipeline import Pipeline

log=logging.getLogger('spatiallens'); log.setLevel(logging.INFO)
(ROOT/'logs').mkdir(exist_ok=True)
handler=RotatingFileHandler(ROOT/'logs'/'app.log',maxBytes=2_000_000,backupCount=3)
class JsonFormatter(logging.Formatter):
    def format(self,record):
        return json.dumps({'time':self.formatTime(record),'level':record.levelname,'message':record.getMessage(),'exception':self.formatException(record.exc_info) if record.exc_info else None})
handler.setFormatter(JsonFormatter())
log.addHandler(handler)
errors=RotatingFileHandler(ROOT/'logs'/'error.log',maxBytes=2_000_000,backupCount=2); errors.setLevel(logging.ERROR); errors.setFormatter(JsonFormatter()); log.addHandler(errors)
pipeline=Pipeline()
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    log.info('application_startup')
    yield
    await asyncio.to_thread(pipeline.stop)
app=FastAPI(title='SpatialLens · Research & Safety Console',version='1.0.0',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=os.getenv('ALLOWED_HOSTS','127.0.0.1,localhost,testserver').split(','))

@app.middleware('http')
async def origin_guard(request, call_next):
    # Browser mutations must come from the local console. Nonbrowser clients authenticate normally.
    origin=request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin:
        allowed={str(request.base_url).rstrip('/'),'http://127.0.0.1:5173','http://localhost:5173'}
        if origin not in allowed: return Response('Cross-origin request blocked',status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    return response

class Credentials(BaseModel):
    username: str = Field(min_length=3,max_length=64,pattern=r'^[a-zA-Z0-9_.-]+$')
    password: str = Field(min_length=10,max_length=128)
class Source(BaseModel):
    kind: Literal['demo','video','webcam','rtsp']='demo'
    value: str=''
class Control(BaseModel):
    action: Literal['pause','resume','stop','record_on','record_off']
class WaypointInput(BaseModel):
    name: str = Field(min_length=1,max_length=60)
    x: float = Field(ge=-1000,le=1000)
    z: float = Field(ge=-1000,le=1000)

@app.get('/api/health')
def health(): return {'status':'ok','setup_required':auth.needs_setup(),'version':'1.0.0'}
@app.post('/api/auth/setup')
def setup(body:Credentials,response:Response):
    with auth.LOCK:
        if not auth.needs_setup(): raise HTTPException(409,'Account already configured. Sign in.')
        with DB.begin() as db: db.add(User(username=body.username,password_hash=auth.password_hash(body.password),role='operator'))
    return login(body,response)
@app.post('/api/auth/login')
def login(body:Credentials,response:Response):
    key=body.username; current=time.time()
    with auth.LOCK:
        times=[t for t in auth.ATTEMPTS.get(key,[]) if t>current-60]
        if len(times)>=5: raise HTTPException(429,'Too many attempts. Wait one minute.')
        times.append(current); auth.ATTEMPTS[key]=times
    with DB() as db:
        user=db.get(User,body.username)
        if not user or not auth.verify(body.password,user.password_hash): raise HTTPException(401,'Invalid username or password.')
        token=secrets.token_urlsafe(32)
        with auth.LOCK:
            for old in [k for k,v in auth.TOKENS.items() if v['expires']<current]: auth.TOKENS.pop(old,None)
            auth.TOKENS[token]={'username':user.username,'role':user.role,'expires':current+28800}
        response.set_cookie('spatial_session',token,httponly=True,samesite='strict',max_age=28800,secure=os.getenv('COOKIE_SECURE','false').lower()=='true')
        return {'username':user.username,'role':user.role}
@app.get('/api/auth/me')
def me(user=Depends(auth.current_user)): return user
@app.post('/api/auth/logout')
def logout(request:Request,response:Response):
    with auth.LOCK: auth.TOKENS.pop(request.cookies.get('spatial_session'),None)
    response.delete_cookie('spatial_session'); return {'ok':True}
@app.get('/api/config')
def config(user=Depends(auth.current_user)): return load_settings()
@app.put('/api/config')
def update_config(body:Settings,user=Depends(auth.operator)):
    save_settings(body); return {'settings':body,'applies':'next session'}
@app.get('/api/models')
def models(user=Depends(auth.current_user)):
    import importlib.util
    return {'ultralytics_installed':importlib.util.find_spec('ultralytics') is not None,'models':[{'name':name,'available':(ROOT/'models'/name).is_file()} for name in ('yolov8n.pt','yolo11n.pt')],'demo':'Bundled synthetic color detector','depth':'Optional calibrated size-prior approximation; no learned depth map'}
@app.post('/api/upload')
async def upload(file:UploadFile=File(...),user=Depends(auth.operator)):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in ('.mp4','.avi','.mov','.mkv','.webm'): raise HTTPException(400,'Choose MP4, AVI, MOV, MKV or WebM.')
    name=uuid.uuid4().hex+suffix; path=DATA/'uploads'/name; size=0
    try:
        with path.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>200*1024*1024: raise HTTPException(413,'Video exceeds the 200 MB upload limit.')
                out.write(chunk)
        def check():
            cap=cv2.VideoCapture(str(path)); ok,frame=cap.read(); cap.release(); return ok and frame is not None
        if not await asyncio.to_thread(check): raise HTTPException(400,'This video cannot be decoded. Convert it to an H.264 MP4 or MJPEG AVI.')
    except Exception:
        path.unlink(missing_ok=True); raise
    finally: await file.close()
    return {'file_id':name,'size':size}
@app.post('/api/sessions')
def start_session(body:Source,user=Depends(auth.operator)):
    if body.kind=='video':
        if Path(body.value).name!=body.value or not (DATA/'uploads'/body.value).is_file(): raise HTTPException(400,'Upload a video first.')
    if body.kind=='webcam':
        if not body.value.isdigit() or int(body.value)>9: raise HTTPException(400,'Camera index must be 0–9.')
    if body.kind=='rtsp':
        url=urlparse(body.value)
        if url.scheme not in ('rtsp','rtsps') or not url.hostname: raise HTTPException(400,'Enter a valid rtsp:// or rtsps:// URL.')
    try: sid=pipeline.start(body.model_dump(),load_settings())
    except RuntimeError as exc: raise HTTPException(409,str(exc))
    return {'session_id':sid}
@app.post('/api/control')
def control(body:Control,user=Depends(auth.operator)):
    if body.action=='stop': pipeline.stop()
    elif body.action in ('pause','resume'):
        if pipeline.state.get('status') not in ('running','paused'): raise HTTPException(409,'Start a source first.')
        pipeline.pause(body.action=='pause')
    else:
        if pipeline.state.get('status') not in ('running','paused'): raise HTTPException(409,'Start a source first.')
        pipeline.record=body.action=='record_on'
    return {'ok':True}
@app.get('/api/state')
def state(user=Depends(auth.current_user)): return pipeline.packet()[1]
@app.get('/api/snapshot')
def snapshot(user=Depends(auth.current_user)):
    _,_,jpeg=pipeline.packet()
    if not jpeg: raise HTTPException(404,'No frame available.')
    return Response(jpeg,media_type='image/jpeg',headers={'Content-Disposition':'attachment; filename=spatiallens-snapshot.jpg'})
@app.get('/api/sessions')
def sessions(user=Depends(auth.current_user)):
    with DB() as db:
        rows=db.execute(select(Session,func.count(Frame.id)).outerjoin(Frame,Frame.session_id==Session.id).group_by(Session.id).order_by(Session.started.desc()).limit(100))
        return [{'id':s.id,'source':s.source,'started':s.started,'ended':s.ended,'frames':n} for s,n in rows]
@app.delete('/api/sessions/{sid}')
def delete_session(sid:str,user=Depends(auth.operator)):
    if sid==pipeline.session_id and pipeline.thread and pipeline.thread.is_alive(): raise HTTPException(409,'Stop this session before deleting.')
    with DB.begin() as db:
        if not db.get(Session,sid): raise HTTPException(404,'Session not found.')
        for model in (Frame,Track,Event,TrackPoint,Detection,Scene,SensorStatus,SystemMetric,Waypoint): db.execute(delete(model).where(model.session_id==sid))
        db.execute(delete(Session).where(Session.id==sid))
    import shutil
    directory=DATA/'recordings'/sid
    if directory.parent==DATA/'recordings': shutil.rmtree(directory,ignore_errors=True)
    return {'ok':True}
@app.get('/api/tracks')
def tracks(session_id:str|None=None,user=Depends(auth.current_user)):
    if not session_id: return pipeline.packet()[1].get('tracks',[])
    with DB() as db: return [t.state for t in db.scalars(select(Track).where(Track.session_id==session_id))]
@app.get('/api/events')
def events(session_id:str|None=None,q:str='',severity:str='',track:str='',limit:int=100,user=Depends(auth.current_user)):
    with DB() as db:
        query=select(Event)
        if session_id: query=query.where(Event.session_id==session_id)
        if q: query=query.where(Event.description.contains(q))
        if severity: query=query.where(Event.severity==severity)
        if track: query=query.where(Event.related_track_id==track)
        return [{'event_id':e.id,'timestamp':e.timestamp,'type':e.type,'severity':e.severity,'description':e.description,'related_track_id':e.related_track_id} for e in db.scalars(query.order_by(Event.timestamp.desc()).limit(max(1,min(limit,500))))]
@app.get('/api/scenes')
def scenes(session_id:str|None=None,user=Depends(auth.current_user)):
    if not session_id: return pipeline.packet()[1].get('scene',{})
    with DB() as db: return [s.payload for s in db.scalars(select(Scene).where(Scene.session_id==session_id).order_by(Scene.seq).limit(1000))]
@app.post('/api/waypoints')
def waypoint(body:WaypointInput,user=Depends(auth.operator)):
    if pipeline.state.get('source')!='demo' or pipeline.state.get('status') not in ('running','paused'): raise HTTPException(409,'Waypoints are available in an active simulated session.')
    wp={'id':'CP-'+uuid.uuid4().hex[:6],**body.model_dump()}
    with pipeline.lock:
        if len(pipeline.navigation.waypoints)>=30: raise HTTPException(409,'Limit of 30 waypoints reached.')
        pipeline.navigation.waypoints.append(wp)
    with DB.begin() as db: db.add(Waypoint(session_id=pipeline.session_id,seq=pipeline.state.get('seq',0),payload=wp))
    return wp
@app.get('/api/replay/{sid}')
def replay_index(sid:str,user=Depends(auth.current_user)):
    with DB() as db:
        if not db.get(Session,sid): raise HTTPException(404,'Session not found.')
        return [{'seq':seq,'timestamp':ts} for seq,ts in db.execute(select(Frame.seq,Frame.timestamp).where(Frame.session_id==sid).order_by(Frame.seq))]
@app.get('/api/replay/{sid}/{seq}')
def replay_frame(sid:str,seq:int,user=Depends(auth.current_user)):
    with DB() as db:
        frame=db.scalar(select(Frame).where(Frame.session_id==sid,Frame.seq==seq))
        if not frame: raise HTTPException(404,'Recorded frame not found.')
        path=DATA/'recordings'/frame.image
        if not path.is_file(): raise HTTPException(410,'Recording image is missing from disk.')
        return {'state':frame.state,'image':base64.b64encode(path.read_bytes()).decode()}
@app.get('/api/export/{sid}')
def export(sid:str,format:Literal['json','csv']='json',user=Depends(auth.current_user)):
    with DB() as db:
        if not db.get(Session,sid): raise HTTPException(404,'Session not found.')
        rows=[{'seq':r.seq,**r.payload} for r in db.scalars(select(SystemMetric).where(SystemMetric.session_id==sid).order_by(SystemMetric.seq))]
    if format=='json': content=json.dumps({'session_id':sid,'metrics':rows,'note':'ID switches require ground truth and are not measured.'},indent=2); mime='application/json'
    else:
        stream=io.StringIO(); writer=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else ['seq']); writer.writeheader(); writer.writerows(rows); content=stream.getvalue(); mime='text/csv'
    return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename=spatiallens-metrics.{format}'})

@app.websocket('/ws/{channel}')
async def websocket(ws:WebSocket,channel:str):
    if channel not in ('live','tracks','events','system'): await ws.close(code=1008); return
    origin=ws.headers.get('origin','')
    expected=('https://' if ws.url.scheme=='wss' else 'http://')+ws.headers.get('host','')
    if origin and origin not in (expected,'http://localhost:5173','http://127.0.0.1:5173'): await ws.close(code=1008); return
    if not auth.authenticate_token(ws.cookies.get('spatial_session')): await ws.close(code=1008); return
    await ws.accept(); log.info('websocket_connected'); version=-1
    try:
        while True:
            if not auth.authenticate_token(ws.cookies.get('spatial_session')): await ws.close(code=1008); break
            new,state,jpeg=pipeline.packet()
            if new!=version:
                packet={'state':state,'image':base64.b64encode(jpeg).decode() if jpeg else None} if channel=='live' else {'tracks':state.get('tracks',[])} if channel=='tracks' else {'events':state.get('events',[])} if channel=='events' else {'metrics':state.get('metrics',{}),'status':state['status']}
                await asyncio.wait_for(ws.send_json(packet),timeout=5)
                version=new
            await asyncio.sleep(.033)
    except (WebSocketDisconnect,RuntimeError,asyncio.TimeoutError): pass

# Serve the prebuilt client so everyday users need Python only after setup.
dist=ROOT/'frontend'/'dist'
if dist.is_dir(): app.mount('/',StaticFiles(directory=str(dist),html=True),name='frontend')
