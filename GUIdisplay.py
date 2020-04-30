import sys
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QLCDNumber, QGridLayout, \
    QMainWindow, QAction, qApp, QMessageBox, QPushButton, QSizePolicy, QTabWidget
from PyQt5.QtGui import QIcon, QCursor, QPixmap
from PyQt5 import QtGui
from PyQt5 import QtCore
import pyqtgraph as pg
import obd
import time
from datetime import datetime
from pytz import timezone

# Setting these as global variables for access from multiple scopes
startTime = None
endTime = None
connection = None
syncConn = None


class CarCommunication(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('C:\\Users\\jarahn\\PycharmProjects\\CarStuff\\IconPic.jpg'))
        self.initUI()

    def initUI(self):
        # QAction is an abstraction for actions performed with a menubar, toolbar, or keyboard shortcut
        exitAct = QAction(QIcon('exit24.png'), '&Exit', self)
        # Sets a keyboard shortcut for the specified QAction
        exitAct.setShortcut('Ctrl+Q')
        # This status tip is displayed in the status bar on mouse over of the menu item
        exitAct.setStatusTip('Exit application')
        # Emits signal to terminate application - this is how you connect a function to a menu item or button
        exitAct.triggered.connect(qApp.quit)
        self.statusBar()

        def checkTheCodes():
            checkForCodes = obd.commands.STATUS
            statusRsp = connection.query(checkForCodes)
            if not statusRsp.is_null():
                if statusRsp.value.DTC_count == 0:
                    codesDsp.display(0)
                    QMessageBox.information(self, 'Trouble Code Data', 'You have zero pending trouble codes.',
                                            QMessageBox.Ok, QMessageBox.Ok)
                else:
                    codesDsp.display(statusRsp.value.DTC_count)
                    readCodes.setEnabled(True)
                    freezeFrame.setEnabled(True)
                    clearCodes.setEnabled(True)
            else:
                readErr = "Unable to retrieve trouble code information."
                QMessageBox.information(self, 'Trouble Code Data', readErr, QMessageBox.Ok, QMessageBox.Ok)

        def readTheCodes():
            print('Codes read!')

            checkForCodes = obd.commands.STATUS
            statusRsp = connection.query(checkForCodes)

            if not statusRsp.is_null():
                if statusRsp.value.DTC_count == 0:
                    codeData = "No Codes!"
                else:
                    codeReader = obd.commands.GET_DTC
                    codeRsp = connection.query(codeReader)
                    # In case of error change back to str(codeRsp.value)
                    codeData = ' '.join(map(str, codeRsp.value))
            else:
                codeData = "Unable to retrieve trouble code information."

            QMessageBox.information(self, 'Trouble Code Data', codeData, QMessageBox.Ok, QMessageBox.Ok)

        def runFreezeFrame():
            checkForCodes = obd.commands.STATUS
            statusRsp = connection.query(checkForCodes)

            speedCmd = obd.commands.DTC_SPEED
            speedResponse = connection.query(speedCmd)

            if not statusRsp.is_null():
                if statusRsp.value.DTC_count == 0:
                    freezeData = "No Codes!"
                elif speedResponse.value is None:
                    freezeData = "Your vehicle does not store freeze frame information."
                else:
                    # get RPMs when code was thrown
                    rpmCmd = obd.commands.DTC_RPM
                    rpmResponse = connection.query(rpmCmd)
                    freezeData = "RPMs: " + rpmResponse.value

                    # get speed when code was thrown
                    speedCmd = obd.commands.DTC_SPEED
                    speedResponse = connection.query(speedCmd)
                    freezeData = "Speed: " + str(speedResponse.value)
            else:
                freezeData = "Unable to retrieve trouble code information."

            QMessageBox.information(self, 'Freeze Frame Data', freezeData, QMessageBox.Ok, QMessageBox.Ok)

        def clearTheCodes():
            checkForCodes = obd.commands.STATUS
            statusRsp = connection.query(checkForCodes)

            if not statusRsp.is_null():
                if statusRsp.value.DTC_count == 0:
                    clearMsg = "No codes to clear!"
                else:
                    codeClear = obd.commands.CLEAR_DTC
                    connection.query(codeClear)
                    clearMsg = "All codes cleared!"
                    codesDsp.display(0)
                    readCodes.setEnabled(False)
                    freezeFrame.setEnabled(False)
                    clearCodes.setEnabled(False)
            else:
                clearMsg = "Unable to retrieve trouble code information."

            QMessageBox.information(self, 'Clearing Codes', clearMsg, QMessageBox.Ok, QMessageBox.Ok)

        def startTripLog():
            print("starting trip!")

            # Establish asynch connection to monitor desired variables
            global connection
            global syncConn
            connection.close()
            obd.logger.setLevel(obd.logging.DEBUG)
            connection = obd.Async(portstr="\\.\\COM3", baudrate=38400, fast=False)
            syncConn = False

            def new_speed(s):
                speed.append(int(s.value.magnitude))

            def new_rpm(r):
                rpms.append(int(r.value.magnitude))

            def new_load(ld):
                engineLoad.append(int(ld.value.magnitude))

            connection.watch(obd.commands.SPEED, callback=new_speed)
            connection.watch(obd.commands.RPM, callback=new_rpm)
            connection.watch(obd.commands.ENGINE_LOAD, callback=new_load)

            # Start asynch connection
            connection.start()

            # start counter for graph purposes
            global startTime
            startTime = time.time_ns()
            stopTrip.setEnabled(True)

        def endTrip(prnt):
            print("ending the trip!")

            # Stop trip monitoring
            global connection
            global syncConn
            connection.stop()
            connection.close()

            global endTime
            endTime = time.time_ns()
            # Get the time in seconds
            timeSec = int((endTime - startTime) / 1000000000)

            tripSecs = len(speed)
            # Used in case callback functions return a few more values than total seconds
            tripzTime = range(0, tripSecs)

            # Convert speed from kph to mph
            for i in range(tripSecs):
                speed[i] = int(0.621371*speed[i])
            speedGraph.plot(tripzTime, speed, pen='g')
            rpmGraph.plot(tripzTime, rpms, pen='r')
            engineGraph.plot(tripzTime, engineLoad, pen='w')
            print("plotted!")

            # Trip log file i/o and data
            tripsFile = open("tLog.txt", "a")

            today = datetime.today()
            formDate = today.strftime("%B %d, %Y")    # put date in month/day/year format
            est = timezone('EST')   # Doesn't account for daylight savings, shows up as central time
            trpLogTime = datetime.now(est).strftime("%H:%M:%S")
            tripsFile.write("\n\nDate: " + formDate + " Time: " + trpLogTime + " C.T.\n")

            # Estimated distance math - Take the average miles per hour from the whole trip and divide by 60 then..
            # .. divide that by 60 to get miles per second. Multiply mi/sec with total seconds
            avgSpd = sum(speed)/len(speed)
            estDistance = ((avgSpd/60)/60 * timeSec)
            # truncate estimated distance to the hundreds place
            truncDist = int(estDistance*1000)
            truncDist = float(truncDist/1000)
            tripsFile.write("Total trip time: " + str(timeSec) + " Seconds. Estimated distance: " + str(truncDist)
                            + " Miles\n")

            # Information about the check engine light
            obd.logger.setLevel(obd.logging.DEBUG)
            connection = obd.OBD(portstr="\\.\\COM3", baudrate=38400, fast=False)
            syncConn = True
            checkForCodes = obd.commands.STATUS
            statusRsp = connection.query(checkForCodes)
            if not statusRsp.is_null():
                if statusRsp.value.DTC_count == 0:
                    tripsFile.write("Check Engine Light: Off\n")
                else:
                    tripsFile.write("Check Engine Light: On\n")
                    codeReader = obd.commands.GET_DTC
                    codeRsp = connection.query(codeReader)
                    # If this is giving an error change back to 'str(codeRsp.value)'
                    codeData = ' '.join(map(str, codeRsp.value))
                    tripsFile.write("Trouble Code Data: " + codeData + "\n")
            else:
                tripsFile.write("Unable to retrieve trouble code information.\n")
            connection.close()

            # Data for speed, rpms, engine load
            speedData = ' '.join(map(str, speed))
            rpmData = ' '.join(map(str, rpms))
            engineData = ' '.join(map(str, engineLoad))
            tripsFile.write("Speed list: " + speedData + "\n")
            tripsFile.write("RPM list: " + rpmData + "\n")
            tripsFile.write("Engine load list: " + engineData + "\n")

            tripsFile.close()

            # User message to remind them about entering trip info
            QMessageBox.information(self, 'Ending trip. ', 'Remember: You can add trip info in the past trips tab.',
                                    QMessageBox.Ok, QMessageBox.Ok)
            stopTrip.setEnabled(False)
            submitBtn.setEnabled(True)

        # This function handles all connection changes, including the initial connection
        # called every time the tab changes.
        def setConnection(tabIndex):
            print(tabIndex)
            '''
            global connection
            global syncConn
            connection.close()
            
            if tabIndex == 0:
                obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses for debugging
                connection = obd.Async(portstr="\\.\\COM3", fast=False)
                syncConn = False

                def new_spd(s):
                    kphNum = int(s.value.magnitude)
                    mphNum = int(0.621371*kphNum)
                    speedDsp.display(mphNum)

                def new_rotations(r):
                    rpmDsp.display(int(r.value.magnitude))

                def new_engineLd(ld):
                    loadDsp.display(int(ld.value.magnitude))

                def new_intakeT(t):
                    tempC = int(t.value.magnitude)
                    tempF = int(tempC * 9/5) + 32
                    tempDsp.display(tempF)

                connection.watch(obd.commands.SPEED, callback=new_spd)
                connection.watch(obd.commands.RPM, callback=new_rotations)
                connection.watch(obd.commands.ENGINE_LOAD, callback=new_engineLd)
                connection.watch(obd.commands.INTAKE_TEMP, callback=new_intakeT)
                # Start asynch connection
                connection.start()
                
            elif tabIndex == 1:
                if syncConn != True:
                    obd.logger.setLevel(obd.logging.DEBUG)  
                    connection = obd.OBD(portstr="\\.\\COM3", baudrate=38400, fast=False)
                    syncConn = True
            '''

        def submitLogInfo(odo, name, wthr):
            tripsFile = open("tLog.txt", "a")
            tripsFile.write("Current odometer: " + str(odo) + "\n")
            tripsFile.write("Trip driver: " + name + "\n")
            tripsFile.write("Trip weather conditions: " + wthr + "\n")
            odomTextB.clear()
            driverTextB.clear()
            weatherTextB.clear()
            tripsFile.close()
            QMessageBox.information(self, 'Success!', 'Your information has been added.', QMessageBox.Ok,
                                    QMessageBox.Ok)
            submitBtn.setEnabled(False)

        # create menu
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&Actions')
        fileMenu.addAction(exitAct)

        # MAIN DASHBOARD WIDGET

        speedL = QLabel('Speed (MPH):')
        RPM = QLabel('RPMs:')
        eLoad = QLabel('Engine Load (%):')
        tempr = QLabel('Intake Air Temp. (°f):')

        # number displays
        speedDsp = QLCDNumber(self)
        rpmDsp = QLCDNumber(self)
        loadDsp = QLCDNumber(self)
        tempDsp = QLCDNumber(self)

        # grid layout to manage widget placement
        dashLayout = QGridLayout()
        dashLayout.setSpacing(10)

        # think of the window as a board, first 2 numbers are placement next 2 are span of widget
        dashLayout.addWidget(speedL, 1, 0)
        dashLayout.addWidget(speedDsp, 1, 1, 2, 1)

        dashLayout.addWidget(RPM, 3, 0)
        dashLayout.addWidget(rpmDsp, 3, 1, 2, 1)

        dashLayout.addWidget(eLoad, 5, 0)
        dashLayout.addWidget(loadDsp, 5, 1, 2, 1)

        dashLayout.addWidget(tempr, 7, 0)
        dashLayout.addWidget(tempDsp, 7, 1, 2, 1)

        # ENGINE CODES WIDGET
        codesLayout = QGridLayout()
        codesLayout.setSpacing(0)

        # Allow buttons to change sizes
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        checkCodes = QPushButton('Check For Trouble Codes')
        checkCodes.setSizePolicy(sizePolicy)
        readCodes = QPushButton('Read Codes')
        readCodes.setSizePolicy(sizePolicy)
        freezeFrame = QPushButton('Get Freeze Frame Data')
        freezeFrame.setSizePolicy(sizePolicy)
        clearCodes = QPushButton('Clear Any Existing Codes')
        clearCodes.setSizePolicy(sizePolicy)

        # Button control for event determining access
        readCodes.setEnabled(False)
        freezeFrame.setEnabled(False)
        clearCodes.setEnabled(False)

        numCodesLbl = QLabel('Number of Trouble Codes: ')
        codesDsp = QLCDNumber(self)

        picLabel = QLabel('Check Engine Light')
        CELpic = QPixmap('check-engine-pic.png')
        picLabel.setPixmap(CELpic)

        checkCodes.clicked.connect(checkTheCodes)
        readCodes.clicked.connect(readTheCodes)
        freezeFrame.clicked.connect(runFreezeFrame)
        clearCodes.clicked.connect(clearTheCodes)

        # Title/number display layout
        codesLayout.addWidget(numCodesLbl, 0, 0)
        codesLayout.addWidget(codesDsp, 1, 0, 2, 1)

        # Image layout
        codesLayout.addWidget(picLabel, 1, 1, QtCore.Qt.AlignCenter)

        # Buttons layout
        codesLayout.addWidget(checkCodes, 5, 0, 1, 1)
        codesLayout.addWidget(readCodes, 5, 1, 1, 1)
        codesLayout.addWidget(freezeFrame, 6, 0, 1, 1)
        codesLayout.addWidget(clearCodes, 6, 1, 1, 1)

        # TRIP LOGGER WIDGET
        graphsLayout = QGridLayout()
        graphsLayout.setSpacing(10)

        # Create graph widgets
        speedGraph = pg.PlotWidget()
        rpmGraph = pg.PlotWidget()
        engineGraph = pg.PlotWidget()

        startTrip = QPushButton('Start Your Trip')
        stopTrip = QPushButton('Stop Your Trip')
        startTrip.clicked.connect(startTripLog)
        stopTrip.clicked.connect(endTrip)
        stopTrip.setEnabled(False)

        # Lists to store information from callback functions
        speed = []
        rpms = []
        engineLoad = []

        rpmGraph.setLabel('left', 'Revolutions', units='per second')
        rpmGraph.setLabel('bottom', 'Time', units='s')
        speedGraph.setLabel('left', 'Speed', units='MPH')
        speedGraph.setLabel('bottom', 'Time', units='s')
        engineGraph.setLabel('left', 'Engine Load', units='%')
        engineGraph.setLabel('bottom', 'Time', units='s')

        graphsLayout.addWidget(startTrip, 0, 1)
        graphsLayout.addWidget(stopTrip, 0, 3)
        graphsLayout.addWidget(speedGraph, 1, 1)
        graphsLayout.addWidget(rpmGraph, 1, 2)
        graphsLayout.addWidget(engineGraph, 1, 3)

        # PAST TRIPS WIDGET
        tripsLayout = QGridLayout()
        tripsLayout.setSpacing(10)

        # The following code was taken from:
        # https://stackoverflow.com/questions/50211133/open-a-pdf-by-clicking-on-qlabel-made-as-hyperlink
        tripLogTxt = QLabel()
        path = r"tLog.txt"  # r before "" treats the string as a raw string, no '\n' etc - (J.R.)
        url = bytearray(QUrl.fromLocalFile(path).toEncoded()).decode()
        text = "<a href={}>Past Trips Log </a>".format(url)
        tripLogTxt.setText(text)
        tripLogTxt.setOpenExternalLinks(True)
        tripLogTxt.show()

        submitBtn = QPushButton('Submit Information')
        submitBtn.setEnabled(False)
        sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        submitBtn.setSizePolicy(sizePolicy)
        submitBtn.clicked.connect(lambda: submitLogInfo(odomTextB.text(), driverTextB.text(), weatherTextB.text()))
        odomTextB = QLineEdit()
        odomTextB.setPlaceholderText("Odometer reading:")
        driverTextB = QLineEdit()
        driverTextB.setPlaceholderText("Driver name:")
        weatherTextB = QLineEdit()
        weatherTextB.setPlaceholderText("Current weather:")
        odomLbl = QLabel('Odometer:')
        driverLbl = QLabel('Driver:')
        weatherLbl = QLabel('Weather:')

        tripsLayout.addWidget(submitBtn, 2, 0, 1, 1)
        tripsLayout.addWidget(tripLogTxt, 2, 2, QtCore.Qt.AlignCenter)
        tripsLayout.addWidget(odomLbl, 0, 0)
        tripsLayout.addWidget(driverLbl, 0, 1)
        tripsLayout.addWidget(weatherLbl, 0, 2)
        tripsLayout.addWidget(odomTextB, 1, 0, QtCore.Qt.AlignCenter)
        tripsLayout.addWidget(driverTextB, 1, 1, QtCore.Qt.AlignCenter)
        tripsLayout.addWidget(weatherTextB, 1, 2, QtCore.Qt.AlignCenter)

        # Tabs can be added to a QTabWidget. The QTabWidget can be added to a layout and the layout to the window.
        tabsLayout = QGridLayout()
        tabsLayout.setSpacing(10)

        tabWidget = QTabWidget()

        dash = QWidget()
        dash.setLayout(dashLayout)
        tabWidget.addTab(dash, "Dashboard")

        cel = QWidget()
        cel.setLayout(codesLayout)
        tabWidget.addTab(cel, "Codes")

        cTrip = QWidget()
        cTrip.setLayout(graphsLayout)
        tabWidget.addTab(cTrip, "Current Trip")

        pTrip = QWidget()
        pTrip.setLayout(tripsLayout)
        tabWidget.addTab(pTrip, "Previous Trips")

        tabsLayout.addWidget(tabWidget, 0, 0)

        # this allows you to place a widget as the central widget - keeping it separate from the main window
        tabsWidg = QWidget()
        tabsWidg.setLayout(tabsLayout)
        self.setCentralWidget(tabsWidg)

        # Event handlers for tab selection (to make sure the correct connection is established)
        tabWidget.currentChanged.connect(setConnection)

        # Main styling for GUI
        dash.setStyleSheet("background-color: #7FDBFF")
        cel.setStyleSheet("background-color: #FF6F61")
        pTrip.setStyleSheet("background-color: #FCEED1")

        # Style for labels
        speedL.setFont(QtGui.QFont("Times", 11, weight=QtGui.QFont.Bold))
        RPM.setFont(QtGui.QFont("Times", 11, weight=QtGui.QFont.Bold))
        eLoad.setFont(QtGui.QFont("Times", 11, weight=QtGui.QFont.Bold))
        tempr.setFont(QtGui.QFont("Times", 11, weight=QtGui.QFont.Bold))
        numCodesLbl.setFont(QtGui.QFont("Times", 11, weight=QtGui.QFont.Bold))
        odomLbl.setFont(QtGui.QFont("Times", 11, weight=QtGui.QFont.Bold))
        driverLbl.setFont(QtGui.QFont("Times", 11, weight=QtGui.QFont.Bold))
        weatherLbl.setFont(QtGui.QFont("Times", 11, weight=QtGui.QFont.Bold))

        # style for buttons
        checkCodes.setStyleSheet("QPushButton { font-size: 8pt; font-weight: bold}")
        checkCodes.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        readCodes.setStyleSheet("QPushButton { font-size: 8pt; font-weight: bold}")
        readCodes.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        freezeFrame.setStyleSheet("QPushButton { font-size: 8pt; font-weight: bold}")
        freezeFrame.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        clearCodes.setStyleSheet("QPushButton { background-color: red; font-size: 8pt; font-weight: bold} }"
                                 "QPushButton:pressed { background-color: green }")
        clearCodes.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        startTrip.setStyleSheet("background-color: green; font-weight: bold")
        startTrip.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        stopTrip.setStyleSheet("background-color: red; font-weight: bold")
        stopTrip.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        submitBtn.setStyleSheet("QPushButton { font-size: 8pt; font-weight: bold}")
        submitBtn.setCursor(QCursor(QtCore.Qt.PointingHandCursor))

        self.setGeometry(525, 200, 900, 675)
        self.setWindowTitle('Vehicle Companion')
        self.show()
        setConnection(0)  # Handles the initial asynch connection


if __name__ == '__main__':

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Calls the application class we created
    ex = CarCommunication()
    
    # Enters the gui application into its main loop
    sys.exit(app.exec_())