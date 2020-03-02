# I used http://zetcode.com/gui/pyqt5 as a reference and guide for writing this program
import sys
from PyQt5.QtWidgets import *
# need these and maybe a few more (QWidget, QLabel, QLineEdit, QLCDNumber,
#                              QTextEdit, QGridLayout, QMainWindow, QAction, qApp, QApplication)
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon
import pyqtgraph as pg
import obd
import time

# Setting these as global variables for access from callback function
speedDsp = None
rpmDsp = None
loadDsp = None
tempDsp = None
startTime = None
endTime = None

# speed = []
# rpms = []
# engineLoad = []


# Testing github 2/24/20
class Example(QMainWindow):

    def __init__(self):
        super().__init__()
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
            # STOP ASYNCH HERE AND START STANDARD CONNECTION
            global connection
            connection.stop()
            connection.close()
            obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses - debugging purposes
            connection = obd.OBD(portstr="\\.\\COM3", baudrate=38400, fast=False)

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
                    codeData = str(codeRsp.value)
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

                    # decide what other info is relevant and create queries
            else:
                freezeData = "Unable to retrieve trouble code information."

            # Take quotes off of freezeData when ready
            QMessageBox.information(self, 'Freeze Frame Data', freezeData, QMessageBox.Ok, QMessageBox.Ok)

        def clearTheCodes():
            print('The car is fixed!')

            # again - could optimize to only allow button click when checkTheCodes has a nonzero value
            checkForCodes = obd.commands.STATUS
            statusRsp = connection.query(checkForCodes)

            if not statusRsp.is_null():
                if statusRsp.value.DTC_count == 0:
                    clearMsg = "No codes to clear!"
                else:
                    # obd.commands.CLEAR_DTC
                    clearMsg = "All codes cleared!"
            else:
                clearMsg = "Unable to retrieve trouble code information."

            QMessageBox.information(self, 'Clearing Codes', clearMsg, QMessageBox.Ok, QMessageBox.Ok)

        def startTripLog(self):
            print("starting trip!")

            # restart asynch connection - SHOULD HAVE A BOOLEAN FOR CHECKING IF ASYNCH OR STANDARD
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

        def endTrip(self):
            print("ending the trip!")

            # Stop Asynch connection
            global connection
            connection.stop()
            connection.close()

            global endTime
            endTime = time.time_ns()
            timeSec = int((endTime - startTime) / 1000000000)
            tripTime = range(0, int(timeSec))
            # tripTime = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
            print(startTime)
            print(endTime)
            print(tripTime)
            print(*speed)
            print(*rpms)
            speedGraph.plot(tripTime, speed)
            rpmGraph.plot(tripTime, rpms)
            engineGraph.plot(tripTime, engineLoad)
            print("plotted!")

            # speedGraph.plot(hour, temperature)

        # TODO: revise this section
        # creates a menu
        menubar = self.menuBar()
        # creates a menu item - whatever that means
        fileMenu = menubar.addMenu('&Actions')
        # menubar.addMenu('&Previous Trips')
        # menubar.addMenu('&Settings')
        # adds desired action to the menu item
        fileMenu.addAction(exitAct)

        # Sets a toolbar and ties it to the desired action - not sure how to place images
        # toolbar = self.addToolBar('Exit')
        # toolbar.addAction(exitAct)

        # TODO:
        # MAIN DASHBOARD WIDGET

        # setting labels for the widgets
        speed = QLabel('Speed')
        RPM = QLabel('RPMs')
        codes = QLabel('Engine Load')
        tempr = QLabel('Temperature')

        # TODO: Hook up qlcd to the asynch callback function for speed, etc.
        # number display (called lcd)
        global speedDsp
        global rpmDsp
        global loadDsp
        global tempDsp
        speedDsp = QLCDNumber(self)
        rpmDsp = QLCDNumber(self)
        loadDsp = QLCDNumber(self)
        tempDsp = QLCDNumber(self)
        # speedDsp.display(speedDspNum)

        # using a grid layout to manage the layout of the page
        grid = QGridLayout()
        grid.setSpacing(10)

        # think of the window as a board, first 2 numbers are placement next 2 are span of widget
        grid.addWidget(speed, 1, 0)
        grid.addWidget(speedDsp, 1, 1, 2, 1)

        grid.addWidget(RPM, 3, 0)
        grid.addWidget(rpmDsp, 3, 1, 2, 1)

        grid.addWidget(codes, 5, 0)
        grid.addWidget(loadDsp, 5, 1, 2, 1)

        grid.addWidget(tempr, 7, 0)
        grid.addWidget(tempDsp, 7, 1, 1, 1)

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

        # style for buttons
        '''
        clearCodes.setStyleSheet("QPushButton { background-color: blue }" "QPushButton:pressed { background-color: "
                                 "red }")
        '''

        # Button control for professional style
        readCodes.setEnabled(False)
        freezeFrame.setEnabled(False)
        clearCodes.setEnabled(False)

        # Display for # of codes - Currently displays zero before button press consider changing
        numCodesLbl = QLabel('Number of Trouble Codes')
        codesDsp = QLCDNumber(self)

        # Connect the button to a function on button click
        # RANDY- why does using self tell python im talking about the function
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

        # Create a graph widget
        speedGraph = pg.PlotWidget()
        rpmGraph = pg.PlotWidget()
        engineGraph = pg.PlotWidget()

        # button for starting/stopping trip (reconnect to asynch connection)
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
        # speedGraph.plot(hour, temperature, pen='g')
        # rpmGraph.plot(hour, temperature, pen='r')
        # engineGraph.plot(hour, temperature, pen='w')
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
        widget1 = QWidget()
        widget1.setLayout(grid)
        tabWidget.addTab(widget1, "Dashboard")

        widget2 = QWidget()
        widget2.setLayout(codesLayout)
        tabWidget.addTab(widget2, "Codes")

        widget3 = QWidget()
        widget3.setLayout(graphsLayout)
        tabWidget.addTab(widget3, "Current Trip")

        widget4 = QWidget()
        widget4.setLayout(tripsLayout)
        tabWidget.addTab(widget4, "Previous Trips")

        widget5 = QWidget()
        widget5.setLayout(emissionsLayout)
        tabWidget.addTab(widget5, "Emissions Test")

        tabsLayout.addWidget(tabWidget, 0, 0)

        # this allows you to place a widget as the central widget - keeping it separate from the main window
        tabsWidg = QWidget()
        tabsWidg.setLayout(tabsLayout)
        self.setCentralWidget(tabsWidg)

        # Main styling for GUI
        # self.setStyleSheet("background-color:#6e6e6e")
        # Can also do like normal CSS ex:
        '''
        QMainWindow{
            background-color:#6e6e6e;
        }
        '''

        self.setGeometry(700, 250, 500, 400)
        self.setWindowTitle('Menu')
        self.show()

        # Function connected to the check codes button press


if __name__ == '__main__':
    # Start gui in asynch mode so we can update live displays

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
    
    app = QApplication(sys.argv)
    # Calls the application class we created
    ex = Example()
    
    # Start asynch query of all watched commands
    connection.start()
    
    # Enters the gui application into its main loop
    sys.exit(app.exec_())