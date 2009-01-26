import gobject
import threading
import time

class C(gobject.GObject):
    __gsignals__ = { 'my_signal': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                   (str,)) }
    def __init__(self) :
        gobject.GObject.__init__(self)
        a = None
        

class receiver:
    def __init__(self,emiter,lock) :
        self.emiter = emiter
        self.emiter.connect("my_signal",self.do)
        self.lock = threading.Lock()
        self.waiting = []
                
    def do(self,param1,param2) :
        t = threading.Thread(target=self.display,args=[self.dothing,[param2],self.lock,self.waiting])
        t.start()
        
    def display(self,func,param,lock,waiting) :
        if lock.acquire(False) :
            func(*param)
            lock.release()
        else :
            if not waiting :
                print "waiting"
                waiting.append(True)
                lock.acquire()
                func(*param)
                lock.release()
                waiting.remove(True)
            else :
                print "blocked"
            
    def dothing(self,param) :
        print "signal received with %s"%(param)
        time.sleep(4)
        print "end of receiver"
        
class intermediate:
    def __init__(self,emiter) :
        self.emiter = emiter
        
    def connect(self,signal,func) :
        self.emiter.connect(signal,func)

def create(ee) :
    ee.emit("my_signal","1")
    
    
e = C()
inter = intermediate(e)
lock = threading.Lock()
#i = 0
#while i < 5 :
#    r = threading.Thread(target=receiver,args=[e,lock])
#    r2 = threading.Thread(target=receiver,args=[e,lock])
#    r.start()
#    r2.start()
#    i += 1
r = receiver(inter,lock)
#r2 = receiver(inter,lock)

create(e)
create(e)
create(e)
time.sleep(1)
create(e)
create(e)
time.sleep(3)
create(e)
create(e)
#t = threading.Thread(target=create,args=[e])
#t.start()

        
