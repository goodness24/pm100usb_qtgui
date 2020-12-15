# ThorLabs PM100USB Frontend (Qt version)
#  2020.12.7 v1.0 Goro Nishimura
#       12.15 v1.01 change graph title,
#                   start/stop button means recording now
#                   The program is always showing the count rate
#                   when it connects the device
#
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import threading
import time
import datetime
import numpy as np
import re
import os
import sys

import MeasureThorLabs
import ThorlabUSBTMC as thorlabs
from ThorlabUSBTMC import list_thorlabs_devinfo
import MeasureThorLabs as measThorlabs

verinfo = 'pm100usb_qtgui (PyQt5) v1.01(20201215)'

# PM100USB measurement event
class UpDateEvent( QObject):
    update = pyqtSignal(int)
    

# PM100USB measurement (wrapper for PyQt5)
class PM100USB_Measure( MeasureThorLabs.PM100USB):
    def __init__ (self, gui_win):
        super(PM100USB_Measure, self).__init__()
        self.gui_win = gui_win # keep parent window ID
        self.num = 0
        self.UpDateEvent = UpDateEvent()
                    
    def timerMeasurement(self, num):       
        next_call = time.time() # the initial time
        while self.measurement and num!=0:
            next_call = next_call + self.period
            try:
                time.sleep(next_call - time.time())
            except:
                pass
            self.measure()
            self.UpDateEvent.update.emit( len(self.power))
            if num>0:
                num -=1
        self.measurement = False
        self.num = num
        
    def startMeasurement(self, num=1):
        if self.active:              # check device connected
            if not self.measurement: # check other measurement process
                self.measurement = True
                self.measure()  # the first data
                num -= 1
                if num!=0: # continue measurement in different thread
                    self.measurement_id=threading.Thread(
                        target=self.timerMeasurement,
                        args=([num])
                    )
                    self.measurement_id.daemon = True
                    self.UpDateEvent.update.connect(self.onUpdate)
                    self.measurement_id.start()

                else:
                    self.measurement = False

    def onUpdate(self, value):
        self.gui_win.onUpdate(value)

    def stopMeasurement(self):
        if self.measurement:
            self.measurement = False
            try:
                self.measurement_id
                self.measurement_id.join()
            except NameError:
                pass

    def continueMeasurement(self):
        if self.active and not self.measurement:
            self.startMeasurement( self.num)

# Console for PM100USB: display data and some information
#
    
