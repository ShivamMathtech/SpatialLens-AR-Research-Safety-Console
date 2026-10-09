"""Deterministic offline dataset: actual colored image components, not YOLO claims."""
import cv2, numpy as np, math
PALETTE = {'person': (78, 207, 245), 'car': (228, 151, 60), 'bicycle': (188, 97, 212)}
class SyntheticSource:
    fps = 30
    def __init__(self, width=960):
        self.width = width
        self.height = round(width * 9 / 16)
        self.index = 0
    def frame(self, t):
        w,h = self.width,self.height
        im = np.zeros((h,w,3),np.uint8)
        for y in range(h):
            f = y / h
            im[y,:] = (int(74-38*f),int(55-14*f),int(34-5*f))
        def poly(points,c): cv2.fillPoly(im,[np.array([(int(x*w),int(y*h)) for x,y in points],np.int32)],c)
        poly([(0,.53),(.1,.24),(.19,.42),(.36,.12),(.51,.47),(.65,.22),(.86,.48),(1,.2),(1,1),(0,1)],(74,75,64))
        poly([(0,.66),(.2,.39),(.33,.63),(.53,.36),(.71,.57),(.9,.3),(1,.53),(1,1),(0,1)],(55,65,52))
        poly([(0,.75),(.29,.55),(.48,.65),(.72,.55),(1,.69),(1,1),(0,1)],(36,51,39))
        poly([(.48,.55),(.54,.55),(.75,1),(.30,1)],(81,86,79))
        poly([(.7,.59),(.73,.59),(.98,1),(.87,1)],(126,107,62))
        for bx,by,bw,bh in [(.25,.5,.08,.13),(.61,.47,.11,.16),(.72,.53,.08,.1)]:
            x,y,ww,hh = [int(v*s) for v,s in zip((bx,by,bw,bh),(w,h,w,h))]
            cv2.rectangle(im,(x,y),(x+ww,y+hh),(101,106,95),-1)
            for dx in (.2,.6): cv2.rectangle(im,(x+int(ww*dx),y+int(hh*.2)),(x+int(ww*(dx+.16)),y+int(hh*.45)),(37,43,38),-1)
        objects = [('person',.28+.10*math.sin(t*.18),.71,.026,.14),('person',.58+.07*math.sin(t*.13+2),.61,.018,.09),('car',.47+.11*math.sin(t*.12),.75,.095,.08),('bicycle',.81-.08*math.sin(t*.16),.78,.045,.065)]
        for label,cx,cy,bw,bh in objects:
            x,y,ww,hh = int(cx*w),int(cy*h),int(bw*w),int(bh*h)
            col = PALETTE[label]
            if label=='person':
                cv2.circle(im,(x,y-hh+ww//2),max(2,ww//3),col,-1)
                cv2.rectangle(im,(x-ww//2,y-hh+ww),(x+ww//2,y-hh//3),col,-1)
                cv2.line(im,(x-ww//4,y-hh//3),(x-ww//3,y),col,max(3,ww//4))
                cv2.line(im,(x+ww//4,y-hh//3),(x+ww//3,y),col,max(3,ww//4))
            else:
                cv2.rectangle(im,(x-ww//2,y-hh),(x+ww//2,y-3),col,-1)
                cv2.circle(im,(x-ww//3,y-2),max(3,hh//5),(13,22,20),-1)
                cv2.circle(im,(x+ww//3,y-2),max(3,hh//5),(13,22,20),-1)
        cv2.putText(im,'SYNTHETIC RESEARCH ENVIRONMENT',(18,h-20),cv2.FONT_HERSHEY_SIMPLEX,.43,(162,186,175),1,cv2.LINE_AA)
        return im

class SyntheticDetector:
    name = 'Synthetic color-component detector (not a neural model)'
    def detect(self, image):
        detections=[]
        for name,color in PALETTE.items():
            c = np.array(color, dtype=np.int16)
            mask=cv2.inRange(image,np.maximum(c-8,0).astype('uint8'),np.minimum(c+8,255).astype('uint8'))
            mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
            contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x,y,w,h=cv2.boundingRect(contour)
                if w*h > 50: detections.append({'class':name,'confidence':1.0,'bbox':[x,y,x+w,y+h], 'confidence_kind':'synthetic color match'})
        return detections
