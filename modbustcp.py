#!/usr/bin/env python3

""" Read 10 coils and print result on stdout. """

import time
from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import encode_ieee, decode_ieee, \
                              long_list_to_word, word_list_to_long

# init modbus client

client = ModbusClient(host='10.68.42.3', port=502)
print(client.open())
# open the socket for 2 reads then close it.
if client.open():
    regs_list_1 = client.read_holding_registers(0,1)
    regs_list_2 = client.read_input_registers(30,1)
    ramp = client.write_single_register(35, 25*10)
    # time.sleep(3)
    regs_list_3 = client.read_holding_registers(35)
    regs_list_4 = client.read_holding_registers(363, 1)

    #client.write_single_register(35, 20)
    client.close()
print(regs_list_1)
print(regs_list_2)
print(regs_list_3)
print(regs_list_4)