class PM100USB_Cont(QWidget):
    def __init__ (self, parent=None):
        super().__init__()

        self.parent = parent
       
        pm100usb_conf_layout = QHBoxLayout() # main layout

        # Power indicator
        self.InitDataPanel()
        self.meas_buttons_init()
        self.InitDevConfInfo()
        self.conf_oc_buttons_init()

        pm100usb_conf_layout.addLayout( self.datapanel_layout)
        pm100usb_conf_layout.addLayout( self.startstop_layout)
        pm100usb_conf_layout.addLayout( self.devconf_layout)
        pm100usb_conf_layout.addLayout( self.confbutton_layout)
        
        self.setLayout( pm100usb_conf_layout)
        
 
    def changeFontSize( self, label, val):
        font = label.font()
        font.setPointSize(val)
        label.setFont(font)
        
    def InitDataPanel(self):
        self.datapanel_layout = QGridLayout()
        # main power indicator
        self.power_text = QLabel('')
        self.changeFontSize( self.power_text, 32)
        self.power_text.setStyleSheet('background-color: white')
        self.power_text.setFixedWidth(160)
        self.power_text.setAlignment(Qt.AlignRight)
        self.powerunit_text = QLabel('')
        self.changeFontSize( self.powerunit_text, 24)
        self.powerunit_text.setFixedWidth(50)
        
        # Max/Min/Temp indicator

        self.max_label = QLabel('max')
        self.max_label.setAlignment(Qt.AlignRight)
        self.max_text = QLabel('')
        self.changeFontSize( self.max_text, 12)
        self.max_text.setStyleSheet('background-color: white')
        self.max_text.setFixedWidth(60)
        self.maxunit_text = QLabel('')
        self.changeFontSize( self.maxunit_text, 12)
        
        self.min_label = QLabel('min')
        self.min_label.setAlignment(Qt.AlignRight)
        self.min_text = QLabel('')
        self.changeFontSize( self.min_text, 12)
        self.min_text.setStyleSheet('background-color: white')
        self.min_text.setFixedWidth(60)
        self.minunit_text = QLabel('')
        self.changeFontSize( self.minunit_text, 12)
        
        self.temp_label = QLabel('T')
        self.temp_label.setAlignment(Qt.AlignRight)
        self.temp_text = QLabel('')
        self.changeFontSize( self.temp_text, 12)
        self.temp_text.setStyleSheet('background-color: white')
        self.temp_text.setFixedWidth(40)    
        self.tempunit_text = QLabel('C')
        self.changeFontSize( self.tempunit_text, 12)
        self.tempunit_text.setAlignment(Qt.AlignLeft)

        self.UpdateDataPanel( [0,0,0,0])

        self.datapanel_layout.addWidget( self.power_text, 0,0,-1,1, Qt.AlignVCenter|Qt.AlignLeft)
        self.datapanel_layout.addWidget( self.powerunit_text, 0,1,-1,1, Qt.AlignVCenter | Qt.AlignRight)
        self.datapanel_layout.addWidget( self.max_label, 0,3, Qt.AlignTop |Qt.AlignLeft)
        self.datapanel_layout.addWidget( self.max_text, 0,4, Qt.AlignCenter)
        self.datapanel_layout.addWidget( self.maxunit_text, 0,5, Qt.AlignLeft|Qt.AlignVCenter)
        self.datapanel_layout.addWidget( self.min_label, 1,3, Qt.AlignTop |Qt.AlignLeft)
        self.datapanel_layout.addWidget( self.min_text, 1,4, Qt.AlignCenter)
        self.datapanel_layout.addWidget( self.minunit_text,1,5, Qt.AlignLeft|Qt.AlignVCenter)
        self.datapanel_layout.addWidget( self.temp_label, 2,3, Qt.AlignTop |Qt.AlignLeft)
        self.datapanel_layout.addWidget( self.temp_text, 2,4, Qt.AlignCenter)
        self.datapanel_layout.addWidget( self.tempunit_text, 2,5, Qt.AlignLeft|Qt.AlignVCenter)

    # power unit
    def power_unit( self, pw):
        apw = abs(pw)
        if apw<1.0e-6:
            return pw*1.0e9,'pW'
        if apw<1.0e-3:
            return pw*1.0e6,'nW'
        if apw<1.0:
            return pw*1.0e3,'uW'
        if apw<1000.0:
            return pw,'mW'
        return pw/1000.0,'W '

    def UpdateDataPanel(self, data):
        r = self.power_unit( data[0])        
        self.power_text.setText('{:>8.2f}'.format(r[0]))
        self.powerunit_text.setText(r[1])
        self.power_text.setAlignment(Qt.AlignRight)
        self.powerunit_text.setAlignment(Qt.AlignLeft)
        
        r = self.power_unit( data[2])
        self.max_text.setText('{:>8.2f}'.format(r[0]))
        self.maxunit_text.setText(r[1])
        self.max_text.setAlignment(Qt.AlignRight)
        self.maxunit_text.setAlignment(Qt.AlignLeft)
        
        r = self.power_unit( data[1])        
        self.min_text.setText('{:>8.2f}'.format(r[0]))
        self.minunit_text.setText(r[1])
        self.min_text.setAlignment(Qt.AlignRight)
        self.minunit_text.setAlignment(Qt.AlignLeft)
        
        self.temp_text.setText('{:5.1f}'.format(data[3]))
        self.temp_text.setAlignment(Qt.AlignRight)

    def meas_buttons_init(self):
        # Measurement Start/Stop/Clear Button
        self.startstop_layout = QVBoxLayout()

        # Start/Stop Button
        self.startstopButton = QPushButton('Start')
        self.startstopButton.clicked.connect( self.onStartStop)
        self.startstop('0')
        if not self.parent.isActive_pm100usb():
            self.startstopButton.setDisabled(True)

        # Data Clear Button
        clearButton = QPushButton('Clear')
        clearButton.clicked.connect( self.onClear)

        self.startstop_layout.addWidget( self.startstopButton)
        self.startstop_layout.addWidget( clearButton)

    # Initialize device and configuration information
    def InitDevConfInfo(self):
        self.devconf_layout = QGridLayout()
        
        # Init Dev Info
        
        self.devinfo_label = QLabel('device:')
        self.devinfo_text = QLabel( self.device_info_str())
        self.devinfo_text.setFixedWidth( 300)
        self.devinfo_text.setAlignment( Qt.AlignLeft)
        self.sensinfo_label = QLabel('sensor:')
        self.sensinfo_text = QLabel(self.sensor_info_str())
        self.sensinfo_text.setFixedWidth( 300)
        self.sensinfo_text.setAlignment( Qt.AlignLeft)
        self.changeFontSize( self.devinfo_label, 10)
        self.changeFontSize( self.devinfo_text, 10)
        self.changeFontSize( self.sensinfo_label, 10)
        self.changeFontSize( self.sensinfo_text, 10)
        
        self.devconf_layout.addWidget( self.devinfo_label,0,0,1,1,Qt.AlignLeft) 
        self.devconf_layout.addWidget( self.devinfo_text,0,1,1,1,Qt.AlignRight)
        self.devconf_layout.addWidget( self.sensinfo_label,1,0,1,1,Qt.AlignLeft)
        self.devconf_layout.addWidget( self.sensinfo_text,1,1,1,1,Qt.AlignRight)
        
        # Init Conf Info
        self.confinfo_layout = QHBoxLayout()

        self.wl_text  = QLabel('')
        self.changeFontSize( self.wl_text, 10)

        self.ave_text = QLabel('')
        self.changeFontSize( self.ave_text, 10)

        self.bw_text = QLabel('')
        self.changeFontSize( self.bw_text, 10)
        
        self.p_text  = QLabel('')
        self.changeFontSize( self.p_text, 10)
        self.UpdateConfInfo()
        
        self.confinfo_layout.addWidget( self.wl_text)
        self.confinfo_layout.addWidget( self.ave_text)
        self.confinfo_layout.addWidget( self.bw_text)
        self.confinfo_layout.addWidget( self.p_text)
                                
        self.devconf_layout.addLayout( self.confinfo_layout, 2, 0, 1, 4)

    # update configuration information
    def UpdateConfInfo(self):
        wl_str = "WL: "+str(self.parent.pm100usb.wavelength)+"(nm)"
        self.wl_text.setText( wl_str)
        ave_str = "Ave:"+str(self.parent.pm100usb.average)+' '
        self.ave_text.setText( ave_str)
        if self.parent.pm100usb.bw == 0:
            bw_str = "BW: high"
        else:
            bw_str = "BW:  low"
        self.bw_text.setText( bw_str)
        p_str = "Period: " + '{:.2f}'.format( self.parent.pm100usb.period) + "(sec)"
        self.p_text.setText( p_str)


    def conf_oc_buttons_init(self):
        # Config Button and Open/Close button
        self.confbutton_layout = QVBoxLayout()
        confButton = QPushButton('Config')
        confButton.clicked.connect( self.onConf)

        self.opencloseButton = QPushButton( 'Close')
        self.opencloseButton.clicked.connect( self.onOpenClose)
        self.openclose('0')

        self.confbutton_layout.addWidget( confButton)
        self.confbutton_layout.addWidget( self.opencloseButton)

        
    # Button Event Handling of Main Panel
    def startstop(self, state='0'):
        if state=='1': # open the device
            self.startstopButton.setStyleSheet('QPushButton {'
                                               'color: green;'
                                               '}')
            self.startstopButton.setText('Stop')
            self.startstop_state='1'
        else:
            self.startstopButton.setStyleSheet('QPushButton {'
                                               'color: red;'
                                               '}')
            self.startstopButton.setText('Start')
            self.startstop_state='0'       

    def onStartStop(self, event):
        if self.startstop_state=='0':
