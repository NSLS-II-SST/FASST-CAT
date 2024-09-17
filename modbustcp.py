#!/usr/bin/env python3

""" Read 10 coils and print result on stdout. """

import time
from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import encode_ieee, decode_ieee, \
                              long_list_to_word, word_list_to_long

# init modbus client

modbustcp = ModbusClient(host='10.68.42.3', port=502)
# print(client.open())
# open the socket for 2 reads then close it.
def pid_clausen_coiled():
    modbustcp.open()
    regs_list_1 = modbustcp.read_holding_registers(6,4)
    print(regs_list_1)
    modbustcp.write_multiple_registers(6,[9876,0,96,16])
    regs_list_2 = modbustcp.read_holding_registers(6,4)
    print(regs_list_2)
    modbustcp.close()

def get_temp_wsp():
    """Return the process value (PV) for loop1."""
    modbustcp.open()
    regs_list_1 = format(modbustcp.read_holding_registers(2)[0]*0.1, ".1f")
    print(regs_list_1)
    print(f"WSP Temp = {regs_list_1} degC")
    modbustcp.close()

def get_temp_tc():
    """Return the process value (PV) for loop1."""
    modbustcp.open()
    regs_list_1 = format(modbustcp.read_holding_registers(1)[0]*0.1, ".1f")
    print(regs_list_1)
    print(f"TC Temp = {regs_list_1} degC")
    modbustcp.close()

def get_temp_prog():
    """Return the process value (PV) for loop1."""
    modbustcp.open()
    regs_list_1 = format(modbustcp.read_holding_registers(5)[0]*0.1, ".1f")
    print(regs_list_1)
    print(f"Prog Temp = {regs_list_1} degC")
    modbustcp.close()

def get_pw_prog():
    """Return the process value (PV) for loop1."""
    modbustcp.open()
    regs_list_1 = format(modbustcp.read_holding_registers(85)[0]*0.1, ".1f")
    print(regs_list_1)
    print(f"Prog Power = {regs_list_1}%")
    modbustcp.close()

def get_heating_rate():
    """Return the process value (PV) for loop1."""
    modbustcp.open()
    regs_list_1 = format(modbustcp.read_holding_registers(35)[0]*0.1, ".1f")
    print(regs_list_1)
    print(f"Heating rate = {regs_list_1} degC/min")
    modbustcp.close()

def write_wsp(sp):
    """Return the process value (PV) for loop1."""
    modbustcp.open()
    sp = float(sp)*10
    modbustcp.write_single_register(2, sp)
    get_temp_wsp()

def write_heating_rate(rate):
    """Return the process value (PV) for loop1."""
    modbustcp.open()
    rate = float(rate)*10
    modbustcp.write_single_register(35, rate)
    get_heating_rate()
    modbustcp.close()

def heating_event(rate_sp = None, sp = None):
    """Loops over actual temperature in an heating event until setpoint is reached"""
    modbustcp.open()
    print('Starting heating event:')
    try:
        print('Heating rate: {} C/min'.format(rate_sp))
        rate_sp = float(rate_sp*10)
        modbustcp.write_single_register(35, rate_sp)
    except:
        rate_sp = None      
    try:
        print('Setpoint: {} C'.format(sp))
        sp = float(sp*10)
        modbustcp.write_single_register(2, sp)
    except:
        sp = None      
    while True:
        try:
            temp_tc = get_temp_tc()
            temp_programmer = get_temp_prog()
            power_out = get_pw_prog()
        except IOError:
            continue
            # print("Failed to read from instrument")
        except ValueError:
            continue
            # print("Instrument response is invalid")
        try:
            result = float(temp_tc) < float(sp)
            if result == True:
                temp_tc = float(temp_tc)
                # self.pressure_report()
                print("-----------------------------------------------------------------------------------------------------\n",
                f"Setpoint Temp: {sp} C | Programmer Temp: {temp_programmer} C | Reactor Temp: {temp_tc} C | Power out: {power_out}%\n",
                "-----------------------------------------------------------------------------------------------------")
                print("\033[F\033[F\033[F\033[F", end="")
                time.sleep(1)
            else:
                print('{} C setpoint reached!'.format(sp))
                break
        except TypeError:
            continue
    modbustcp.close()

pid_clausen_coiled()
get_temp_wsp()
get_temp_tc()
get_temp_prog()
get_pw_prog()
