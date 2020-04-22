import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtGui
import pyqtgraph as pg
import obd
import time
from datetime import datetime
from pytz import timezone

# Setting these as global variables for access from callback function
'''
speedDsp = None
rpmDsp = None
loadDsp = None
tempDsp = None
'''
startTime = None
endTime = None
connection = None


class Example(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setStyleSheet = """
                 QMainWindow{
                 background-color: aqua
                 }
        """
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
        # This is highlighted for some reason but still works
        exitAct.triggered.connect(qApp.quit)    # could I stop the asynch connection using this?
        self.statusBar()

        def checkTheCodes():
            print('Checking for codes!')
            checkForCodes = obd.commands.STATUS
            statusRsp = connection.query(checkForCodes)
            if not statusRsp.is_null():
                if statusRsp.value.DTC_count == 0:
                    codesDsp.display(0)
                else:
                    codesDsp.display(statusRsp.value.DTC_count)
                    readCodes.setEnabled(True)
                    freezeFrame.setEnabled(True)
                    clearCodes.setEnabled(True)
            else:
                print("Unable to retrieve trouble code information.")

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
                    # Extract info out of the response tuple (codes) or list if multiple codes -ASK RANDY HOW TO DO THIS
            else:
                codeData = "Unable to retrieve trouble code information."
            QMessageBox.information(self, 'Trouble Code Data', codeData, QMessageBox.Ok, QMessageBox.Ok)

        def runFreezeFrame():
            print('Getting freeze frame data!')

            checkForCodes = obd.commands.STATUS
            statusRsp = connection.query(checkForCodes)

            if not statusRsp.is_null():
                if statusRsp.value.DTC_count == 0:
                    freezeData = "No Codes!"
                else:
                    # get RPMs when code was thrown
                    '''
                    rpmCmd = obd.commands.DTC_RPM
                    rpmResponse = connection.query(rpmCmd)
                    freezeData = "RPMs: " + rpmResponse.value
                    '''

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
            else:
                clearMsg = "Unable to retrieve trouble code information."

            QMessageBox.information(self, 'Clearing Codes', clearMsg, QMessageBox.Ok, QMessageBox.Ok)

        def startTripLog(self):
            print("starting trip!")

            # restart asynch connection
            global connection
            connection.close()
            obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses for debugging purposes
            connection = obd.Async(portstr="\\.\\COM3", baudrate=38400, fast=False)

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
            # Enable stopping of trip
            stopTrip.setEnabled(True)

        def endTrip(prnt):
            print("ending the trip!")

            # Stop Asynch connection
            global connection
            connection.stop()
            connection.close()

            global endTime
            endTime = time.time_ns()
            timeSec = int((endTime - startTime) / 1000000000)
            tripTime = range(0, int(timeSec))
            '''
            print(startTime)
            print(endTime)
            print(tripTime)
            print(*speed)
            print(*rpms)
            '''
            tripSecs = len(speed)
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

            # Trip time in seconds and estimated distance
            # Estimated distance math - Take the average miles per hour from the whole trip and divide by 60 then..
            # .. divide that by 60 to get miles per second. Multiply mi/sec with total seconds
            avgSpd = sum(speed)/len(speed)
            estDistance = ((avgSpd/60)/60 * timeSec)
            # truncate estimated distance to the hundreds place
            truncDist = int(estDistance*1000)
            truncDist = float(truncDist/1000)
            tripsFile.write("Total trip time: " + str(timeSec) + " Seconds. Estimated distance: " + str(truncDist)
                            + "\n")

            # Information about the check engine light
            obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses - debugging purposes
            connection = obd.OBD(portstr="\\.\\COM3", baudrate=38400, fast=False)
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
            # connection.stop()
            connection.close()

            # Data for speed, rpms, engine load
            speedData = ' '.join(map(str, speed))
            rpmData = ' '.join(map(str, rpms))
            engineData = ' '.join(map(str, engineLoad))
            tripsFile.write("Speed list: " + speedData + "\n")
            tripsFile.write("RPM list: " + rpmData + "\n")
            tripsFile.write("Engine load list: " + engineData + "\n")

            tripsFile.close()

        # This function handles all connection changes, including the initial connection
            # - called every time the tab changes.
        def setConnection(tabIndex):
            print(tabIndex)
            '''
            global connection
            # connection.stop()
            connection.close()
            
            if tabIndex == 0:
                obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses for debugging
                connection = obd.Async(portstr="\\.\\COM3", fast=False)

                def new_spd(s):
                    kphNum = int(s.value.magnitude)
                    mphNum = int(0.621371*kphNum)
                    speedDsp.display(mphNum)

                def new_rotations(r):
                    rpmDsp.display(int(r.value.magnitude))

                def new_engineLd(ld):
                    loadDsp.display(int(ld.value.magnitude))

                def new_intakeT(t):
                    tempDsp.display(int(t.value.magnitude))

                connection.watch(obd.commands.SPEED, callback=new_spd)
                connection.watch(obd.commands.RPM, callback=new_rotations)
                connection.watch(obd.commands.ENGINE_LOAD, callback=new_engineLd)
                connection.watch(obd.commands.INTAKE_TEMP, callback=new_intakeT)
                # Start asynch connection
                connection.start()
                
            elif tabIndex == 1:
                obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses - debugging
                connection = obd.OBD(portstr="\\.\\COM3", baudrate=38400, fast=False)
            '''


        # TODO: revise this section
        # creates a menu
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&Actions')
        # adds desired action to the menu item
        fileMenu.addAction(exitAct)

        # Sets a toolbar and ties it to the desired action - not sure how to place images
        # toolbar = self.addToolBar('Exit')
        # toolbar.addAction(exitAct)

        # TODO:
        # MAIN DASHBOARD WIDGET

        # setting labels for the widgets
        speedL = QLabel('Speed (MPH)')
        RPM = QLabel('RPMs')
        eLoad = QLabel('Engine Load (%)')
        tempr = QLabel('Intake Air Temp. (°f)')

        # TODO: Hook up qlcd to the asynch callback function for speed, etc.
        # number display (called lcd)
        '''
        global speedDsp
        global rpmDsp
        global loadDsp
        global tempDsp
        '''
        speedDsp = QLCDNumber(self)
        rpmDsp = QLCDNumber(self)
        loadDsp = QLCDNumber(self)
        tempDsp = QLCDNumber(self)
        # speedDsp.display(speedDspNum)

        # using a grid layout to manage the layout of the page
        grid = QGridLayout()
        grid.setSpacing(10)

        # think of the window as a board, first 2 numbers are placement next 2 are span of widget
        grid.addWidget(speedL, 1, 0)
        grid.addWidget(speedDsp, 1, 1, 2, 1)

        grid.addWidget(RPM, 3, 0)
        grid.addWidget(rpmDsp, 3, 1, 2, 1)

        grid.addWidget(eLoad, 5, 0)
        grid.addWidget(loadDsp, 5, 1, 2, 1)

        grid.addWidget(tempr, 7, 0)
        grid.addWidget(tempDsp, 7, 1, 2, 1)

        # TODO:
        # ENGINE CODES WIDGET
        # Layout
        codesLayout = QGridLayout()
        codesLayout.setSpacing(10)

        #  Check CEL status/# of codes (buttons)
        checkCodes = QPushButton('Check For Trouble Codes')     # display in window
        readCodes = QPushButton('Read Codes')       # open new window with info
        freezeFrame = QPushButton('Get Freeze Frame Data')      # open new window with info
        clearCodes = QPushButton('Clear Any Existing Codes')  # reset num and make button unclickable -display message?

        # Button control for professional style
        readCodes.setEnabled(False)
        freezeFrame.setEnabled(False)
        clearCodes.setEnabled(False)

        # Display for # of codes - Currently displays zero before button press
        numCodesLbl = QLabel('Number of Trouble Codes')
        codesDsp = QLCDNumber(self)

        # Connect the button to a function on button click
        checkCodes.clicked.connect(checkTheCodes)
        readCodes.clicked.connect(readTheCodes)
        freezeFrame.clicked.connect(runFreezeFrame)
        clearCodes.clicked.connect(clearTheCodes)

        codesLayout.addWidget(checkCodes, 1, 1, 2, 1)
        # layout for title/number display
        codesLayout.addWidget(numCodesLbl, 3, 0)
        codesLayout.addWidget(codesDsp, 3, 1, 1, 1)

        codesLayout.addWidget(readCodes, 4, 1, 2, 1)
        codesLayout.addWidget(freezeFrame, 5, 1, 2, 1)
        codesLayout.addWidget(clearCodes, 6, 1, 2, 1)

        # TODO:
        # TRIP LOGGER WIDGET
        # Layout
        graphsLayout = QGridLayout()
        graphsLayout.setSpacing(10)

        # Create graph widgets
        speedGraph = pg.PlotWidget()
        rpmGraph = pg.PlotWidget()
        engineGraph = pg.PlotWidget()

        # button for starting/stopping trip
        startTrip = QPushButton('Start Your Trip')  # display in window
        stopTrip = QPushButton('Stop Your Trip')  # display in window
        startTrip.clicked.connect(startTripLog)
        stopTrip.clicked.connect(endTrip)
        stopTrip.setEnabled(False)

        # Create points for the graph widget to plot
        hour = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        temperature = [30, 32, 34, 32, 33, 31, 29, 32, 35, 45]
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

        # TODO:
        # PAST TRIPS WIDGET
        # Layout
        tripsLayout = QGridLayout()
        tripsLayout.setSpacing(10)

        # The following code was taken from:
        # https://stackoverflow.com/questions/50211133/open-a-pdf-by-clicking-on-qlabel-made-as-hyperlink
        tripLogTxt = QLabel()
        path = r"tLog.txt"  # r before "" treats the string as a raw string, no '\n' etc
        url = bytearray(QUrl.fromLocalFile(path).toEncoded()).decode()
        text = "<a href={}>Past Trips Log </a>".format(url)
        tripLogTxt.setText(text)
        tripLogTxt.setOpenExternalLinks(True)
        tripLogTxt.show()
        tripsLayout.setAlignment(Qt.AlignCenter)
        tripsLayout.addWidget(tripLogTxt, 2, 2)


        # TODO:
        # EMISSIONS WIDGET
        # Layout
        emissionsLayout = QGridLayout()
        emissionsLayout.setSpacing(10)

        # TODO: Tab Layout
        # Tabs can be added to a QTabWidget. The QTabWidget can be added to a layout and the layout to the window.
        tabsLayout = QGridLayout()
        tabsLayout.setSpacing(10)
        # Creates a widget to hold tabs
        tabWidget = QTabWidget()

        # You can add anything from a button or label to a full widget when adding a tab
        dash = QWidget()
        dash.setLayout(grid)
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

        eTest = QWidget()
        eTest.setLayout(emissionsLayout)
        tabWidget.addTab(eTest, "Emissions Test")

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
        # style for buttons
        clearCodes.setStyleSheet("QPushButton { background-color: red }" "QPushButton:pressed { background-color: "
                                 "green }")
        startTrip.setStyleSheet("background-color: green")
        stopTrip.setStyleSheet("background-color: red")

        self.setGeometry(700, 250, 500, 400)
        self.setWindowTitle('Vehicle Companion')
        self.show()
        setConnection(0)  # Handles the initial asynch connection

        # Function connected to the check codes button press


if __name__ == '__main__':
    # Start gui in asynch mode so we can update live displays
    '''
    obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses for debugging purposes
    connection = obd.Async(portstr="\\.\\COM3", fast=False)

    def new_spd(s):
        speedDsp.display(int(s.value.magnitude))


    def new_rotations(r):
        rpmDsp.display(int(r.value.magnitude))


    def new_engineLd(ld):
        loadDsp.display(int(ld.value.magnitude))


    def new_intakeT(t):
        tempDsp.display(int(t.value.magnitude))

    connection.watch(obd.commands.SPEED, callback=new_spd)
    connection.watch(obd.commands.RPM, callback=new_rotations)
    connection.watch(obd.commands.ENGINE_LOAD, callback=new_engineLd)
    connection.watch(obd.commands.INTAKE_TEMP, callback=new_intakeT)    
    '''
    '''
    obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses - debugging
    connection = obd.OBD(portstr="\\.\\COM3", baudrate=38400, fast=False)
    '''

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Calls the application class we created
    ex = Example()

    # Start asynch query of all watched commands
    # connection.start()
    
    # Enters the gui application into its main loop
    sys.exit(app.exec_())