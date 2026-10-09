import os, tempfile, time, json, base64
os.environ['SPATIAL_DATA_DIR']=tempfile.mkdtemp(prefix='spatiallens-test-')
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from backend.app.main import app,pipeline
from backend.app.core.config import Settings
from backend.app.core.db import DB,Frame,Base,User
from backend.app.core.security import password_hash
from backend.app.cv.synthetic import SyntheticSource,SyntheticDetector
from backend.app.cv.tracking import SmoothTracker
from backend.app.cv.spatial import SizePriorDepth,camera_to_world
from backend.app.services.events import EventEngine

@pytest.fixture(scope='module')
def client():
    with TestClient(app) as c:
        assert c.post('/api/auth/setup',json={'username':'testuser','password':'test-only-password-0123'}).status_code==200
        yield c
    pipeline.stop()

def wait_state(client,predicate,timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        state=client.get('/api/state').json()
        if predicate(state): return state
        time.sleep(.08)
    raise AssertionError(f'Timed out: {state}')

def test_synthetic_detection_and_identity():
    source=SyntheticSource(640);detector=SyntheticDetector();tracker=SmoothTracker(Settings())
    first=tracker.update(detector.detect(source.frame(0)),100)
    second=tracker.update(detector.detect(source.frame(.2)),100.2)
    assert len(first)==len(second)==4
    assert {t['track_id'] for t in first}=={t['track_id'] for t in second}
    assert all(len(t['trajectory'])==2 for t in second)
    assert all(0<=t['confidence']<=1 for t in second)

def test_depth_requires_calibration():
    track={'class':'person','bbox':[300,100,340,300]}
    assert SizePriorDepth(Settings()).estimate(track,640) is None
    result=SizePriorDepth(Settings(calibration_enabled=True)).estimate(track,960)
    assert result['z']==pytest.approx(6.8)
    assert result['uncertainty_m']>0
    assert camera_to_world(0,10,90)['x']==pytest.approx(10)

def test_lost_tracking_event_and_prediction():
    s=Settings(max_missed=1);tracker=SmoothTracker(s);events=EventEngine()
    tracks=tracker.update([{'class':'person','bbox':[10,10,40,80],'confidence':.8}],100)
    assert events.update(tracks,100)[0]['type']=='object_detected'
    assert tracker.update([],100.1)[0]['status']=='predicted'
    tracks=tracker.update([],100.2)
    assert not tracks
    assert events.update(tracks,100.2)[0]['type']=='tracking_lost'

def test_auth_and_origin(client):
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/config').status_code==401
        assert anonymous.post('/api/auth/setup',json={'username':'second','password':'a-long-password'}).status_code==409
    assert client.post('/api/control',json={'action':'stop'},headers={'Origin':'https://untrusted.invalid'}).status_code==403
    assert client.put('/api/config',json={'processing_fps':200}).status_code==422
    assert client.post('/api/sessions',json={'kind':'video','value':'../../bad.mp4'}).status_code==400

def test_live_pause_record_replay_export_delete(client):
    assert client.put('/api/config',json=Settings(processing_fps=8,width=640,max_recorded_frames=30).model_dump()).status_code==200
    sid=client.post('/api/sessions',json={'kind':'demo'}).json()['session_id']
    state=wait_state(client,lambda s:s.get('seq',0)>=4)
    assert len(state['tracks'])==4 and state['sensors']['GPS']=='SIMULATED'
    assert state['metrics']['fps']>0 and state['metrics']['latency_ms']>0
    with client.websocket_connect('/ws/live') as ws:
        packet=ws.receive_json();assert packet['image'];assert packet['state']['session_id']==sid
        assert base64.b64decode(packet['image']).startswith(b'\xff\xd8')
    assert client.post('/api/control',json={'action':'pause'}).status_code==200
    time.sleep(.25);paused=client.get('/api/state').json();time.sleep(.25)
    assert client.get('/api/state').json()['seq']==paused['seq']
    assert client.post('/api/control',json={'action':'resume'}).status_code==200
    wait_state(client,lambda s:s.get('seq',0)>paused['seq'])
    assert client.post('/api/waypoints',json={'name':'Test waypoint','x':1,'z':60}).status_code==200
    assert client.get('/api/snapshot').headers['content-type']=='image/jpeg'
    client.post('/api/control',json={'action':'stop'})
    frames=client.get('/api/replay/'+sid).json();assert len(frames)>=5
    replay=client.get(f"/api/replay/{sid}/{frames[2]['seq']}").json()
    with DB() as db:
        row=db.scalar(select(Frame).where(Frame.session_id==sid,Frame.seq==frames[2]['seq']))
        assert replay['state']==row.state
    assert replay['state']['tracks'] and replay['state']['events']
    assert client.get('/api/export/'+sid+'?format=csv').text.startswith('seq,')
    assert client.get('/api/tracks?session_id='+sid).json()
    assert client.get('/api/events?session_id='+sid).json()
    assert client.delete('/api/sessions/'+sid).status_code==200
    assert client.get('/api/replay/'+sid).status_code==404

def test_recording_limit_and_restart(client):
    sid=client.post('/api/sessions',json={'kind':'demo'}).json()['session_id']
    state=wait_state(client,lambda s:s.get('recorded_frames',0)>=30,timeout=8)
    assert state['recording'] is False
    assert any(e['type']=='recording_limit' for e in state['events'])
    client.post('/api/control',json={'action':'stop'})
    assert len(client.get('/api/replay/'+sid).json())==30

def test_viewer_cannot_mutate(client):
    with DB.begin() as db: db.add(User(username='viewer',password_hash=password_hash('viewer-password-123'),role='viewer'))
    with TestClient(app) as viewer:
        assert viewer.post('/api/auth/login',json={'username':'viewer','password':'viewer-password-123'}).status_code==200
        assert viewer.get('/api/config').status_code==200
        assert viewer.post('/api/sessions',json={'kind':'demo'}).status_code==403

def test_invalid_video_and_missing_ai_error(client):
    assert client.post('/api/upload',files={'file':('bad.mp4',b'not a video','video/mp4')}).status_code==400
    assert client.post('/api/upload',files={'file':('bad.exe',b'no','application/octet-stream')}).status_code==400
