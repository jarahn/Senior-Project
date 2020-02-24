import obd
import time

# obd/elm327.py WAS UPDATED (BY ME) TO INCLUDE A 1 SECOND DELAY FOR ALL AT COMMANDS - after that
# python obd began connecting and responding to commands

# Code taken from https://python-obd.readthedocs.io/en/latest/Async%20Connections/

# fast=False guarantees the unaltered output of the command from the vehicle

obd.logger.setLevel(obd.logging.DEBUG)  # prints the PID commands and their responses for debugging purposes
connection = obd.Async(portstr="\\.\\COM3", fast=False)
'''
cmd = obd.commands.SPEED  # select an OBD command (sensor)
cmd2 = obd.commands.RPM
response2 = connection.query(cmd2)
print(response2.value)

response = connection.query(cmd)  # send the command, and parse the response
print(response.value)  # returns unit-bearing values thanks to Pint

print(response.value.to("mph"))  # user-friendly unit conversions
# the status command returns information about the CEL
cmd3 = obd.commands.STATUS     # obd_conn refers to the bluetooth connection that has been established
response3 = connection.query(cmd3)
# if not response.is_null():
if response3.value.DTC_count == 0:
    print("No Codes!")
else:
    print("You have " + str(response3.value.DTC_count) + " engine codes.")
# else:
    # print("Unable to retrieve trouble code information.")
'''


# A callback that prints every new rpm value to the console
def new_rpm(r):
    print(r.value)


# Give the asynch connection a command to watch and a callback function to execute when the value changes
connection.watch(obd.commands.RPM, callback=new_rpm)
# Start asynch query of all watched commands
connection.start()
# the callback will now be fired upon receipt of new values

# Let the asynch mode run for 60
time.sleep(60)
# Stop the asynch query (ALWAYS INCLUDE!!)
connection.stop()

# Class to manage accessing PCM(ECU) trouble codes
''' class EcuCodes:

    # Constructor - automatically creates get and set methods using objName.varName
    def __init__(self, obd_conn):
        self.obd_conn = obd_conn

    def check_codes(self):
        # validate bluetooth connection
        valid_connection = False

        if valid_connection:
            # check if the CEL is on
            # response = self.obd_conn.commands.status

            # if not response.is_null():
                # if response.value.MIL == 0:
                    print("No Codes!")
                # else:
                    # print("You have " + response.value.DTC_count + "engine codes.")
                    # codes = self.obd_conn.commands.GET_DTC
                    # Extract info out of the response tuple
            # else:
                # print("Unable to retrieve trouble code information.")
'''
