#!/usr/bin/env python3


import time
from datetime import datetime
from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import encode_ieee, decode_ieee, \
                              long_list_to_word, word_list_to_long


HOST = "10.68.42.3"
PORT = 502

class EuroTCP:

    def __init__(
            self,
            host: str = HOST,
            port: int = PORT,
            ) -> None:

        self.host = host
        self.port = port
        self.modbustcp = ModbusClient(host, port)
        pass

    def get_temp_wsp(self):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        regs_list_1 = format(self.modbustcp.read_holding_registers(2)[0]*0.1, ".1f")
        print(regs_list_1)
        print(f"WSP Temp = {regs_list_1} degC")
        self.modbustcp.close()

    def get_temp_tc(self):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        regs_list_1 = format(self.modbustcp.read_holding_registers(1)[0]*0.1, ".1f")
        print(regs_list_1)
        print(f"TC Temp = {regs_list_1} degC")
        self.modbustcp.close()

    def get_temp_prog(self):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        regs_list_1 = format(self.modbustcp.read_holding_registers(5)[0]*0.1, ".1f")
        print(regs_list_1)
        print(f"Prog Temp = {regs_list_1} degC")
        self.modbustcp.close()

    def get_pw_prog(self):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        regs_list_1 = format(self.modbustcp.read_holding_registers(85)[0]*0.1, ".1f")
        print(regs_list_1)
        print(f"Prog Power = {regs_list_1}%")
        self.modbustcp.close()

    def get_heating_rate(self):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        regs_list_1 = format(self.modbustcp.read_holding_registers(35)[0]*0.1, ".1f")
        print(regs_list_1)
        print(f"Heating rate = {regs_list_1} degC/min")
        self.modbustcp.close()

    def write_wsp(self, sp):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        sp = int(sp)*10
        self.modbustcp.write_single_register(2, sp)
        self.get_temp_wsp()
        self.modbustcp.close()

    def write_heating_rate(self, rate):
        """Return the process value (PV) for loop1."""
        self.modbustcp.open()
        rate = int(rate)*10
        self.modbustcp.write_single_register(35, rate)
        self.get_heating_rate()
        self.modbustcp.close()

    def heating_event(self, rate_sp = None, sp = None):
        """Loops over actual temperature in an heating event until setpoint is reached"""
        self.modbustcp.open()
        print('Starting heating event:')
        try:
            print('Heating rate: {} C/min'.format(rate_sp))
            rate_sp = int(rate_sp*10)
            self.modbustcp.write_single_register(35, rate_sp)
        except:
            rate_sp = None      
        try:
            print('Setpoint: {} C'.format(sp))
            sp = int(sp*10)
            self.modbustcp.write_single_register(2, sp)
        except:
            sp = None      
        while True:
            try:
                temp_tc = format(self.modbustcp.read_holding_registers(1)[0]*0.1, ".1f")
                temp_programmer = format(self.modbustcp.read_holding_registers(5)[0]*0.1, ".1f")
                power_out = format(self.modbustcp.read_holding_registers(85)[0]*0.1, ".1f")
                sp = format(self.modbustcp.read_holding_registers(2)[0]*0.1, ".1f")
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
                    print("\033[F\033[F\033[F", end="")
                    time.sleep(1)
                else:
                    print('{} C setpoint reached!'.format(sp))
                    break
            except TypeError:
                continue
        self.modbustcp.close()

    def cooling_event(self, rate_sp = None, sp = None):
        """Loops over actual temperature in an heating event until setpoint is reached"""
        self.modbustcp.open()
        print('Starting cooling event:')
        try:
            print('Heating rate: {} C/min'.format(rate_sp))
            rate_sp = int(rate_sp*10)
            self.modbustcp.write_single_register(35, rate_sp)
        except:
            rate_sp = None      
        try:
            print('Setpoint: {} C'.format(sp))
            sp = int(sp*10)
            self.modbustcp.write_single_register(2, sp)
        except:
            sp = None      
        while True:
            try:
                temp_tc = format(self.modbustcp.read_holding_registers(1)[0]*0.1, ".1f")
                temp_programmer = format(self.modbustcp.read_holding_registers(5)[0]*0.1, ".1f")
                power_out = format(self.modbustcp.read_holding_registers(85)[0]*0.1, ".1f")
                sp = format(self.modbustcp.read_holding_registers(2)[0]*0.1, ".1f")
            except IOError:
                continue
                # print("Failed to read from instrument")
            except ValueError:
                continue
                # print("Instrument response is invalid")
            try:
                result = float(temp_tc) > float(sp)
                if result == True:
                    temp_tc = float(temp_tc)
                    # self.pressure_report()
                    print("-----------------------------------------------------------------------------------------------------\n",
                    f"Setpoint Temp: {sp} C | Programmer Temp: {temp_programmer} C | Reactor Temp: {temp_tc} C | Power out: {power_out}%\n",
                    "-----------------------------------------------------------------------------------------------------")
                    print("\033[F\033[F\033[F", end="")
                    time.sleep(1)
                else:
                    print('{} C setpoint reached!'.format(sp))
                    break
            except TypeError:
                continue
        self.modbustcp.close()

    def temperature_ramping_event(self, rate_sp = None, sp = None ):
        while True:
            try:
                temp_tc = format(self.modbustcp.read_holding_registers(1)[0]*0.1, ".1f")
            except IOError:
                continue
                # print("Failed to read from instrument")
            except ValueError:
                continue
                # print("Instrument response is invalid")
            try:
                result = float(temp_tc) > float(sp)
                if result == True:
                    self.cooling_event(rate_sp, sp)
                    print('Starting cooling event')
                    break
                else:
                    self.heating_event(rate_sp, sp)
                    print('Starting heating event')
                    break
            except TypeError:
                continue

    def setpoint_finish_experiment(self):
        """Loops over actual temperature in an cooling event until setpoint is reached"""
        rate_sp=10
        sp=18
    
        print('adjust temperature set point to 18C:')
        try:
            print(f"Cooling rate: {rate_sp} C/min")
            rate_sp = int(rate_sp*10)
            self.modbustcp.write_single_register(35, rate_sp)
        except:
            rate_sp = None
    
        try:
            print(f"Setpoint: {sp} C")
            sp = int(sp*10)
            self.modbustcp.write_single_register(2, sp)
        except:
            sp = None

    def time_event(self, time_in_seconds: int, argument: str):
        """Waits for a specified time while printing the elapsed time on the terminal.

        Args:
            time_in_seconds (int): The time to wait in seconds.
        """
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time < time_in_seconds:
                temp_tc = format(self.modbustcp.read_holding_registers(1)[0]*0.1, ".1f")
                # self.pressure_report()            
                print("-----------------------------------------------------------------------------------------------------\n",
                f"Elapsed time for {str(argument)}: {int(elapsed_time)} seconds at {temp_tc} degC\n",
                "-----------------------------------------------------------------------------------------------------")
                print("\033[F\033[F\033[F", end="")
                time.sleep(1)
            else:
                print("-----------------------------------------------------------------------------------------------------\n",
                f"Wait time of {time_in_seconds} seconds at {temp_tc} degC completed.",
                "-------------------------------------------------------------------\n",
                "-----------------------------------------------------------------------------------------------------", end="\r")
                break

    def drift_mantis_pid(self):
        self.modbustcp.open()
        self.modbustcp.write_multiple_registers(6,[869,0,96,16])
        regs_list_2 = self.modbustcp.read_holding_registers(6,4)
        p = regs_list_2[0]*0.1
        i = regs_list_2[2]
        d = regs_list_2[3]
        print(f"PID for Harrick Mantis DRIFTS cell is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to LOCAL")
        self.modbustcp.close()

    def clausen_coil_local_pid(self):    
        self.modbustcp.open()
        self.modbustcp.write_multiple_registers(6,[9876,0,96,16])
        regs_list_2 = self.modbustcp.read_holding_registers(6,4)
        p = regs_list_2[0]*0.1
        i = regs_list_2[2]
        d = regs_list_2[3]
        print(f"PID for clausen cell with coil heating elements and REMOTE power supply is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to LOCAL")
        self.modbustcp.close()
        
    def clausen_coil_remote_pid(self):
        self.modbustcp.open()
        self.modbustcp.write_multiple_registers(6,[6000,0,20,4])
        regs_list_2 = self.modbustcp.read_holding_registers(6,4)
        p = regs_list_2[0]*0.1
        i = regs_list_2[2]
        d = regs_list_2[3]
        print(f"PID for clausen cell with coil heating elements and REMOTE power supply is:\nProportional band = {p}\nIntegral time = {i}\nDerivative time = {d}\nPlease switch power output to REMOTE")
        self.modbustcp.close()
  
    def MS_ON(self):
        """Sends a logic value (0 or 1) to perform remote MS digital triggering to RlyAA"""
        self.modbustcp.write_single_register(363,0)
        time.sleep(1)
        print('MS recipe started')
    
    def MS_OFF(self):
        """Sends a logic value (0 or 1) to perform remote MS digital triggering to RlyAA"""
        self.modbustcp.write_single_register(363,1)
        time.sleep(1)
        print('MS recipe stopped')
    
    def IR_ON(self):
        """Sends 5V pulse to perform remote IR triggering to logic A"""    
        self.modbustcp.write_single_register(376,5)
        # value_high = self.modbustcp.read_holding_registers(376)[0]
        time.sleep(1)
        # print(value_high)
        self.modbustcp.write_single_register(376,0)
        # value_low = self.modbustcp.read_holding_registers(376)[0]
        # print(value_low)
        print('IR data acquisition started')
        now = datetime.now()
        dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
        print('\ndate and time =', dt_start)
    
    def pulse_ON(self):
        """Sends 3V to perform remote triggering to logic A"""    
        self.modbustcp.write_single_register(376,3)
        #sleep(1)
        #self.write_register(376, 0)
        print('Pulse ON')
        now = datetime.now()
        dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
        print('\ndate and time =', dt_start)
    
    def pulse_OFF(self):
        """Sends 0V to perform remote triggering to logic A"""    
        self.modbustcp.write_single_register(376,0)
        #sleep(1)
        #self.write_register(376, 0)
        print('Pulse OFF')
        now = datetime.now()
        dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
        print('\ndate and time =', dt_start)
    
    def IR_STATUS(self):
        """Sends 5V to perform remote triggering to logic A"""    
        while True:
            try:
                result = self.modbustcp.read_holding_registers(361)[0]
                # print(result)
            except IOError:
                continue
                # print("Failed to read from instrument")
            except ValueError:
                continue
                # print("Instrument response is invalid")
            if result == 1:
                break
            elif result == 0:
                time.sleep(0.1)
                continue

if __name__ == "__main__":

    eurotcp = EuroTCP()
    
    eurotcp.pid_clausen_coiled()
    eurotcp.get_temp_wsp()
    eurotcp.get_temp_tc()
    eurotcp.get_temp_prog()
    eurotcp.get_pw_prog()
    eurotcp.get_heating_rate()
