import math
class Navigation:
    """Explicitly simulated local navigation, in metres; never inferred GPS."""
    def __init__(self):
        self.waypoints=[{'id':'CP-A','name':'Checkpoint Alpha','x':4.,'z':80.},{'id':'CP-B','name':'Observation deck','x':-35.,'z':150.}]
        self.reached=set(); self.breadcrumbs=[]
    def update(self,t,demo):
        if not demo: return {'status':'UNAVAILABLE','reason':'GPS/IMU adapter not connected','waypoints':self.waypoints,'position':None,'breadcrumbs':[]}
        x=5*math.sin(t*.02); z=min(t*.8,160)
        self.breadcrumbs.append({'x':x,'z':z})
        self.breadcrumbs=self.breadcrumbs[-120:]
        target=next((p for p in self.waypoints if p['id'] not in self.reached),None)
        distance=math.hypot(target['x']-x,target['z']-z) if target else None
        bearing=math.degrees(math.atan2(target['x']-x,target['z']-z))%360 if target else 0
        reached=None
        if target and distance<10: self.reached.add(target['id']); reached=target['name']
        return {'status':'SIMULATED','position':{'x':x,'z':z},'heading':bearing,'speed_kmh':2.88,'altitude_m':612,'target':target,'distance_m':distance,'waypoints':self.waypoints,'breadcrumbs':self.breadcrumbs[:],'checkpoint_reached':reached}
