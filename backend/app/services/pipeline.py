"""Bounded latest-frame capture + inference worker; HTTP/WS never run inference."""
import base64, copy, logging, queue, threading, time, uuid
from collections import deque
import cv2, numpy as np, psutil
from sqlalchemy import select
from ..core.config import DATA
from ..core.db import DB, Session, Frame, Track, Event, TrackPoint, Detection, Scene, SensorStatus, SystemMetric, Waypoint, now
from ..cv.synthetic import SyntheticSource, SyntheticDetector
from ..cv.yolo import YoloDetector
from ..cv.tracking import SmoothTracker
from ..cv.spatial import SizePriorDepth, SceneAnalyzer, alternate_view
from .events import EventEngine
from .navigation import Navigation
from .telemetry import Telemetry
log=logging.getLogger('spatiallens')

class Capture:
    def __init__(self,source,settings,stop,pause):
        self.source=source; self.settings=settings; self.stop=stop; self.pause=pause
        self.queue=queue.Queue(maxsize=1); self.drops=0; self.error=None; self.done=False
        self.cap=None; self.thread=None
    def start(self):
        self.thread=threading.Thread(target=self.run,daemon=True,name='capture'); self.thread.start()
    def run(self):
        try:
            demo=self.source['kind']=='demo'; s=self.settings
            synthetic=SyntheticSource(s.width) if demo else None
            if not demo:
                kind=self.source['kind']; value=self.source.get('value',0)
                if kind=='video': value=str(DATA/'uploads'/value)
                if kind=='webcam': value=int(value)
                if kind=='rtsp':
                    self.cap=cv2.VideoCapture(value,cv2.CAP_FFMPEG,[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,5000,cv2.CAP_PROP_READ_TIMEOUT_MSEC,3000])
                else: self.cap=cv2.VideoCapture(value)
                if not self.cap.isOpened(): raise RuntimeError('Camera or video could not be opened. Check the source and camera permissions.')
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
                if kind=='webcam': self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,s.width)
            fps=30 if demo else self.cap.get(cv2.CAP_PROP_FPS)
            fps=fps if 1<=fps<=120 else 30
            idx=0; started=time.perf_counter()
            while not self.stop.is_set():
                if self.pause.is_set():
                    self.stop.wait(.03); started=time.perf_counter()-idx/fps; continue
                if demo: im=synthetic.frame(idx/fps)
                else:
                    ok,im=self.cap.read()
                    if not ok:
                        if self.source['kind']=='video': self.done=True; break
                        raise RuntimeError('Camera disconnected or stream ended. Stop and reconnect the source.')
                h,w=im.shape[:2]
                if w!=s.width: im=cv2.resize(im,(s.width,round(h*s.width/w)))
                item=(idx,idx/fps,time.time(),im)
                try: self.queue.put_nowait(item)
                except queue.Full:
                    try: self.queue.get_nowait(); self.drops+=1
                    except queue.Empty: pass
                    self.queue.put_nowait(item)
                idx+=1
                if demo or self.source['kind']=='video': self.stop.wait(max(0,started+idx/fps-time.perf_counter()))
        except Exception as exc:
            log.exception('capture_error'); self.error=str(exc)
        finally:
            self.done=True
            if self.cap is not None: self.cap.release()