#            self.parent.startstop_pm100usb(True)
            self.parent.pm100usb.recording = True
            self.startstop('1')
        else:
#            self.parent.startstop_pm100usb(False)
            self.parent.pm100usb.recording = False
            self.startstop('0')

    def onClear(self, event):
        self.parent.pm100usb.init_data()
        self.parent.graphpanel.upDate()
        
    def openclose(self, state='0'):
        if state=='1': # open the device
            self.opencloseButton.setStyleSheet('QPushButton {'
                                               'color: #00ff00;'
                                               '}')
            self.opencloseButton.setText('Close')
            self.parent.startstop_pm100usb(True)
            self.open_state='1'
        else:
            self.opencloseButton.setStyleSheet('QPushButton {'
                                               'color: #ff0000;'
                                               '}')
            self.opencloseButton.setText('Connect')
            self.parent.startstop_pm100usb(False)
            self.open_state='0'       

    def onOpenClose(self, event):
        if self.open_state=='0':
            self.parent.openclose_pm100usb( True)

            if self.parent.isActive_pm100usb(): # if the device activates,
                self.openclose('1')  # change button color and label
                self.devinfo_text.setText( self.device_info_str())
                self.sensinfo_text.setText( self.sensor_info_str())
                self.startstopButton.setEnabled(True)
        else:
            self.openclose('0')
            self.parent.openclose_pm100usb( False)
            self.devinfo_text.setText( '')
            self.sensinfo_text.setText( '')
            self.startstopButton.setDisabled(True)

        self.startstop('0')
        
    def onConf(self, event):
        self.conf_frame = PM100USB_Configuration_Frame(self)
        if self.conf_frame.exec_():
            self.UpdateConfInfo()
        else:
            pass

    def onUpdate(self, data):
        self.UpdateDataPanel(data)

    def device_info_str(self):
        if len(self.parent.pm100usb.device_info)==0:
            return ''
        return self.parent.pm100usb.dev_name+' (' \
            + ','.join(self.parent.pm100usb.device_info)+')'

    def sensor_info_str(self):
        if len(self.parent.pm100usb.sensor_info)==0:
            return ''
        return ','.join(self.parent.pm100usb.sensor_info)


