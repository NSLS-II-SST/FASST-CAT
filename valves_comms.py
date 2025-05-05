import serial
import time

# Global variable to hold the serial object
ser1 = None

def serial_connection_valves():
    global ser1
    COMPORT = 'COM6'
    # Initialize ser1 as a serial connection
    ser1 = serial.Serial()
    ser1.baudrate = 9600
    ser1.port = COMPORT  # Counter for port name starts at 0
    parity = serial.PARITY_NONE
    stopbits = serial.STOPBITS_ONE
    bytesize = serial.EIGHTBITS

    if not ser1.isOpen():
        ser1.timeout = 0.05
        ser1.open()
    else:
        print(f'The Port is closed: {ser1.portstr}')

def get_valve_position(valve):
    # Make sure to call serial_connection_valves() before interacting with the serial port
    serial_connection_valves()

    ser1.write('/{}CP\r'.format(valve).encode())
    current_position = ser1.readline().decode('utf-8').strip()
    
    valve_no = current_position[1]
    position = current_position[-2]
    if position == 'A':
        return valve_no, 'OFF'
    elif position == 'B':
        return valve_no, 'ON'
    else:
        return valve_no, 'Unknown'

# Other functions (e.g., alternate_current_position, move_valve_to_position, etc.) remain the same
