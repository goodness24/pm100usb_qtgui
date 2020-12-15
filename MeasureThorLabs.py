#  ThorLabs PM100USB Measurement Module
#
#  2020.11.27 v1.0 Goro Nishimura
#       12.15 v1.01 add recording flag
import time
import threading
import ThorlabUSBTMC as thorlabs

class PM100USB(thorlabs.pm100usb):
    def __init__(self):
        super().__init__()
        self.time = []
        self.power = []
        self.temp = []
        self.maxmin_power = []
        self.period = 1.0     # seconds
        self.measurement = False
        self.recording = False
        self.lock = threading.Lock()
        self.init_data()

    def open(self, dev_name=None):
        if not self.active:
            self.measurement = False
            if super().open(dev_name):
                self.active = True

    def close(self):
        if self.active:
            if self.measurement:
                self.stopMeasurement()
            super().close()
            self.recording = False
            self.measurement = False

    def measure(self):
        if self.active:
            tim,p,tmp = super().get_data()
            p *= 1000.0
            self.current_power = p
            self.current_temp = tmp
            if self.recording:
                self.lock.acquire()
                self.time.append(tim)
                self.power.append(p)
                self.temp.append(tmp)
                self.lock.release()
                
            if p<self.maxmin_power[0]: # check minimum
                self.maxmin_power[0] = p
            if p>self.maxmin_power[1]: # check maximum
                self.maxmin_power[1] = p

    def init_data(self):
        self.current_power = 0.0
        self.current_temp = 25.0
        self.lock.acquire()
        self.time.clear()
        self.power.clear()
        self.temp.clear()
        self.maxmin_power = [1e9,-1e9]
        self.lock.release()

    def isActive(self):
        return self.active

    def timerMeasurement(self, num):
        next_call = time.time()
        while self.measurement and num!=0:
            self.measure()
            if num>0:
                num -=1
            next_call = next_call + self.period
            time.sleep(next_call - time.time())
        self.measurement = False

    def startMeasurement(self, num=1):
        if self.active:
            if not self.measurement:
                self.measurement = True
                self.measure()  # the first data
                num -= 1
                if num!=0: # continue measurement in different thread
                    self.measurement_id=threading.Thread(
                        target=self.timerMeasurement,
                        args=([num])
                    )
                    self.measurement_id.daemon = True
                    self.measurement_id.start()
                else:
                    self.measurement = False

    def stopMeasurement(self):
        if self.measurement:
            self.measurement = False
            try:
                self.measurement_id
                self.measurement_id.join()
            except NameError:
                pass

