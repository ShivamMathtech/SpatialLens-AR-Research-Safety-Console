"""Optional system measurements must never take down the perception pipeline."""
import psutil
class Telemetry:
    def __init__(self):
        try:
            self.process=psutil.Process();self.process.cpu_percent()
        except (psutil.Error,OSError,NotImplementedError): self.process=None
    def sample(self):
        result={'cpu_percent':None,'process_cpu_percent':None,'ram_mb':None}
        try: result['cpu_percent']=round(psutil.cpu_percent(),1)
        except (psutil.Error,OSError,NotImplementedError): pass
        if self.process:
            try:
                result['process_cpu_percent']=round(self.process.cpu_percent(),1)
                result['ram_mb']=round(self.process.memory_info().rss/1048576,1)
            except (psutil.Error,OSError,NotImplementedError): pass
        return result
