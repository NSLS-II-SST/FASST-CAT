"""Valve and Mass flow control module

__author__ = "Jorge Moncada Vivas"
__version__ = "1.0"
__email__ = "jmoncadav@bnl.gov"

Notes:
This module is based on the code written by Jorge Moncada Vivas and Ryuichi Shimogawa
"""

import os
import time
import serial
from serial.tools import list_ports

import propar

# The HID for the valve 3. This is should ideally be a specified in a different file.
# HID_VALVE = "USB VID:PID=067B:2303 SER= LOCATION=1-11" #RS232
HID_VALVE = "USB VID:PID=0403:6001 SER=B001U9OCA" #RS485
HID_MFC = "COM0COM\PORT\CNCA1"

# This is a dictionary that maps the valve position to an integer.
VALVE_POSITION = {"A": 0, "B": 1, "Unknown": 1, "pulse": 0, "cont": 1, "mix": 1}


class GasControl:
    def __init__(
        self,
        control_hid: str = HID_VALVE,
        control_comport: str = None,
        num_valves=9,
        mfc_hid: str = HID_MFC,
        mfc_comport: str = None,
    ) -> None:
        """Initialize the valve control device
        You can specify the HID or the comport of the valve control device
        It will print the available comports if no comport is specified

        Args:
            control_hid (str): HID of the valve control device, you can also specify the name or hid of the comport [default: HID_VALVE]
            control_comport (str): Comport of the valve control device [default: None]
            num_valves (int): Number of valves connected to the valve control device [default: 8]
            mfc_hid (str): HID of the mfc device, you can also specify the name or hid of the comport [default: HID_MFC]
            mfc_comport (str): Comport of the mfc device [default: None]
        """

        self.status: list[str] = [None] * num_valves

        self.control_hid: str = control_hid
        self.control_comport: str = control_comport
        self.init_control_comport()
        print("Valve comport: {}".format(self.control_comport))
        self.serial_connection_valves()

        self.mfc_hid: str = mfc_hid
        self.mfc_comport: str = mfc_comport
        self.init_mfc_comport()
        print("MFC comport: {}".format(self.mfc_comport))
        self.mfc_master = propar.master(self.mfc_comport, 38400)

        self.define_flowsms()

    def init_control_comport(self):
        """Initialize the comport of the valve control device
        It will print the available comports if no comport is specified
        """

        if self.control_hid:
            control_port = list_ports.grep(self.control_hid)
            control_port = list(control_port)

            if (len(control_port) == 0) and (self.control_comport is None):
                self.print_available_comports()

                raise ValueError(
                    "No comport found for control_hid: {}".format(self.control_hid)
                )
            elif len(control_port) == 1:
                self.control_comport = control_port[0].device
            else:
                self.print_available_comports()
                raise ValueError(
                    "Multiple comports found for control_hid: {}".format(
                        self.control_hid
                    )
                )

        if self.control_comport is None:
            self.print_available_comports()
            raise ValueError("No comport specified")

    def init_mfc_comport(self):
        """Initialize the comport of the mfc device
        It will print the available comports if no comport is specified
        """

        if self.mfc_hid:
            mfc_port = list_ports.grep(self.mfc_hid)
            mfc_port = list(mfc_port)

            if (len(mfc_port) == 0) and (self.mfc_comport is None):
                self.print_available_comports()

                raise ValueError(
                    "No comport found for mfc_hid: {}".format(self.mfc_hid)
                )
            elif len(mfc_port) == 1:
                self.mfc_comport = mfc_port[0].device
            else:
                self.print_available_comports()
                raise ValueError(
                    "Multiple comports found for mfc_hid: {}".format(self.mfc_hid)
                )

        if self.mfc_comport is None:
            self.print_available_comports()
            raise ValueError("No comport specified")

    def print_available_comports(self):
        """Prints the available comports along with their description and hardware id"""
        comports_available = list_ports.comports()
        print("Available comports:")
        for comport in comports_available:
            print(
                "{}: {} [{}]".format(comport.device, comport.description, comport.hwid)
            )

    def get_status(self, valve: [int, list[int]] = 1):
        """Get the status of the valve
        The status is stored in self.status
        The status can be "A", "B" or "Unknown"

        Args:
            valve (int, list[int]): Valve number or list of valve numbers [default: 1]
        """
        if self.ser is None:
            self.serial_connection_valves()

        if isinstance(valve, list):
            for val in valve:
                if (val < 1) or (val > len(self.status)):
                    pass
                self.ser.write(bytes("{}CP\r".format(val), encoding="ascii"))
                status: str = str(self.ser.read_until(b"\r").decode())
                valve_position: str = status.split("\r")[0].split(" ")[-1].split("'")[0]

                if valve_position == "A":
                    self.status[val - 1] = "A"
                elif valve_position == "B":
                    self.status[val - 1] = "B"
                else:
                    self.status[val - 1] = "Unknown"
                print(f"Valve {val}: {self.status[val-1]}")
        else:
            if (valve < 1) or (valve > len(self.status)):
                pass
            self.ser.write(bytes("{}CP\r".format(valve), encoding="ascii"))
            status: str = str(self.ser.read_until(b"\r").decode())
            valve_position: str = status.split("\r")[0].split(" ")[-1]

            if valve_position == '"A"':
                self.status[valve - 1] = "A"
            elif valve_position == '"B"':
                self.status[valve - 1] = "B"
            else:
                self.status[valve - 1] = "Unknown"
            print(f"Valve {valve}: {self.status[valve-1]}")

    def serial_connection_valves(self):
        """Function that establishes the serial connection with the valve controller
        It will connect to the comport specified in self.control_comport
        """

        self.ser = serial.Serial()
        self.ser.baudrate = 9600
        self.ser.port = self.control_comport
        parity = serial.PARITY_NONE
        stopbits = serial.STOPBITS_ONE
        bytesize = serial.EIGHTBITS

        if self.ser.isOpen() == False:
            self.ser.timeout = 10
            self.ser.open()

        else:
            print("The Port is closed: " + self.ser.portstr)

    def carrier_He_mix(self):
        """Fuction that selects He as carrier gas for the mixing line"""
        self.ser.write(b'/GCW\r')
        current_position_A = self.ser.readline().decode('utf-8').strip()
        # print(current_position_A)
        valve_no_A = current_position_A[1]
        position_A = current_position_A[-2]
        if position_A == 'A':
            position_is_A = 'OFF'
        elif position_A == 'B':
            position_is_A = 'ON'
        else:
            position_is_A = 'Unknown'
        print("Feeding He to mixing line")

    def carrier_Ar_mix(self):
        """Fuction that selects Ar as carrier gas for the mixing line"""
        self.ser.write(b"5CC\r")
        print("Feeding Ar to mixing line")

    def carrier_He_pulses(self):
        """Fuction that selects He as carrier gas for the pulses line"""
        self.ser.write(b"4CC\r")
        print("Feeding He to pulses line")

    def carrier_Ar_pulses(self):
        """Function that selects Ar as carrier gas for the pulses line"""
        self.ser.write(b"4CW\r")
        print("Feeding Ar to pulses line")

    def feed_16O2(self):
        """Fuction that selects 16O2 as oxygen gas source for the mixing line"""
        self.ser.write(b"6CW\r")
        print("Feeding 16O2")

    def feed_18O2(self):
        """Fuction that selects 18O2 as oxygen gas source for the mixing line"""
        self.ser.write(b"6CC\r")
        print("Feeding 18O2")

    def feed_12CO2(self):
        """Fuction that selects 12CO2 as carbon dioxide gas source for the mixing line"""
        self.ser.write(b"9CW\r")
        print("Feeding 12CO2")

    def feed_13CO2(self):
        """Fuction that selects 13CO2 as carbon dioxide gas source for the mixing line"""
        self.ser.write(b"9CC\r")
        print("Feeding 13CO2")

    def feed_H2(self):
        """Function that selects H2 as hydrogen gas source for the mixing line"""
        self.ser.write(b"7CW\r")
        print("Feeding H2")

    def feed_D2(self):
        """Function that selects D2 as deuterium gas source for the mixing line"""
        self.ser.write(b"7CC\r")
        print("Feeding D2")

    def feed_12CH4(self):
        """Fuction that selects 12CH4 as methane gas source for the mixing line"""
        self.ser.write(b"8CW\r")
        print("Feeding 12CH4")

    def feed_13CH4(self):
        """Function that selects 13CH4 as methane gas source for the mixing line"""
        self.ser.write(b"8CC\r")
        print("Feeding 13CH4")

    def feed_CO(self):
        """Fuction that selects CO as carbon monoxide gas source for the mixing line
        This function is not implemented in the valve control module"""
        pass

    def valve1(self, position: str):
        """Function that selects the position of Valve 1 (Reaction mode selection module)

        Args:
            position (str): Position of the valve, can be "off" or "on"
                            "off" means that the valve is in the position mix -> reactor
                            "on" means that the valve is in the position mix -> loop
        """
        if position == "off":
            self.ser.write(b"1CW\r")
            print("Mixing line valve position: off (mix -> reactor)")
        elif position == "on":
            self.ser.write(b"1CC\r")
            print("Mixing line valve position: on (mix -> loop)")

    def valve2(self, position: str):
        """Function that selects the position of Valve 2 (Reaction mode selection module)

        Args:
            position (str): Position of the valve, can be "off" or "on"
                            "off" means that the valve is in the position mix -> reactor
                            "on" means that the valve is in the position mix -> vapor -> reactor
        """

        if position == "off":
            self.ser.write(b"2CW\r")
            print("Water vapor valve position: off (mix -> reactor)")
        elif position == "on":
            self.ser.write(b"2CC\r")
            print("Water vapor valve position: on (mix -> vapor -> reactor)")

    def valve3(self, position: str):
        """Function that selects the position of Valve 3 (Reaction mode selection module)

        Args:
            position (str): Position of the valve, can be "off" or "on"
                            "off" means that the valve is in the position mix -> reactor
                            "on" means that the valve is in the position mix -> vapor -> reactor
        """
        if position == "off":
            self.ser.write(b"3CW\r")
            print(
                "Pulses line valve position: off (mix -> loop 1 -> waste / carrier -> loop 2 -> reactor)"
            )
        elif position == "on":
            self.ser.write(b"3CC\r")
            print(
                "Pulses line valve position: on (mix -> loop 2 -> waste/ carrier -> loop 1 -> reactor)"
            )

    def cont_mode_dry(self, verbose: bool = True):
        """Function that selects the position of the valves in the reaction mode selection
        module to the continuous mode (dry) mode

        mix -> reactor ... pulses line carrier -> loops -> waste

        Args:
            verbose (bool): If True, prints the valve status [default: True]
        """
        self.ser.write(b"1CW\r")
        self.ser.write(b"2CW\r")
        self.ser.write(b"3CW\r")
        if verbose:
            print("Valves operation mode: continuous mode (dry)")
            print("mix -> reactor ... pulses line carrier -> loops -> waste")

    # Fuction that fix the position of the valves in the reaction mode selection
    # module to the continuous mode (wet) mode
    def cont_mode_wet(self, verbose: bool = True):
        """Function that selects the position of the valves in the reaction mode selection
        module to the continuous mode (wet) mode

        mix -> vapor -> reactor ... pulses line carrier -> loops -> waste

        Args:
            verbose (bool): If True, prints the valve status [default: True]
        """
        self.ser.write(b"1CC\r")
        self.ser.write(b"2CW\r")
        self.ser.write(b"3CW\r")
        if verbose:
            print("Valves operation mode: continuous mode (wet)")
            print("mix -> vapor -> reactor ... pulses line carrier -> loops -> waste")

    def modulation(
        self,
        pulses=10,
        time1=10,
        time2=10,
        start_gas="pulse",
        end_gas="pulse",
        monitoring_interval=0.01,
        save_log="./log.txt",
    ):
        """Function that modulates the valves in the reaction mode selection module
        between the pulses mode and the continuous mode (dry) mode

        Args:
            pulses (int): Number of pulses to be performed [default: 10]
            time1 (int): Time in seconds for the valve to be in the pulses mode [default: 10]
            time2 (int): Time in seconds for the valve to be in the continuous mode (dry) mode [default: 10]
            start_gas (str): Gas to be used as carrier gas in the pulses line at the beginning of the modulation [default: "pulse"]
            end_gas (str): Gas to be used as carrier gas in the pulses line at the end of the modulation [default: "pulse"]
            monitoring_interval (float): Time in seconds between each valve status check [default: 0.01]
            save_log (str): Path to the file where the valve status will be saved [default: "log.txt"]
        """
        if save_log is not None:
            os.makedirs(os.path.dirname(save_log), exist_ok=True)

            if not os.path.isfile(save_log):
                with open(save_log, "w") as f:
                    f.write("Time, Valve1\n")

        start_time = time.time()
        end_time = start_time + pulses * (time1 + time2)

        if start_gas == "pulse":
            valve_fun1 = self.pulses_mode
            valve_fun2 = self.cont_mode_dry
        else:
            valve_fun1 = self.cont_mode_dry
            valve_fun2 = self.pulses_mode

        self.get_status()
        if start_gas in VALVE_POSITION.keys():
            start_gas_id = VALVE_POSITION[start_gas]
        else:
            raise ValueError(f"start_gas must be in {VALVE_POSITION.keys()}")

        if end_gas in VALVE_POSITION.keys():
            end_gas_id = VALVE_POSITION[end_gas]
        else:
            raise ValueError(f"end_gas must be in {VALVE_POSITION.keys()}")

        if VALVE_POSITION[start_gas] == 1:
            valve_fun1 = self.pulses_mode
            valve_fun2 = self.cont_mode_dry
        else:
            valve_fun1 = self.cont_mode_dry
            valve_fun2 = self.pulses_mode

        if VALVE_POSITION[end_gas] == 0:
            valve_end_fun = self.pulses_mode
        else:
            valve_end_fun = self.cont_mode_dry

        while True:
            current_time = time.time()
            accumulated_time = current_time - start_time

            current_pulse = int(accumulated_time / (time1 + time2))
            current_time_in_pulse = accumulated_time - current_pulse * (time1 + time2)

            if current_time_in_pulse < time1:
                if VALVE_POSITION[self.status[0]] == start_gas_id:
                    time.sleep(monitoring_interval)
                    continue
                else:
                    self.get_status()
                    if VALVE_POSITION[self.status[0]] == start_gas_id:
                        time.sleep(monitoring_interval)
                        continue
                    else:
                        valve_fun1(verbose=False)
                        if save_log is not None:
                            self.get_status()
                            with open(save_log, "a") as f:
                                f.write(
                                    f"{current_time}, {VALVE_POSITION[self.status[0]]}\n"
                                )
            else:
                if VALVE_POSITION[self.status[0]] != start_gas_id:
                    time.sleep(monitoring_interval)
                    continue
                else:
                    self.get_status()
                    if VALVE_POSITION[self.status[0]] != start_gas_id:
                        time.sleep(monitoring_interval)
                        continue
                    else:
                        valve_fun2(verbose=False)
                        if save_log is not None:
                            self.get_status()
                            with open(save_log, "a") as f:
                                f.write(
                                    f"{current_time}, {VALVE_POSITION[self.status[0]]}\n"
                                )

            time.sleep(monitoring_interval)

            if current_time > end_time:
                break

        valve_end_fun()

    def pulses_mode(self, verbose=True):
        """Function that selects the position of the valves in the reaction mode selection
        module to the pulses mode

        mix -> loop 2 -> reactor ... mix -> loop 1 -> waste

        Args:
            verbose (bool): If True, prints the valve status [default: True]
        """
        self.ser.write(b"1CC\r")
        self.ser.write(b"2CW\r")
        self.ser.write(b"3CW\r")
        if verbose:
            print("Valves operation mode: pulses")
            print("pulses line carrier -> loop 2 -> reactor ... mix -> loop 1 -> waste")

    def define_flowsms(self):
        """Function to define the parameters of the Flow-SMS mass flow controllers
        The parameters are defined in the following dictionaries:

        gas_list: List of the available gases
        gas_dict: Dictionary that assigns a number to each gas
        gas_ID: Dictionary that assigns a node ID to each gas
        gas_cal: Dictionary that assigns a calibration ID to each gas. If there it is applicable to one gas, the value is None.
        gas_flow_range: Dictionary that assigns a flow range to each gas
        calibration_factor: Dictionary that assigns a calibration factor to each gas
        feed_gas_functions: Dictionary that assigns a function to each gas
        gas_float_to_int_factor: Dictionary that assigns a conversion factor from float to int to each gas
        """
        self.gas_list = [
            "H2_A",
            "H2_B",
            "D2_A",
            "D2_B",
            "O2_A",
            "O2_B",
            "CO_AH",
            "CO_AL",
            "CO_BH",
            "CO_BL",
            "CO2_AH",
            "CO2_AL",
            "CO2_BH",
            "CO2_BL",
            "CH4_A",
            "CH4_B",
            "C2H6_A",
            "C2H6_B",
            "C3H8_A",
            "C3H8_B",
            "He_A",
            "He_B",
            "Ar_A",
            "Ar_B",
            "N2_A",
            "N2_B",
        ]

        self.gas_dict = {self.gas_list[i]: i for i in range(len(self.gas_list))}

        self.gas_ID = {
            "H2_A": 4,
            "D2_A":4,
            "O2_A": 5,
            "CO_AH": 6,
            "CO_AL": 6,
            "CO2_AH": 6,
            "CO2_AL": 6,
            "CH4_A": 7,
            "C2H6_A": 7,
            "C3H8_A": 7,
            "He_A": 8,
            "Ar_A": 8,
            "N2_A": 8,
            "He_B": 9,
            "Ar_B": 9,
            "N2_B": 9,
            "CH4_B": 10,
            "C2H6_B": 10,
            "C3H8_B": 10,
            "CO_BH": 11,
            "CO_BL": 11,
            "CO2_BH": 11,
            "CO2_BL": 11,
            "O2_B": 12,
            "H2_B": 13,
            "D2_B":13,
        }

        self.gas_cal = {
            "H2_A": 0,
            "H2_B": 0,
            "D2_A": 1,
            "D2_B": 1,
            "O2_A": None,
            "O2_B": None,
            "CO_AH": 0,
            "CO_BH": 0,
            "CO2_AH": 1,
            "CO2_BH": 1,
            "CO2_AL": 2,
            "CO2_BL": 2,
            "CO_AL": 3,
            "CO_BL": 3,
            "CH4_A": 0,
            "CH4_B": 0,
            "C2H6_A": 1,
            "C2H6_B": 1,
            "C3H8_A": 2,
            "C3H8_B": 2,
            "He_A": 0,
            "He_B": 0,
            "Ar_A": 1,
            "Ar_B": 1,
            "N2_A": 2,
            "N2_B": 2,
        }

        self.gas_flow_range = {
            "CO2_AH": [0.6, 30.0],
            "CO2_AL": [0.26, 13.0],
            "CO2_BH": [0.6, 30.0],
            "CO2_BL": [0.26, 13.0],
            "CO_AH": [0.6, 30.0],
            "CO_AL": [0.36, 18.0],
            "CO_BH": [0.6, 30.0],
            "CO_BL": [0.36, 18.0],
            "CH4_A": [0.6, 30.0],
            "CH4_B": [0.6, 30.0],
            "C2H6_A": [0.6, 30.0],
            "C2H6_B": [0.6, 30.0],
            "C3H8_A": [0.6, 30.0],
            "C3H8_B": [0.6, 30.0],
            "H2_A": [0.6, 30.0],
            "H2_B": [0.6, 30.0],
            "D2_A": [0.6, 30.0],
            "D2_B": [0.6, 30.0],
            "O2_A": [0.6, 30.0],
            "O2_B": [0.6, 30.0],
            "He_A": [1.2, 60.0],
            "He_B": [1.2, 60.0],
            "Ar_A": [1.2, 60.0],
            "Ar_B": [1.2, 60.0],
            "N2_A": [1.2, 60.0],
            "N2_B": [1.2, 60.0],
        }

        self.calibration_factor = {
            "H2_A": 1.0,
            "H2_B": 1.0,
            "D2_A": 1.0,
            "D2_B": 1.0,
            "O2_A": 1.0,
            "O2_B": 1.0,
            "CO_AH": 1.0,
            "CO_AL": 1.0,
            "CO_BH": 1.0,
            "CO_BL": 1.0,
            "CH4_A": 1.0,
            "CH4_B": 1.0,
            "C2H6_A": 1.0,
            "C2H6_B": 1.0,
            "C3H8_A": 1.0,
            "C3H8_B": 1.0,
            "CO2_AH": 1.0,
            "CO2_AL": 1.0,
            "CO2_BH": 1.0,
            "CO2_AL": 1.0,
            "He_A": 1.0,
            "He_B": 1.0,
            "Ar_A": 1.0,
            "Ar_B": 1.0,
            "N2_A": 1.0,
            "N2_B": 1.0,
        }

        self.feed_gas_functions = {
            "H2_A": self.feed_H2,
            "H2_B": self.feed_H2,
            "D2_A": self.feed_D2,
            "D2_B": self.feed_D2,
            "O2_A": self.feed_16O2,
            "O2_B": self.feed_16O2,
            "CO_AH": self.feed_CO,
            "CO_AL": self.feed_CO,
            "CO_BH": self.feed_CO,
            "CO_BL": self.feed_CO,
            "CH4_A": self.feed_12CH4,
            "CH4_B": self.feed_12CH4,
            "C2H6_A": 1.0,
            "C2H6_B": 1.0,
            "C3H8_A": 1.0,
            "C3H8_B": 1.0,
            "CO2_AH": self.feed_12CO2,
            "CO2_AL": self.feed_12CO2,
            "CO2_BH": self.feed_12CO2,
            "CO2_AL": self.feed_12CO2,
            "He_A": self.carrier_He_mix,
            "He_B": self.carrier_He_pulses,
            "Ar_A": self.carrier_Ar_mix,
            "Ar_B": self.carrier_Ar_pulses,
            "N2_A": self.carrier_Ar_mix,
            "N2_B": self.carrier_Ar_pulses,
        }

        self.gas_float_to_int_factor = {
            "H2_A": 30,
            "H2_B": 30,
            "D2_A": 30,
            "D2_B": 30,
            "O2_A": 30,
            "O2_B": 30,
            "CO_AH": 30,
            "CO_AL": 18,
            "CO_BH": 30,
            "CO_BL": 18,
            "CH4_A": 30,
            "CH4_B": 30,
            "C2H6_A": 30,
            "C2H6_B": 30,
            "C3H8_A": 30,
            "C3H8_B": 30,
            "CO2_AH": 30,
            "CO2_AL": 13,
            "CO2_BH": 30,
            "CO2_BL": 13,
            "He_A": 60,
            "He_B": 60,
            "Ar_A": 60,
            "Ar_B": 60,
            "N2_A": 60,
            "N2_B": 60,
        }

    def set_flowrate(
        self,
        gas: str,
        flow: float,
    ):
        """Function that sets the flow rate of a gas in the Flow-SMS mass flow controllers

        Args:
            gas (str): Gas for which the flow rate will be set
            flow (float): Flow rate in sccm
        """
        if gas not in self.gas_list:
            raise ValueError("Gas not in list of available gases")

        while True:
            if (flow is None) or (flow == 0.0):
                flow_conv = 0.0
                break

            flow_conv = flow / self.calibration_factor[gas]

            if flow_conv < self.gas_flow_range[gas][0]:
                print(
                    f"{gas} flow lower than minimum {self.gas_flow_range[gas][0]} sccm"
                )
                interval = input(
                    'Write "Yes" for setting a new flow or "No" for quiting the program: '
                )
                if interval == "Yes":
                    flow = float(input("Enter new flow: "))
                elif interval == "No":
                    raise SystemExit
                else:
                    break

            elif flow_conv > self.gas_flow_range[gas][1]:
                print(
                    f"{gas} flow higher than maximum {self.gas_flow_range[gas][1]} sccm"
                )
                interval = input(
                    'Write "Yes" for setting a new flow or "No" for quiting the program: '
                )
                if interval == "Yes":
                    flow = float(input("Enter new flow: "))
                elif interval == "No":
                    raise SystemExit
                else:
                    break
            else:
                break

        if flow_conv > 0.0:
            self.feed_gas_functions[gas]()

        flow_data = int(flow_conv * 32000 / self.gas_float_to_int_factor[gas])

        param = []

        if self.gas_cal[gas] is not None:
            param.append(
                {
                    "node": self.gas_ID[gas],
                    "proc_nr": 1,
                    "parm_nr": 16,
                    "parm_type": propar.PP_TYPE_INT8,
                    "data": self.gas_cal[gas],
                }
            )

        param.append(
            {
                "node": self.gas_ID[gas],
                "proc_nr": 1,
                "parm_nr": 1,
                "parm_type": propar.PP_TYPE_INT16,
                "data": flow_data,
            }
        )

        status = self.mfc_master.write_parameters(param)

    def flowsms_setpoints(
        self,
        H2_A: None,
        D2_A: None,
        O2_A: None,
        CO_AH: None,
        CO2_AH: None,
        CO_AL: None,
        CO2_AL: None,
        CH4_A: None,
        C2H6_A: None,
        C3H8_A: None,
        He_A: None,
        Ar_A: None,
        N2_A: None,
        He_B: None,
        Ar_B: None,
        N2_B: None,
        CH4_B: None,
        C2H6_B: None,
        C3H8_B: None,
        CO_BH: None,
        CO2_BH: None,
        CO_BL: None,
        CO2_BL: None,
        O2_B: None,
        H2_B: None,
        D2_B: None,
    ):
        """Function that sets the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            H2_A (float): Flow rate of H2 in sccm for gas line A [default: None]
            H2_B (float): Flow rate of H2 in sccm for gas line B [default: None]
            D2_A (float): Flow rate of D2 in sccm for gas line A [default: None]
            D2_B (float): Flow rate of D2 in sccm for gas line B [default: None]
            O2_A (float): Flow rate of O2 in sccm for gas line A [default: None]
            O2_B (float): Flow rate of O2 in sccm for gas line B [default: None]
            CO_AH (float): Flow rate of CO in sccm for gas line A with high flow calibration curve [default: None]
            CO_AL (float): Flow rate of CO in sccm for gas line A with low flow calibration curve [default: None]
            CO_BH (float): Flow rate of CO in sccm for gas line B with high flow calibration curve [default: None]
            CO_BL (float): Flow rate of CO in sccm for gas line B with low flow calibration curve [default: None]
            CO2_AH (float): Flow rate of CO2 in sccm for gas line A with high flow calibration curve [default: None]
            CO2_AL (float): Flow rate of CO2 in sccm for gas line A with low flow calibration curve [default: None]
            CO2_BH (float): Flow rate of CO2 in sccm for gas line B with high flow calibration curve [default: None]
            CO2_BL (float): Flow rate of CO2 in sccm for gas line B with low flow calibration curve [default: None]
            CH4_A (float): Flow rate of CH4 in sccm for gas line A [default: None]
            CH4_B (float): Flow rate of CH4 in sccm for gas line B [default: None]
            C2H6_A (float): Flow rate of C2H6 in sccm for gas line A [default: None]
            C2H46_B (float): Flow rate of C2H6 in sccm for gas line B [default: None]            
            He_A (float): Flow rate of He in sccm for gas line A [default: None]
            He_B (float): Flow rate of He in sccm for gas line B [default: None]
            Ar_A (float): Flow rate of Ar in sccm for gas line A [default: None]
            Ar_B (float): Flow rate of Ar in sccm for gas line B [default: None]
            N2_A (float): Flow rate of N2 in sccm for gas line A [default: None]
            N2_B (float): Flow rate of N2 in sccm for gas line B [default: None]
        """
        if CO_AH is not None and CO_AH > 0.0:
            self.set_flowrate("CO_AH", CO_AH)
        elif CO_AL is not None and CO_AL > 0.0:
            self.set_flowrate("CO_AL", CO_AL)
        elif CO2_AH is not None and CO2_AH > 0.0:
            self.set_flowrate("CO2_AH", CO2_AH)
        else:
            self.set_flowrate("CO2_AL", CO2_AL)

        if CO_BH is not None and CO_BH > 0.0:
            self.set_flowrate("CO_BH", CO_BH)
        elif CO_BL is not None and CO_BL > 0.0:
            self.set_flowrate("CO_BL", CO_BL)
        elif CO2_BH is not None and CO2_BH > 0.0:
            self.set_flowrate("CO2_BH", CO2_BH)
        else:
            self.set_flowrate("CO2_BL", CO2_BL)
        
        if CH4_A is not None and CH4_A > 0.0:
            self.set_flowrate("CH4_A", CH4_A)
        elif C2H6_A is not None and C2H6_A > 0.0:
            self.set_flowrate("C2H6_A", C2H6_A)
        else:
            self.set_flowrate("C3H8_A", C3H8_A)

        if CH4_B is not None and CH4_B > 0.0:
            self.set_flowrate("CH4_B", CH4_B)
        elif C2H6_B is not None and C2H6_B > 0.0:
            self.set_flowrate("C2H6_B", C2H6_B)
        else:
            self.set_flowrate("C3H8_B", C3H8_B)

        if H2_A is not None and H2_A > 0.0:
            self.set_flowrate("H2_A", H2_A)
        else:
            self.set_flowrate("D2_A", D2_A)
        
        if H2_B is not None and H2_B > 0.0:
            self.set_flowrate("H2_B", H2_B)
        else:
            self.set_flowrate("D2_B", D2_B)
        
        if He_A is not None and He_A > 0.0:
            self.set_flowrate("He_A", He_A)
        elif Ar_A is not None and Ar_A > 0.0:
            self.set_flowrate("Ar_A", Ar_A)
        else:
            self.set_flowrate("N2_A", N2_A)

        if He_B is not None and He_B > 0.0:
            self.set_flowrate("He_B", He_B)
        elif Ar_B is not None and Ar_B > 0.0:
            self.set_flowrate("Ar_B", Ar_B)
        else:
            self.set_flowrate("N2_B", N2_B)

        self.set_flowrate("O2_A", O2_A)

        self.set_flowrate("O2_B", O2_B)

    def flowsms_status(self, delay=0.0):
        """Function that reads the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            delay (float): Delay time in seconds before reading the flow rates [default: 0.0]
        """

        # Node ID values assigned in the MFCs configuration

        ID_P_A = 3
        ID_H2_D2_A = 4,
        ID_O2_A = 5,
        ID_CO_CO2_A = 6,
        ID_HC_A = 7,
        ID_CARRIER_A = 8,
        ID_CARRIER_B = 9,
        ID_HC_B = 10,
        ID_CO_CO2_B = 11,
        ID_O2_B = 12,
        ID_H2_D2_B = 13,
        ID_P_B = 14

        # ID assigned in the MFCs configuration for calibration curve allocation
        H2_A = 0
        D2_A = 1
        H2_B = 0
        D2_B = 1
        O2_A = 0
        O2_B = 0
        CO_AH = 0
        CO2_AH = 1
        CO2_AL = 2
        CO_AL = 3
        CO_BH = 0
        CO2_BH = 1
        CO2_BL = 2
        CO_BL = 3
        CH4_A = 0
        C2H6_A = 1
        C3H8_A = 2
        CH4_B = 0
        C2H6_B = 1
        C3H8_B = 2
        CARRIER_He_A = 0
        CARRIER_Ar_A = 1
        CARRIER_N2_A = 2
        CARRIER_He_B = 0
        CARRIER_Ar_B = 1
        CARRIER_N2_B = 2

        # Setting a delay time before reading the actual flows
        # If non present zero delay will be applied before reading

        time.sleep(delay)

        # Parameters to be read from the Flow-SMS mass flow controllers
        
        params_h2_d2_a = [
            {
                "node": ID_H2_D2_A,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_H2_D2_A,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_H2_D2_A,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_h2_d2_b = [
            {
                "node": ID_H2_D2_B,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_H2_D2_B,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_H2_D2_B,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_o2_a = [
            {
                "node": ID_O2_A,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_O2_A,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
        ]
        params_o2_b = [
            {
                "node": ID_O2_B,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_O2_B,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
        ]
        params_hc_a = [
            {
                "node": ID_HC_A,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_HC_A,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_HC_A,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_hc_b = [
            {
                "node": ID_HC_B,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_HC_B,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_HC_B,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_co_co2_a = [
            {
                "node": ID_CO_CO2_A,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CO_CO2_A,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CO_CO2_A,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_co_co2_b = [
            {
                "node": ID_CO_CO2_B,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CO_CO2_B,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CO_CO2_B,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_carrier_a = [
            {
                "node": ID_CARRIER_A,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CARRIER_A,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CARRIER_A,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_carrier_b = [
            {
                "node": ID_CARRIER_B,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CARRIER_A,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CARRIER_B,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_p_a = [
            {
                "node": ID_P_A,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            }
        ]
        params_p_b = [
            {
                "node": ID_P_B,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            }
        ]

        # Sending the specified parameters to the Flow-SMS
        values_h2_d2_a = self.mfc_master.read_parameters(params_h2_d2_a)
        values_h2_d2_b = self.mfc_master.read_parameters(params_h2_d2_b)
        values_o2_a = self.mfc_master.read_parameters(params_o2_a)
        values_o2_b = self.mfc_master.read_parameters(params_o2_b)
        values_co_co2_a = self.mfc_master.read_parameters(params_co_co2_a)
        values_co_co2_b = self.mfc_master.read_parameters(params_co_co2_b)
        values_hc_a = self.mfc_master.read_parameters(params_hc_a)
        values_hc_b = self.mfc_master.read_parameters(params_hc_b)
        values_carrier_a = self.mfc_master.read_parameters(params_carrier_a)
        values_carrier_b = self.mfc_master.read_parameters(params_carrier_b)
        values_p_a = self.mfc_master.read_parameters(params_p_a)
        values_p_b = self.mfc_master.read_parameters(params_p_b)

        # Creating induviduals lists for the read values from each MFC
        lst_h2_d2_a = []
        for value in values_h2_d2_a:
            if "data" in value:
                flow = value.get("data")
            lst_h2_d2_a.append(format(flow, ".2f"))
        fluid_h2_d2_a = float(lst_h2_d2_b[2])
        if fluid_h2_d2_a == 0:
            fluid_h2_d2_a = "H2_A"
        elif fluid_h2_d2_a == 1:
            fluid_h2_d2_a = "D2_A"

        lst_h2_d2_b = []
        for value in values_h2_d2_b:
            if "data" in value:
                flow = value.get("data")
            lst_h2_d2_b.append(format(flow, ".2f"))
        fluid_h2_d2_b = float(lst_h2_d2_b[2])
        if fluid_h2_d2_b == 0:
            fluid_h2_d2_b = "H2_B"
        elif fluid_h2_d2_b == 1:
            fluid_h2_d2_b = "D2_B"

        lst_o2_a = []
        for value in values_o2_a:
            if "data" in value:
                flow = value.get("data")
            lst_o2_a.append(format(flow, ".2f"))

        lst_o2_b = []
        for value in values_o2_b:
            if "data" in value:
                flow = value.get("data")
            lst_o2_b.append(format(flow, ".2f"))   
        
        lst_co_co2_a = []
        for value in values_co_co2_a:
            if "data" in value:
                flow = value.get("data")
            lst_co_co2_a.append(format(flow, ".2f"))
        fluid_co_co2_a = float(lst_co_co2_b[2])
        if fluid_co_co2_a == 0:
            fluid_co_co2_a = "CO_AH"
        elif fluid_co_co2_a == 1:
            fluid_co_co2_a = "CO2_AH"
        elif fluid_co_co2_a == 2:
            fluid_co_co2_a = "CO2_AL"
        elif fluid_co_co2_a == 3:
            fluid_co_co2_a = "CO_AL"

        lst_co_co2_b = []
        for value in values_co_co2_b:
            if "data" in value:
                flow = value.get("data")
            lst_co_co2_b.append(format(flow, ".2f"))
        fluid_co_co2_b = float(lst_co_co2_b[2])
        if fluid_co_co2_b == 0:
            fluid_co_co2_b = "CO_BH"
        elif fluid_co_co2_b == 1:
            fluid_co_co2_b = "CO2_BH"
        elif fluid_co_co2_b == 2:
            fluid_co_co2_b = "CO2_BL"
        elif fluid_co_co2_b == 3:
            fluid_co_co2_b = "CO_BL"

        lst_hc_a = []
        for value in values_hc_a:
            if "data" in value:
                flow = value.get("data")
            lst_hc_a.append(format(flow, ".2f"))
        fluid_hc_a = float(lst_hc_a[2])
        if fluid_hc_a == 0:
            fluid_hc_a = "CH4_A"
        elif fluid_hc_a == 1:
            fluid_hc_a = "C2H6_A"
        elif fluid_hc_a == 2:
            fluid_hc_a = "C3H8_A"

        lst_hc_b = []
        for value in values_hc_b:
            if "data" in value:
                flow = value.get("data")
            lst_hc_b.append(format(flow, ".2f"))
        fluid_hc_b = float(lst_hc_b[2])
        if fluid_hc_b == 0:
            fluid_hc_b = "CH4_B"
        elif fluid_hc_b == 1:
            fluid_hc_b = "C2H6_B"
        elif fluid_hc_b == 2:
            fluid_hc_b = "C3H8_B"

        lst_carrier_a = []
        for value in values_carrier_a:
            if "data" in value:
                flow = value.get("data")
            lst_carrier_a.append(format(flow, ".2f"))
        fluid_carrier_a = float(lst_carrier_a[2])
        if fluid_carrier_a == 0:
            fluid_carrier_a = "He"
        elif fluid_carrier_a == 1:
            fluid_carrier_a = "Ar"
        elif fluid_carrier_a == 2:
            fluid_carrier_a = "N2"

        lst_carrier_b = []
        for value in values_carrier_b:
            if "data" in value:
                flow = value.get("data")
            lst_carrier_b.append(format(flow, ".2f"))
        fluid_carrier_b = float(lst_carrier_b[2])
        if fluid_carrier_b == 0:
            fluid_carrier_b = "He"
        elif fluid_carrier_b == 1:
            fluid_carrier_b = "Ar"
        elif fluid_carrier_b == 2:
            fluid_carrier_b = "N2"

        lst_p_a = []
        for value in values_p_a:
            if "data" in value:
                pressure = value.get("data")
            lst_p_a.append(format(pressure, ".2f"))

        lst_p_b = []
        for value in values_p_b:
            if "data" in value:
                pressure = value.get("data")
            lst_p_b.append(format(pressure, ".2f"))

        # Calculating percentage values for the actual flows

        total_flow_a = float(
            format(
                float(lst_h2_d2_a[0])
                + float(lst_o2_a[0])
                + float(lst_co_co2_a[0])
                + float(lst_hc_a[0])
                + float(lst_carrier_a[0]),
                ".2f",
            )
        )
        if total_flow_a != 0:
            H2_D2_percent_a = format((float(lst_h2_d2_a[0]) / total_flow_a) * 100, ".1f")
            O2_percent_a = format((float(lst_o2_a[0]) / total_flow_a) * 100, ".1f")
            CO_CO2_percent_a = format((float(lst_co_co2_a[0]) / total_flow_a) * 100, ".1f")
            HC_percent_a = format((float(lst_hc_a[0]) / total_flow_a) * 100, ".1f")
            # carrier_a_percent = format((float(lst_carrier_a[0])/total_flow_a)*100, '.1f')

        total_flow_b = float(
            format(
                float(lst_h2_d2_b[0])
                + float(lst_o2_b[0])
                + float(lst_co_co2_b[0])
                + float(lst_hc_b[0])
                + float(lst_carrier_b[0]),
                ".2f",
            )
        )
        if total_flow_b != 0:
            H2_D2_percent_b = format((float(lst_h2_d2_b[0]) / total_flow_b) * 100, ".1f")
            O2_percent_b = format((float(lst_o2_b[0]) / total_flow_b) * 100, ".1f")
            CO_CO2_percent_b = format((float(lst_co_co2_b[0]) / total_flow_b) * 100, ".1f")
            HC_percent_b = format((float(lst_hc_b[0]) / total_flow_b) * 100, ".1f")
            # carrier_b_percent = format((float(lst_carrier_b[0])/total_flow_b)*100, '.1f')

        # Creating and printing table with the actual and set flows, and line pressures
        print(" ")
        print("------------------------------------------------------------")
        print("-------------------")
        print("--- Flow Report ---")
        print("-------------------")

        if float(lst_h2_d2_a[1]) == 0:
            pass
        else:
            print(
                "{}: measured flow is {} sccm. Flow setpoint is {} sccm. Concentration is {}%".format(
                    fluid_h2_d2_a, lst_h2_d2_a[0], lst_h2_d2_a[1], H2_D2_percent_a
                )
            )

        if float(lst_h2_d2_b[1]) == 0:
            pass
        else:
            print(
                "{}: measured flow is {} sccm. Flow setpoint is {} sccm. Concentration is {}%".format(
                    fluid_h2_d2_b, lst_h2_d2_b[0], lst_h2_d2_b[1],H2_D2_percent_b
                )
            )

        if float(lst_o2_a[1]) == 0:
            pass
        else:
            print(
                "O2_A: measured flow is {} sccm. Flow setpoint is {} sccm. Concentration is {}%".format(
                    lst_o2_a[0], lst_o2_a[1], O2_percent_a
                )
            )

        if float(lst_o2_b[1]) == 0:
            pass
        else:
            print(
                "O2_B: measured flow is {} sccm. Flow setpoint is {} sccm. Concentration is {}%".format(
                    lst_o2_b[0], lst_o2_b[1], O2_percent_b
                )
            )

        if float(lst_co_co2_a[1]) == 0:
            pass
        else:
            print(
                "{}: measured flow is {} sccm. Flow setpoint is {} sccm. Concentration is {}%".format(
                    fluid_co_co2_a, lst_co_co2_a[0], lst_co_co2_a[1], CO_CO2_percent_a
                )
            )

        if float(lst_co_co2_b[1]) == 0:
            pass
        else:
            print(
                "{}: measured flow is {} sccm. Flow setpoint is {} sccm. Concentration is {}%".format(
                    fluid_co_co2_b, lst_co_co2_b[0], lst_co_co2_b[1], CO_CO2_percent_b
                )
            )

        if float(lst_hc_a[1]) == 0:
            pass
        else:
            print(
                "{}: measured flow is {} sccm. Flow setpoint is {} sccm. Concentration is {}%".format(
                    fluid_hc_a, lst_hc_a[0], lst_hc_a[1], HC_percent_a
                )
            )

        if float(lst_hc_b[1]) == 0:
            pass
        else:
            print(
                "{}: measured flow is {} sccm. Flow setpoint is {} sccm. Concentration is {}%".format(
                    fluid_hc_b, lst_hc_b[0], lst_hc_b[1], HC_percent_b
                )
            )

        if float(lst_carrier_a[1]) == 0:
            pass
        else:
            print(
                "{}: measured flow is {} sccm. Flow setpoint is {} sccm".format(
                    fluid_carrier_a, lst_carrier_a[0], lst_carrier_a[1]
                )
            )

        if float(lst_carrier_b[1]) == 0:
            pass
        else:
            print(
                "{}: measured flow is {} sccm. Flow setpoint is {} sccm".format(
                    fluid_carrier_b, lst_carrier_b[0], lst_carrier_b[1]
                )
            )

        print("Total flow line A: {} sccm".format(total_flow_a))

        print("Total flow line B: {} sccm".format(total_flow_b))

        print("-----------------------")
        print("--- Pressure Report ---")
        print("-----------------------")

        print("Pressure in line A: {} psia".format(lst_p_a[0]))

        print("Pressure in line B: {} psia".format(lst_p_b[0]))
        print(
            "Note: If using gases different than the calibrated ones fix the reported flows/concentrations by their correspondent calibration factor"
        )
        print("------------------------------------------------------------")


if __name__ == "__main__":
    vc = GasControl()
    vc.pulses_mode()
    vc.get_status()

    vc.flowsms_setpoints(
        H2=4.0,
        He_mix=16,
        He_pulses=17.6,
    )

    vc.pulses_mode()

    vc.flowsms_status(10)
    vc.flowsms_setpoints()
    vc.flowsms_status(10)

    vc.flowsms_setpoints(
        H2=4.0,

    )
    # vc.modulation(
    #     pulses=10,
    #     time1=10,
    #     time2=10,
    #     start_gas="pulse",
    #     end_gas="pulse",
    #     monitoring_interval=0.1,
    # )