class PM100USB_Configuration_Frame( QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setObjectName('PM100USB Configuration')

        self.parent = parent
        self.dev = self.parent.parent.get_pm100usb_param()

        # selection of usbtmc device
        device_name_label = QLabel( 'Device')
        
        if not self.parent.parent.isActive_pm100usb():
            self.dev_list = list_thorlabs_devinfo('PM100USB')
            idx = 0
            for d in self.dev_list:
                if d.split(':')[0]!= self.dev[0]:
                    idx +=1
            if idx>=len(self.dev_list):
                idx = 0

            if len(self.dev_list) != 0:
                self.device_selection = QComboBox()
                self.device_selection.addItems( self.dev_list)
                self.device_selection.setCurrentIndex(idx)
            else:
                self.device_selection = QLabel('No Device Found')
        else:
            self.dev_list = [self.parent.device_info_str().replace(' ',':')]
            self.device_selection = QComboBox()
            self.device_selection.addItems( self.dev_list)
            self.device_selection.setCurrentIndex(0)
        #
        if self.parent.parent.isActive_pm100usb():
            self.device_selection.setEnabled(False)
            
        # device name and selector
        device_nameLabel = QLabel('Thorlabs PM100USB')
        device_namelayout = QVBoxLayout( )
        device_namelayout.addWidget( device_name_label, Qt.AlignLeft)
        device_namelayout.addWidget( self.device_selection, 0)
        #

        ItemsLabel = QLabel('Measurement Condition')
        ConfItemlayout = QGridLayout()

        wavelength_label = QLabel('Wavelength (350-1100 nm)')
        self.wavelength_input = QLineEdit( str(self.dev[1]))
        self.wavelength_input.setValidator(QtGui.QIntValidator())
        
        ConfItemlayout.addWidget( wavelength_label, 0, 0)
        ConfItemlayout.addWidget( self.wavelength_input, 0, 1)

        average_label = QLabel( 'Average Count (1-500)')
        self.average_input = QLineEdit( str(self.dev[2]))
        self.average_input.setValidator(QtGui.QIntValidator())
        
        ConfItemlayout.addWidget( average_label, 1, 0)
        ConfItemlayout.addWidget( self.average_input, 1, 1)

        lowpass_label = QLabel( 'Band Width')
        self.lowpass_low = QRadioButton( 'low')
        self.lowpass_high = QRadioButton( 'high')
        if self.dev[3]!=0:
            self.lowpass_low.setChecked(True)
        else:
            self.lowpass_high.setChecked(True)           
        lowpass_input = QButtonGroup()
        lowpass_input.addButton( self.lowpass_low)
        lowpass_input.addButton( self.lowpass_high)
        lowpass_input_layout = QHBoxLayout( )
        lowpass_input_layout.addWidget( self.lowpass_low)
        lowpass_input_layout.addWidget( self.lowpass_high)
        
        ConfItemlayout.addWidget( lowpass_label,2,0)
        ConfItemlayout.addLayout( lowpass_input_layout, 2, 1, 1, 2)

        period_label = QLabel('Measurement Period\n(50-10000ms)')
        self.period_input = QLineEdit( str(self.dev[4]))
        self.period_input.setValidator(QtGui.QIntValidator())
        
        ConfItemlayout.addWidget( period_label, 3, 0)
        ConfItemlayout.addWidget( self.period_input, 3, 1)
        
        # make buttons to set or cancel to store the parameters
        setbutton = QPushButton('Set')
        cancelbutton = QPushButton( 'Cancel')
        cancelbutton.setDefault(True)
        setbutton.setAutoDefault(False)
        self.buttonBox = QDialogButtonBox(Qt.Horizontal)
        self.buttonBox.addButton( cancelbutton, QDialogButtonBox.RejectRole)
        self.buttonBox.addButton( setbutton, QDialogButtonBox.AcceptRole)
        self.buttonBox.accepted.connect(self.onSet)
        self.buttonBox.rejected.connect(self.reject) # close dialog
        
        frame_layout = QVBoxLayout() # The sizer for all items
        frame_layout.addLayout( device_namelayout)
        frame_layout.addLayout( ConfItemlayout)
        frame_layout.addWidget( self.buttonBox)

        self.setLayout( frame_layout)

    def onSet(self):
        # read input and set them as the configuration parameters
        if len(self.dev_list)!=0:
            dn =self.dev_list[self.device_selection.currentIndex()]
            dn = re.split('[ :]', dn)[0] # only take device name
        else:
            dn = self.dev[0]
        wl = int(self.wavelength_input.text())
        ave = int(self.average_input.text())
        if self.lowpass_low.isChecked():
            bw = 1
        else:
            bw = 0
        period = int(self.period_input.text())
        self.parent.parent.set_pm100usb_param( [dn,wl,ave,bw,period])
        self.done(1)  # close dialog box

class TimeAxisItem(pg.AxisItem): # this class is for the horizontal axis
    """Internal timestamp for x-axis"""
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)
        self.enableAutoSIPrefix(enable=False) # prevent the scaling label
        
    def tickStrings(self, values, scale, spacing):
        """Function overloading the weak default version to provide timestamp"""

        return [datetime.datetime.fromtimestamp(value).strftime('%H:%M:%S') for value in values]        

