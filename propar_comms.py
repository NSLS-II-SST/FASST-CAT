import propar

# Data types:

# The data types available in the propar module are:

# PP_TYPE_INT8 (unsigned char)
# PP_TYPE_INT16 (unsigned int)
# PP_TYPE_SINT16 (signed int, -32767…32767)
# PP_TYPE_BSINT16 (signed int, -23593…41942)
# PP_TYPE_INT32 (unsigned long)
# PP_TYPE_FLOAT (float)
# PP_TYPE_STRING (string)

# These types are automatically converted to data types in the propar protocol, which only supports four basic data types:

# 1 byte value (char, unsigned char)
# 2 byte value (unsigned int, signed int, custom signed int)
# 4 byte value (float, unsigned long, long)
# n byte value (string, char array)

# Gas ID:

#         gas_ID = {
#             "CO2": 4,
#             "CO": 6,
#             "CH4": 9,
#             "H2": 10,
#             "D2": 10,
#             "O2": 11,
#             "He_mix": 7,
#             "He_pulses": 5,
#             "Ar_pulses": 5,
#             "Ar_mix": 7,
#             "N2_mix": 7,
#             "N2_pulses": 5,
#         }

# Create the master
mfc_master = propar.master('/dev/ttyUSB0', 38400)


# Get nodes on the network
nodes = mfc_master.get_nodes()
# Read the usertag of all nodes
for node in nodes:
  user_tag = mfc_master.read(node['address'], 113, 6, propar.PP_TYPE_STRING)
  print(user_tag)


# Get nodes on the network
nodes = mfc_master.get_nodes()
# Make wink 5 times all instruments LEDs
for node in nodes:
  wink_5 = mfc_master.write(node['address'], 0, 0, propar.PP_TYPE_STRING, 5)
  print(wink_5)


# Prepare a list of parameters for a chained read containing:
# fmeasure, fsetpoint, temperature, valve output for CO2 MFC
params = [{'node': 4, 'proc_nr':  33, 'parm_nr': 0, 'parm_type': propar.PP_TYPE_FLOAT},
          {'node': 4, 'proc_nr':  33, 'parm_nr': 3, 'parm_type': propar.PP_TYPE_FLOAT},
          {'node': 4, 'proc_nr':  33, 'parm_nr': 7, 'parm_type': propar.PP_TYPE_FLOAT},
          {'node': 4, 'proc_nr': 114, 'parm_nr': 1, 'parm_type': propar.PP_TYPE_INT32}]
# Note that this uses the read_parameters function.
values = mfc_master.read_parameters(params)
# Display the values returned by the read_parameters function. A single 'value' includes
# the original fields of the parameters supplied to the request, with the data stored in
# the value['data'] field.
for value in values:
  print(value)


# Serial number from CO2 MFC
serial_no = mfc_master.read(4, 113, 3, propar.PP_TYPE_STRING)
print(serial_no)

# User tag from CO2 MFC
user_tag = mfc_master.read(4, 113, 6, propar.PP_TYPE_STRING)
print(user_tag)

# Response alarm message from CO2 MFC
alarm_info = mfc_master.read(4, 1, 20, propar.PP_TYPE_INT8)
print(alarm_info)

# Alarm mode from CO2 MFC
alarm_mode = mfc_master.read(4, 97, 3, propar.PP_TYPE_INT8)
print(alarm_mode)

# Fieldbus diagnostics from CO2 mfc
fieldbus1_diagnostic = mfc_master.read(4, 125, 20, propar.PP_TYPE_STRING)
print(fieldbus1_diagnostic)

# Fieldbus diagnostics from CO2 mfc
fieldbus2_diagnostic = mfc_master.read(4, 124, 20, propar.PP_TYPE_STRING)
print(fieldbus2_diagnostic)

# Operation hours for CO2 MFC
operation_hours = mfc_master.read(4, 118, 2, propar.PP_TYPE_INT16)
print(operation_hours)

# Calibration data for CO2 MFC
calibration_date = mfc_master.read(4, 113, 9, propar.PP_TYPE_STRING)
print(calibration_date)

# Bronkhorst Identification Number
id_no = mfc_master.read(4, 113, 12, propar.PP_TYPE_INT8)
print(id_no)

# Wink CO2 MFC LED n times and returns TRUE on print
wink_n = mfc_master.write(4, 0, 0, propar.PP_TYPE_STRING, 5)
print(wink_n)
