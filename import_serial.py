import serial
import time

ser1 = 0        
def serial_connection_valves():

  COMPORT = 'COM4'
  global ser1
  ser1 = serial.Serial()
  ser1.baudrate = 9600
  ser1.port = COMPORT #counter for port name starts at 0
  parity=serial.PARITY_NONE
  stopbits=serial.STOPBITS_ONE
  bytesize=serial.EIGHTBITS
  
  if (ser1.isOpen() == False):
    ser1.timeout = 0.05
    ser1.open()

  else:
    print ('The Port is closed: ' + ser1.portstr)

#Function that displays available commands list
def commands_list():
  serial_connection_valves()
  commands = ser1.write(b'/C?\r')
  
  # Define a buffer to store the data
  buffer = []

  # Read data from the serial port until you receive a complete set of lines
  while True:
    data = ser1.readline().decode().strip()  # Read a line of data and decode it
    if not data:  # If no data is received, break the loop
      break
    buffer.append(data)  # Add the received line to the buffer  
  
  # Split each item at '\r' character to create separate lines
  lines = [item.split('\r') for item in buffer]
  # print(lines)

  # Flatten the list of lines into a single list
  lines = [line for sublist in lines for line in sublist]
  # print(lines)

  # Combine the lines with newline character '\n'
  output = '\n'.join(lines)

  # Print the output
  print(output)
  
  
def valve_current_position(self):
  serial_connection_valves()
  value = str(self)
  ser1.write(bytes("/{}CP\r".format(value), encoding="ascii"))
  current_position_A = ser1.readline().decode('utf-8').strip()
  print(current_position_A)
  valve_no_A = current_position_A[1]
  position_A = current_position_A[-2]
  if position_A == 'A':
    position_is_A = 'OFF'
  elif position_A == 'B':
    position_is_A = 'ON'
  else:
    position_is_A = 'Unknown'
  print('Valve "{}" position is {}'.format(valve_no_A, position_is_A))

def alternate_current_position(self):
  serial_connection_valves()
  value = str(self)
  ser1.write(bytes("/{}CP\r".format(value), encoding="ascii"))
  current_position_A = ser1.readline().decode('utf-8').strip()
  # print(current_position_A)
  valve_no_A = current_position_A[1]
  position_A = current_position_A[-2]
  if position_A == 'A':
    position_is_A = 'OFF'
  elif position_A == 'B':
    position_is_A = 'ON'
  else:
    position_is_A = 'Unknown'
  print('Valve "{}" position is {}'.format(valve_no_A, position_is_A))
  ser1.write(bytes("/{}TO\r".format(value), encoding="ascii"))
  time.sleep(0.3)
  ser1.write(bytes("/{}CP\r".format(value), encoding="ascii"))
  current_position_B = ser1.readline().decode('utf-8').strip()
  # print(current_position_B)
  valve_no_B = current_position_B[1]
  position_B = current_position_B[-2]
  if position_B == 'A':
    position_is_B = 'OFF'
  elif position_B == 'B':
    position_is_B = 'ON'
  else:
    position_is_B = 'Unknown'
  print('Valve "{}" position is {}'.format(valve_no_B, position_is_B))
  if position_is_B == position_is_A:
    ser1.write(bytes("/{}TO\r".format(value), encoding="ascii"))
  else:
    print('Valve in position')
  
  
# valve_current_position("B")
# alternate_current_position("I")
# valves_current_positions()
    
# Function to get valve position
def get_valve_position(valve):
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
    
def id_change(valve):
    valve = str(valve)
    ser1.write('/ID{}\r'.format(valve).encode())
    current_position = ser1.readline().decode('utf-8').strip()
    print(current_position)

# Function to move valve to a specific position
def move_valve_to_position(valve, position):
    serial_connection_valves()
    if position == 'ON':
        position_real = 'B'
        command = 'CC'
    elif position == 'OFF':
        position_real = 'A'
        command = 'CW'
    else:
        print('Invalid position specified.')
        return    
    
    ser1.write('/{}{}\r'.format(valve, command).encode())
    time.sleep(0.3)
    ser1.write('/{}CP\r'.format(valve).encode())
    new_position = ser1.readline().decode('utf-8').strip()[-2]
    if new_position != position_real:
        ser1.write('/{}{}\r'.format(valve, command).encode())
    else:
        print('Valve "{}" successfully moved to position {}'.format(valve, new_position))

# Function to display valve positions
def display_valve_positions(valve=None):
    if valve is not None:
        valve_no, position = get_valve_position(valve)
        print('Valve "{}" position is {}'.format(valve_no, position))
    else:
        valves = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
        positions = [get_valve_position(valve) for valve in valves]
        for valve_no, position in positions:
            print('Valve "{}" position is {}'.format(valve_no, position))

valve_current_position("F")