class GraphPanel(QWidget):
    def __init__(self, parent=None):
        super(GraphPanel, self).__init__(parent)
        #
        self.parent = parent
        self.maximumData = 1200
        
        # plot panel setup
        self.figure = pg.PlotWidget(axisItems={'bottom': TimeAxisItem(orientation='bottom')})

        self.figure.setMouseEnabled(x=False, y=False)
        self.figure.setLabel('left', 'Power (mW)')
        self.figure.setLabel('bottom', 'Time (H:M:S)')
        self.figure.setBackground('k')
        self.figure.showGrid( x=True, y=True)
        self.figure.setMouseEnabled( x=True, y=False)

        self.pen1 = pg.mkPen( color=(255, 0 , 0), width=0.5)
        self.curve = self.figure.plot(pen=self.pen1)
        
        self.initDraw()

        self.graphlayout = QVBoxLayout()
        self.graphlayout.addWidget(self.figure)
        self.setLayout( self.graphlayout)

    def initDraw(self):
        self.curve.setData([0],[0]) 
       
    def draw(self):       
        idx = len(self.parent.pm100usb.power)
        
        if idx > self.maximumData:
            xmax_idx = idx-1
            xmin_idx = idx - self.maximumData
        else:
            xmax_idx = self.maximumData-1
            xmin_idx = 0

        if idx<2:
            ymin = -0.1
            ymax = 0.1
            now = datetime.datetime.now()
            xmin = datetime.datetime.timestamp(datetime.datetime(*now.timetuple()[:6]))
        else:
            ymin = min(self.parent.pm100usb.power[xmin_idx:idx])
            ymax = max(self.parent.pm100usb.power[xmin_idx:idx])
            if ymin==ymax:
                ymax = ymin + 0.1
            xm = datetime.datetime.fromtimestamp(self.parent.pm100usb.time[xmin_idx])
            xmin = datetime.datetime.timestamp(datetime.datetime(*xm.timetuple()[:6]))
        xmax = xmin +self.parent.pm100usb.period*self.maximumData+1.0
         
        self.figure.setXRange(xmin, xmax)
        self.figure.setYRange(ymin, ymax)
               
        if idx>0:        
            self.curve.setData(self.parent.pm100usb.time[1:xmax_idx], np.array(self.parent.pm100usb.power[1:xmax_idx]))
      
    def upDate(self):
        self.draw()

    def upDateTitle(self, isopen):
        if isopen:
            self.figure.setTitle('PM100USB ('+self.parent.pm100usb.dev_name+')')
        else:
            self.figure.setTitle('PM100USB')
        
