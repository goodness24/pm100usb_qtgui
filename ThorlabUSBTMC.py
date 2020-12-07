# ThorLabs USBTMC devices interface
#  depending on usbtmc using Linux kernel usbtmc device
#
#  2020.11.25 v1.0 Goro Nishimura
#       12.6  v1.1 current time is using time.time() instead of datetime.now()
#
#  PM100USB with Si detector
#  TSP01 temperature/humidity sensor
# 
from usbtmc import USBTMC as usbtmc_dev
from usbtmc import find_device, list_devinfo
from enum import IntEnum
import time

def list_thorlabs_devinfo( name=''):
    res = []
    for dev in list_devinfo(): # get info of usbtmc devices
        if dev[1]=='Thorlabs': # check manufacture name
            if name=='' or name==dev[2]:           
                res.append(dev[0]+':('+','.join(dev[1:])+')')
    return res

class pm100usb_bw(IntEnum):
    low = 1
    high = 0


class pm100usb:
    def __init__(self):
        self.dev_name = '/dev/usbtmc0'
        self.device_info = []
        self.sensor_info = []
        self.wavelength = 785
        self.average = 100
        self.bw = 1
        self.active = False
        self.during_meas = False
        
    def open(self, dev_name=None, dev_sn=None):
        if self.active:
            return True  # already open and ignore
        
        if dev_name == None:
            if dev_sn == None:
                d = find_device('PM100USB')
            else:
                d = find_device('PM100USB', dev_sn)
            if d == None:
                return False
            else:
                dev_name = d[0]

        self.dev = usbtmc_dev(dev_name)
        if self.dev.FILE:
            self.dev.sendReset()
            self.device_info = self.dev.getInfo()
            self.sensor_info = self.dev.query("SYSTEM:SENSOR:IDN?")
            if self.wavelength != self.get_wavelength():
                self.set_wavelength( self.wavelength)
            if self.average != self.get_average():
                self.set_average( self.average)
            if self.bw != self.get_bw():
                self.set_bw( self.bw)
            self.active = True
            return True
        else:
            self.active = False
            return False

    def wait_measurement(self):
        # if another process uses measurement, it must wait
        while self.during_meas:
            pass
    
    def set_average(self, count):
        self.wait_measurement()
        self.dev.write("SENS:AVERAGE:COUNT "+str(count))
        self.average = count

    def get_average(self):
        self.wait_measurement()        
        return self.dev.query("SENS:AVER:COUNT?")

    def set_wavelength(self, wavelength):
        self.wait_measurement()
        self.dev.write("SENS:CORR:WAV "+str(wavelength))
        self.wavelength = wavelength

    def get_wavelength(self):
        self.wait_measurement()
        return self.dev.query("SENS:CORR:WAV?")

    def set_bw( self, bw):
        self.wait_measurement()
        self.dev.write("INPUT:FILT:LPAS:STATE "+str(bw))
        self.bw = bw
        
    def get_bw( self):
        self.wait_measurement()
        return self.dev.query("INPUT:FILT:LPAS:STATE?")
        
    def get_power( self):
        self.dev.write("CONF:POW")
        res = self.dev.query("READ?")
        return float(res[0])

    def get_temp( self):
        self.dev.write("CONF:TEMP")
        res = self.dev.query("READ?")
        return float(res[0])

    def get_data( self):
        self.wait_measurement()
        td = time.time()
        self.during_meas = True
        power = self.get_power()
        temp = self.get_temp()
        self.during_meas = False
        return td,power,temp

    def close(self):
        if self.active:
            self.active = False
            self.dev.close()
        
class tsp01:
    def __init__(self):
        self.dev_name = '/dev/usbtmc0'
        self.device_info = ''
        self.active = True
        self.during_meas = False
        
    def wait_measurement(self):
        # if another process uses measurement, it must wait
        while self.during_meas:
            pass

    def open(self, dev_name=None, dev_sn=None):
        if self.active:
            return True
        
        if dev_name == None:
            if dev_sn == None:
                d = find_device('TSP01')
            else:
                d = find_device('TSP01', dev_sn)
            if d == None:
                return None
            else:
                dev_name = d[0]

        self.dev = usbtmc_dev(dev_name)
        self.dev.sendReset()
        self.device_info = self.dev.getInfo()
        self.active = True

    def get_temp(self, ch=0):
        if ch==0:
            res= self.dev.query('SENS1:TEMP:DATA?')
        elif ch==1:
            res= self.dev.query('SENS3:TEMP:DATA?')
        elif ch==2:
            res= self.dev.query('SENS4:TEMP:DATA?')
        else:
            res = ['-100']
        return float(res[0])

    def get_humid(self):
        return self.dev.query('SENS2:HUM:DATA?')

    def get_data( self):
        self.wait_measurement()
        td = time.time()
        self.during_meas = True
        temp0 = self.get_temp()
        temp1 = self.get_temp(1)
        temp2 = self.get_temp(2)
        humid = self.get_humid()
        self.during_meas = False
        return td,temp0,temp1,temp2,humid

    def close(self):
        if self.active:
            self.active = False
            self.dev.close()
        
