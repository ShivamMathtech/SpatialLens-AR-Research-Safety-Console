import time, uuid
from collections import deque
class EventEngine:
    def __init__(self): self.recent=deque(maxlen=100); self.ids=set(); self.counter=0
    def emit(self,kind,description,severity='info',track=None,timestamp=None):
        e={'event_id':uuid.uuid4().hex,'timestamp':timestamp if timestamp is not None else time.time(),'type':kind,'severity':severity,'description':description,'related_track_id':track}
        self.recent.appendleft(e); self.counter+=1
        return e
    def update(self,tracks,timestamp):
        ids={t['track_id'] for t in tracks}; emitted=[]
        for t in tracks:
            if t['track_id'] not in self.ids: emitted.append(self.emit('object_detected',f"{t['class'].title()} detected · {t['track_id']}",track=t['track_id'],timestamp=timestamp))
        for tid in self.ids-ids: emitted.append(self.emit('tracking_lost',f'Track {tid} disappeared','warning',tid,timestamp))
        self.ids=ids
        return emitted
