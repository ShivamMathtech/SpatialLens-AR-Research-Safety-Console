"""Approximate size-prior ranging. No metric output without explicit calibration."""
import math, cv2
HEIGHTS={'person':1.7,'car':1.5,'bicycle':1.1,'truck':3.,'bus':3.2,'motorcycle':1.2}
class SizePriorDepth:
    def __init__(self,settings,demo=False): self.s=settings; self.demo=demo
    def estimate(self,track,width):
        if not (self.s.calibration_enabled or self.demo): return None
        height=HEIGHTS.get(track['class'])
        if height is None: return None
        box=track['bbox']; f=self.s.focal_px*width/self.s.reference_width
        z=f*height/max(1,box[3]-box[1]); x=((box[0]+box[2])/2-width/2)*z/f
        return {'x':round(x,2),'y':0.,'z':round(z,2),'distance_m':round(math.hypot(x,z),1),'uncertainty_m':round(math.hypot(x,z)*.4,1),'method':'size prior; assumed upright object; ±40% heuristic, not a calibrated interval','frame':'simulated local' if self.demo else 'camera relative'}

def camera_to_world(x,z,heading_deg,origin=(0,0)):
    a=math.radians(heading_deg)
    return {'x':origin[0]+x*math.cos(a)+z*math.sin(a),'z':origin[1]-x*math.sin(a)+z*math.cos(a)}

class SceneAnalyzer:
    def __init__(self): self.last=None
    def analyze(self,image,count):
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY); value=float(gray.mean())
        changed=self.last is not None and abs(value-self.last)>28
        self.last=value
        return {'lighting':'Low light' if value<65 else 'Bright' if value>180 else 'Moderate','brightness':round(value,1),'object_count':count,'density':'High' if count>15 else 'Low','scene_changed':changed,'terrain':'Unclassified','weather':'Unavailable','visibility':'Not inferred from RGB','analysis':'Brightness heuristic; no semantic terrain model loaded'}

def alternate_view(image,mode):
    if mode=='normal': return image
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    if mode=='thermal': return cv2.applyColorMap(gray,cv2.COLORMAP_INFERNO)
    image=image.copy(); image[:]=0
    image[:,:,1]=cv2.equalizeHist(gray)
    return image
