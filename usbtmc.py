# Simple USBTMC interface using Linux Kernel USBTMC device
#   I have added a routine to get usbtmc devices and information
#   v1.0 2020.11.25 Goro Nishimura
#
import os
import glob

def list_devices():
    "List all connected USBTMC devices associated to /dev/usbtmc*"
    return glob.glob("/dev/usbtmc*")


def list_devinfo():
    "List info for all connected USBTMC devices"
    res = []

    for dev in list_devices():
        usbtmc_dev = USBTMC( dev)
        usbtmc_dev.sendReset()
        info = usbtmc_dev.getInfo()
        dev_info = [dev]
        dev_info += info[0].split(',')
        res.append( dev_info)
        usbtmc_dev.close()

    return res

def find_device(Product=None, iSerial=None):
    "Find USBTMC instrument"

    devs = list_devinfo()

    if len(devs) == 0:
        return None

    for dev in devs:
        # match VID and PID
        found = dev[2] == Product
        if not found:
            continue

        if iSerial is None:
            return dev
        else:
            s = ''

            # try reading serial number
            try:
                s = dev[3]
            except:
                pass

            if iSerial == s:
                return dev

    return None


class USBTMC(object):
    """Simple implementation of a USBTMC device driver, in the style of visa.h
    """

    def __init__(self, device="/dev/usbtmc0"):
        self.device = device
        try:
            self.FILE = os.open(device, os.O_RDWR)
        except OSError:
            self.FILE = None

    def write(self, command):
        os.write(self.FILE, command.encode('ascii'))

    def read(self, length=None):
        if length is None:
            length = 4000
        return os.read(self.FILE, length)

    def query(self, command, length=None):
        self.write(command)
        return self.read(length=length).decode('ascii').splitlines()

    def ask_for_value(self, command):
        return eval(self.ask(command).strip())

    def getInfo(self):
        return self.query("*IDN?")

    def sendReset(self):
        self.write("*RST")

    def close(self):
        os.close(self.FILE)

if __name__ == "__main__":
    inst = USBTMC()