class Pipeline:
    def __init__(self):
        self.lock=threading.RLock(); self.control=threading.RLock(); self.stop_event=threading.Event(); self.pause_event=threading.Event()
        self.thread=None; self.capture=None; self.state={'status':'idle','tracks':[],'events':[]}; self.jpeg=None; self.version=0
        self.session_id=None; self.record=False; self.navigation=Navigation(); self.error=None
        self.events=EventEngine()
    def start(self,source,settings):
        with self.control:
            self.stop()
            if self.thread and self.thread.is_alive(): raise RuntimeError('Previous source is still closing. Retry in a few seconds.')
            self.stop_event=threading.Event(); self.pause_event=threading.Event(); self.record=settings.record
            self.events=EventEngine(); self.navigation=Navigation(); self.error=None
            self.session_id=uuid.uuid4().hex
            with DB.begin() as db:
                db.add(Session(id=self.session_id,source=source['kind'],settings=settings.model_dump()))
                for wp in self.navigation.waypoints: db.add(Waypoint(session_id=self.session_id,seq=0,payload=wp))
            with self.lock:
                self.state={'status':'loading','session_id':self.session_id,'source':source['kind'],'tracks':[],'events':[]}; self.jpeg=None; self.version+=1
            self.thread=threading.Thread(target=self.run,args=(source,settings,self.session_id),daemon=True,name='inference')
            self.thread.start()
            return self.session_id
    def stop(self):
        self.stop_event.set(); self.pause_event.clear()
        if self.thread and self.thread.is_alive(): self.thread.join(timeout=7)
        with self.lock:
            if self.state.get('status') not in ('error','idle'): self.state={**self.state,'status':'stopped'}; self.version+=1
    def pause(self,paused):
        if paused: self.pause_event.set()
        else: self.pause_event.clear()
        with self.lock: self.state={**self.state,'status':'paused' if paused else 'running'}; self.version+=1
    def packet(self):
        with self.lock: return self.version,copy.deepcopy(self.state),self.jpeg
    def emit(self,*args,**kwargs):
        with self.lock:
            e=self.events.emit(*args,**kwargs)
        with DB.begin() as db:
            db.add(Event(id=e['event_id'],session_id=self.session_id,**{k:v for k,v in e.items() if k!='event_id'}))
        return e
    def run(self,source,s,session_id):
        capture=None
        try:
            cv2.setNumThreads(2)
            demo=source['kind']=='demo'; detector=SyntheticDetector() if demo else YoloDetector(s)
            tracker=SmoothTracker(s); depth=SizePriorDepth(s,demo); analyzer=SceneAnalyzer()
            capture=Capture(source,s,self.stop_event,self.pause_event); self.capture=capture; capture.start()
            self.emit('session_started',f"{source['kind'].title()} session started")
            samples=deque(maxlen=300); detection_samples=deque(maxlen=300); times=deque(maxlen=60); telemetry=Telemetry()
            processed=0; stored=0; seen=set(); recording_dir=DATA/'recordings'/session_id; recording_dir.mkdir()
            previous_counter=0; perf_warn=False
            while not self.stop_event.is_set():
                if self.pause_event.is_set(): self.stop_event.wait(.03); continue
                tick=time.perf_counter()
                try: idx,video_time,captured,frame=capture.queue.get(timeout=.2)
                except queue.Empty:
                    if capture.error: raise RuntimeError(capture.error)
                    if capture.done: break
                    continue
                detect_now=processed%s.detection_interval==0
                d0=time.perf_counter(); detections=detector.detect(frame) if detect_now else []; det_ms=(time.perf_counter()-d0)*1000
                t0=time.perf_counter(); tracks=tracker.update(detections,captured,detect_now); track_ms=(time.perf_counter()-t0)*1000
                z0=time.perf_counter()
                for tr in tracks:
                    tr['position']=depth.estimate(tr,frame.shape[1]); tr['speed_unit']='pixels/s'; tr['speed_px_s']=round(float(np.linalg.norm(tr['velocity_px_s'])),2)
                    tr['direction_deg']=round(float(np.degrees(np.arctan2(tr['velocity_px_s'][0],-tr['velocity_px_s'][1])))%360,1)
                depth_ms=(time.perf_counter()-z0)*1000
                scene=analyzer.analyze(frame,len(tracks))
                if demo: scene.update(terrain='Generated mountain scene',analysis='Synthetic scene; brightness measured from generated frames')
                with self.lock:
                    new_events=self.events.update(tracks,captured)
                    nav=self.navigation.update(video_time,demo)
                if scene['scene_changed']: new_events.append(self.events.emit('scene_changed','Large brightness change detected',timestamp=captured))
                if nav.get('checkpoint_reached'): new_events.append(self.events.emit('checkpoint_reached',nav['checkpoint_reached'],timestamp=captured))
                if detect_now and any(d['confidence']<.5 for d in detections) and processed%60==0: new_events.append(self.events.emit('low_confidence','Some detections have confidence below 50%','warning',timestamp=captured))
                sensors={'RGB Camera':'SIMULATED' if demo else 'ONLINE','Thermal Camera':'OFFLINE','IMU':'SIMULATED' if demo else 'OFFLINE','GPS':'SIMULATED' if demo else 'OFFLINE','Depth Sensor':'OFFLINE'}
                display=alternate_view(frame,s.view_mode)
                ok,jpg=cv2.imencode('.jpg',display,[cv2.IMWRITE_JPEG_QUALITY,s.jpeg_quality])
                if not ok: raise RuntimeError('Preview encoding failed')
                jpeg=jpg.tobytes(); latency=(time.perf_counter()-tick)*1000; samples.append(latency); times.append(time.perf_counter())
                if detect_now: detection_samples.append(det_ms)
                fps=(len(times)-1)/max(.001,times[-1]-times[0]) if len(times)>1 else 0.
                if processed>30 and fps<s.processing_fps*.5 and not perf_warn:
                    new_events.append(self.events.emit('performance_degradation','Processing is below half the configured FPS; reduce resolution or detection frequency.','warning',timestamp=captured)); perf_warn=True
                seen.update(t['track_id'] for t in tracks)
                metrics={'detection_ms':round(det_ms,2),'tracking_ms':round(track_ms,2),'depth_ms':round(depth_ms,2),'latency_ms':round(latency,2),'average_ms':round(float(np.mean(samples)),2),'p95_ms':round(float(np.percentile(samples,95)),2),'fps':round(fps,1),'detection_fps':round(fps/s.detection_interval,1),**telemetry.sample(),'frame_drops':capture.drops,'unique_tracks':len(seen),'processed_frames':processed+1,'mean_confidence':round(float(np.mean([x['confidence'] for x in tracks])),3) if tracks else None,'id_switches':None,'gpu_percent':None,'frame_age_ms':round((time.time()-captured)*1000,1)}
                if stored>=s.max_recorded_frames and self.record:
                    self.record=False; new_events.append(self.events.emit('recording_limit','Recording frame limit reached; live view continues.','warning',timestamp=captured))
                state={'status':'paused' if self.pause_event.is_set() else 'running','session_id':session_id,'source':source['kind'],'demo':demo,'detector':detector.name,'seq':processed,'source_frame':idx,'video_time':round(video_time,3),'timestamp':captured,'width':frame.shape[1],'height':frame.shape[0],'tracks':tracks,'scene':scene,'sensors':sensors,'navigation':nav,'environment':{'status':'SIMULATED','temperature_c':18.,'humidity_pct':46.,'wind_kmh':12.,'air_quality':'Demo value'} if demo else {'status':'UNAVAILABLE'},'metrics':metrics,'events':list(self.events.recent),'recording':self.record,'recorded_frames':stored,'view_mode':s.view_mode,'frame_note':'RGB pseudocolor simulation — not thermal sensing' if s.view_mode=='thermal' else 'RGB contrast filter — not infrared sensing' if s.view_mode=='night' else 'Synthetic input' if demo else 'RGB input'}
                # Snapshot state and displayed pixels are persisted together; replay never reruns AI.
                with DB.begin() as db:
                    for e in new_events: db.add(Event(id=e['event_id'],session_id=session_id,**{k:v for k,v in e.items() if k!='event_id'}))
                    if self.record:
                        filename=f'{processed:08}.jpg'; (recording_dir/filename).write_bytes(jpeg)
                        db.add(Frame(session_id=session_id,seq=processed,timestamp=captured,image=f'{session_id}/{filename}',state=state))
                        stored+=1
                        for tr in tracks:
                            key=f"{session_id}:{tr['track_id']}"; item=db.get(Track,key)
                            if item: item.state=tr
                            else: db.add(Track(key=key,session_id=session_id,track_id=tr['track_id'],state=tr))
                            db.add(TrackPoint(session_id=session_id,seq=processed,payload={'track_id':tr['track_id'],'bbox':tr['bbox'],'position':tr['position'],'timestamp':captured}))
                        for det in detections: db.add(Detection(session_id=session_id,seq=processed,payload=det))
                        if processed%max(1,s.processing_fps)==0:
                            db.add(Scene(session_id=session_id,seq=processed,payload=scene)); db.add(SensorStatus(session_id=session_id,seq=processed,payload=sensors)); db.add(SystemMetric(session_id=session_id,seq=processed,payload=metrics))
                with self.lock: self.state=state; self.jpeg=jpeg; self.version+=1
                processed+=1
                self.stop_event.wait(max(0,1/s.processing_fps-(time.perf_counter()-tick)))
            self.emit('session_ended','Input session ended')
            with self.lock: self.state={**self.state,'status':'stopped','recording':False,'events':list(self.events.recent)}; self.version+=1
        except Exception as exc:
            log.exception('pipeline_error'); self.error=str(exc)
            try: self.emit('source_error',str(exc),'error')
            except Exception: log.exception('event_persistence_error')
            with self.lock: self.state={**self.state,'status':'error','error':str(exc),'recording':False,'events':list(self.events.recent)}; self.version+=1
        finally:
            self.stop_event.set()
            if capture and capture.thread: capture.thread.join(timeout=4)
            with DB.begin() as db:
                session=db.get(Session,session_id)
                if session: session.ended=now()