class MainFrame(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainFrame, self).__init__(*args,**kwargs)

        self.setWindowTitle('PM100USB Controller (QT)')
        self.maincontainer = QWidget()
        self.mainmenubar()

        main_layout = QVBoxLayout()
        self.maincontainer.setLayout( main_layout)      
     
        self.pm100usb = PM100USB_Measure(self)
        self.contpanel = PM100USB_Cont(self)
        self.graphpanel = GraphPanel(self)
        
        main_layout.addWidget( self.contpanel)
        main_layout.addWidget( self.graphpanel)

        self.setCentralWidget(self.maincontainer)       
        self.InitialFilePath()

    def mainmenubar(self):
        self.menu = self.menuBar()
        self.file = self.menu.addMenu('F&ile')
        
        SaveData = QtGui.QAction('S&ave Data', self)
        SaveData.setShortcut('Ctrl+S')
        SaveData.setStatusTip('Save Data')
        SaveData.triggered.connect(self.onSaveData)
        
        Destroy = QtGui.QAction('E&xit', self)
        Destroy.setShortcut('Ctrl+X')
        Destroy.setStatusTip('Finish Application')
        Destroy.triggered.connect(self.close)

        self.file.addAction(SaveData)
        self.file.addAction(Destroy)
        
    def closeEvent( self, event):
        close = QMessageBox.question(self,
                                     "QUIT?",
                                     "Are you sure want to EXIT?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if close == QMessageBox.Yes:
            self.openclose_pm100usb( False)
            self.close()
        else:
            event.ignore()

    def InitialFilePath(self):
        self.previousFile='data.txt'
        self.previousDir=os.getcwd()

    def onSaveData( self, event):
        fileChoices = "Text (*.txt) ;; All (*.*)"

        fileName, _ = QFileDialog.getSaveFileName(self, 'Save Data as ...', self.previousDir, fileChoices, self.previousFile)
        if len(fileName)!= 0:
            meas = self.pm100usb.measurement
            if meas:
                self.pm100usb.stopMeasurement()

            outFile = open( fileName, 'w')
            outFile.write( '# '+verinfo+'\n')
            outFile.write( '# '+ self.pm100usb.dev_name \
                           + ' (' + ','.join(self.pm100usb.device_info)+')\n')
            outFile.write( '# ' \
                           + ','.join(self.pm100usb.sensor_info)+'\n')
            outFile.write( '# WL:'+str(self.pm100usb.wavelength) \
                           +' AVE:'+str(self.pm100usb.average) \
                           +' BW:'+str(self.pm100usb.bw) \
                           +' PERIOD:'+str(self.pm100usb.period) + '\n')
            for i in range(len(self.pm100usb.power)):
                tm = datetime.datetime.fromtimestamp(self.pm100usb.time[i])
                outFile.write(str(i)+' ' \
                              +tm.strftime('%H:%M:%S.%f')[:11]\
                              +' '+'{:.4g}'.format(self.pm100usb.power[i]) \
                              +' '+'{:.1f}'.format(self.pm100usb.temp[i])+'\n')
            outFile.close()

            self.previousDir, self.previousFile = os.path.split(fileName)

            if meas:
                self.pm100usb.continueMeasurement()
            
    def get_pm100usb_param( self):
        return [self.pm100usb.dev_name,
                self.pm100usb.wavelength,
                self.pm100usb.average,
                self.pm100usb.bw,
                int(self.pm100usb.period*1000)]

    def set_pm100usb_param( self, params):
        if not self.pm100usb.active:
            self.pm100usb.dev_name = params[0]
            self.pm100usb.wavelength = params[1]
            self.pm100usb.average = params[2]
            self.pm100usb.bw = params[3]
            self.pm100usb.period = params[4]/1000
        else:
            if self.pm100usb.dev_name == params[0]:
                meas = self.pm100usb.measurement
                if meas:
                    self.pm100usb.stopMeasurement()
                if self.pm100usb.wavelength != params[1]:
                    self.pm100usb.set_wavelength( params[1])
                if self.pm100usb.average != params[2]:
                    self.pm100usb.set_average( params[2])
                if self.pm100usb.bw != params[3]:
                    self.pm100usb.set_bw( params[3])
                if self.pm100usb.period != params[4]/1000:
                    self.pm100usb.period = params[4]/1000
                if meas:
                    self.pm100usb.continueMeasurement()               

    def isActive_pm100usb( self):
        return self.pm100usb.active

    def isMeasurement_pm100usb( self):
        return self.pm100usb.measurement

    def openclose_pm100usb( self, openclose):
        if openclose:
            if not self.pm100usb.active:
                self.pm100usb.open(self.pm100usb.dev_name)
                self.graphpanel.upDateTitle( True)
        else:
            self.pm100usb.stopMeasurement()
            if self.pm100usb.active:
                self.pm100usb.close()
                self.graphpanel.upDateTitle( False)

    def startstop_pm100usb( self, startstop):
        if startstop:
            self.pm100usb.startMeasurement(0)
        else:
            self.pm100usb.stopMeasurement()

    def onUpdate( self, value):
#            idx = value -1
#            data = [self.pm100usb.power[idx], \
#                    self.pm100usb.maxmin_power[0],\
#                    self.pm100usb.maxmin_power[1],\
#                    self.pm100usb.temp[idx]]
#            self.contpanel.onUpdate( data)
        data = [self.pm100usb.current_power,
                self.pm100usb.maxmin_power[0],\
                self.pm100usb.maxmin_power[1],\
                self.pm100usb.current_temp]
        self.contpanel.onUpdate( data)
        if self.pm100usb.recording:
            self.graphpanel.upDate()
            
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    '''
    dark_palette = QtGui.QPalette()
    dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.WindowText, Qt.white)
    dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QtGui.QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QtGui.QPalette.Text, Qt.white)
    dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QtGui.QPalette.BrightText, Qt.red)
    dark_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.HighlightedText, Qt.black)

    app.setPalette(dark_palette)

    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")
    '''
    frame=MainFrame()
    frame.show()
    sys.exit(app.exec_())
