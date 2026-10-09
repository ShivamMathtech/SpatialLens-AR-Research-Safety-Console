"""ID-preserving smoothing and bounded pixel-space trajectory history."""
import math
from collections import deque

def iou(a,b):
    area=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return area/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-area)
class SmoothTracker:
    def __init__(self, settings):
        self.s=settings; self.tracks={}; self.next_id=1
    def update(self,detections,timestamp,detected=True):
        assigned=set()
        for d in detections:
            external=d.get('external_id')
            tid=f'T-{external:03}' if external is not None else None
            if tid is None:
                candidates=[(iou(d['bbox'],v['bbox']),k) for k,v in self.tracks.items() if k not in assigned and v['class']==d['class']]
                score, candidate=max(candidates,default=(0,None))
                tid=candidate if score>.1 else f'T-{self.next_id:03}'
                if tid==f'T-{self.next_id:03}': self.next_id+=1
            old=self.tracks.get(tid)
            if old:
                dt=max(.001,timestamp-old['last_seen'])
                bbox=[self.s.smoothing*n+(1-self.s.smoothing)*o for n,o in zip(d['bbox'],old['bbox'])]
                center=[(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2]
                oldcenter=[(old['bbox'][0]+old['bbox'][2])/2,(old['bbox'][1]+old['bbox'][3])/2]
                velocity=[(center[i]-oldcenter[i])/dt for i in (0,1)]
                trail=old['trajectory']; trail.append({'x':center[0],'y':center[1],'timestamp':timestamp})
            else:
                bbox=d['bbox'][:]; velocity=[0.,0.]; trail=deque(maxlen=self.s.history)
                trail.append({'x':(bbox[0]+bbox[2])/2,'y':(bbox[1]+bbox[3])/2,'timestamp':timestamp})
            self.tracks[tid]={**d,'track_id':tid,'bbox':bbox,'velocity_px_s':velocity,'first_seen':old['first_seen'] if old else timestamp,'last_seen':timestamp,'age_s':timestamp-(old['first_seen'] if old else timestamp),'trajectory':trail,'missed':0,'status':'active'}
            assigned.add(tid)
        for tid in list(self.tracks):
            v=self.tracks[tid]
            if tid not in assigned:
                if detected: v['missed']+=1
                v['status']='predicted'
                if v['missed']>self.s.max_missed or timestamp-v['last_seen']>3: del self.tracks[tid]
        result=[]
        for v in self.tracks.values():
            item={**v,'trajectory':list(v['trajectory'])}
            if v['status']=='predicted':
                dt=min(.25,max(0,timestamp-v['last_seen']))
                vx,vy=v['velocity_px_s']
                item['bbox']=[v['bbox'][i]+(vx if i%2==0 else vy)*dt for i in range(4)]
            result.append(item)
        return result
