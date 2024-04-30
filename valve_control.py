"""Valve and Mass flow control module

__author__ = "Ryuichi Shimogawa"
__version__ = "1.0"
__email__ = "ryuichi.shimogawa@stonybrook.edu"

Notes:
This module is based on the code written by Jorge Moncada Vivas.
"""

import os
import time
import serial
from serial.tools import list_ports

import propar

# The HID for the valve 3. This is should ideally be a specified in a different file.
# HID_VALVE = "USB VID:PID=067B:2303 SER= LOCATION=1-11" #RS232
HID_VALVE = "COM12" #RS485
HID_MFC = "COM11"

# This is a dictionary that maps the valve position to an integer.
VALVE_POSITION = {"A": 0, "B": 1, "Unknown": 1, "pulse": 0, "cont": 1, "mix": 1}


class ValveControl:
    def __init__(
        self,
        control_hid: str = HID_VALVE,
        control_comport: str = None,
        num_valves=8,
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
            mf_hid (str): HID of the mfc device, you can also specify the name or hid of the comport [default: HID_MFC]
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
        self.ser.write(b"/GCW\r")
        print("Feeding He to Gas Line A")

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
            "CO2",
            "CO",
            "CH4",
            "H2",
            "D2",
            "O2",
            "He_mix",
            "He_pulses",
            "Ar_pulses",
            "Ar_mix",
            "N2_mix",
            "N2_pulses",
        ]

        self.gas_dict = {self.gas_list[i]: i for i in range(len(self.gas_list))}

        self.gas_ID = {
            "CO2": 4,
            "CO": 6,
            "CH4": 9,
            "H2": 10,
            "D2": 10,
            "O2": 11,
            "He_mix": 7,
            "He_pulses": 5,
            "Ar_pulses": 5,
            "Ar_mix": 7,
            "N2_mix": 7,
            "N2_pulses": 5,
        }

        self.gas_cal = {
            "CO2": None,
            "CO": None,
            "CH4": None,
            "H2": None,
            "D2": None,
            "O2": None,
            "He_mix": 0,
            "He_pulses": 0,
            "Ar_pulses": 1,
            "Ar_mix": 1,
            "N2_mix": 2,
            "N2_pulses": 2,
        }

        self.gas_flow_range = {
            "CO2": [0.6, 30.0],
            "CO": [0.6, 30.0],
            "CH4": [0.6, 30.0],
            "H2": [0.6, 30.0],
            "D2": [0.6, 30.0],
            "O2": [0.6, 30.0],
            "He_mix": [0.6, 60.0],
            "He_pulses": [0.6, 60.0],
            "Ar_pulses": [0.6, 60.0],
            "Ar_mix": [0.6, 60.0],
            "N2_mix": [0.6, 60.0],
            "N2_pulses": [0.6, 60.0],
        }

        self.calibration_factor = {
            "CO2": 1.0,
            "CO": 1.0,
            "CH4": 1.0,
            "H2": 1.0,
            "D2": 1.0,
            "O2": 1.0,
            "He_mix": 1.0,
            "He_pulses": 1.0,
            "Ar_pulses": 1.0,
            "Ar_mix": 1.0,
            "N2_mix": 1.0,
            "N2_pulses": 1.0,
        }

        self.feed_gas_functions = {
            "CO2": self.feed_12CO2,
            "CO": self.feed_CO,
            "CH4": self.feed_12CH4,
            "H2": self.feed_H2,
            "D2": self.feed_D2,
            "O2": self.feed_16O2,
            "He_mix": self.carrier_He_mix,
            "He_pulses": self.carrier_He_pulses,
            "Ar_pulses": self.carrier_Ar_pulses,
            "Ar_mix": self.carrier_Ar_mix,
            "N2_mix": self.carrier_Ar_mix,
            "N2_pulses": self.carrier_Ar_pulses,
        }

        self.gas_float_to_int_factor = {
            "CO2": 30,
            "CO": 30,
            "CH4": 30,
            "H2": 30,
            "D2": 30,
            "O2": 30,
            "He_mix": 60,
            "He_pulses": 60,
            "Ar_pulses": 60,
            "Ar_mix": 60,
            "N2_mix": 60,
            "N2_pulses": 60,
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
        CO2=None,
        CO=None,
        CH4=None,
        H2=None,
        D2=None,
        O2=None,
        He_mix=None,
        He_pulses=None,
        Ar_mix=None,
        Ar_pulses=None,
        N2_mix=None,
        N2_pulses=None,
    ):
        """Function that sets the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            CO2 (float): Flow rate of CO2 in sccm [default: None]
            CO (float): Flow rate of CO in sccm [default: None]
            CH4 (float): Flow rate of CH4 in sccm [default: None]
            H2 (float): Flow rate of H2 in sccm [default: None]
            D2 (float): Flow rate of D2 in sccm [default: None]
            O2 (float): Flow rate of O2 in sccm [default: None]
            He_mix (float): Flow rate of He in sccm for the mixing line [default: None]
            He_pulses (float): Flow rate of He in sccm for the pulses line [default: None]
            Ar_mix (float): Flow rate of Ar in sccm for the mixing line [default: None]
            Ar_pulses (float): Flow rate of Ar in sccm for the pulses line [default: None]
            N2_mix (float): Flow rate of N2 in sccm for the mixing line [default: None]
            N2_pulses (float): Flow rate of N2 in sccm for the pulses line [default: None]
        """
        self.set_flowrate("CO2", CO2)
        self.set_flowrate("CO", CO)
        self.set_flowrate("CH4", CH4)

        if H2 is not None and H2 > 0.0:
            self.set_flowrate("H2", H2)
        else:
            self.set_flowrate("D2", D2)

        self.set_flowrate("O2", O2)

        if He_mix is not None and He_mix > 0.0:
            self.set_flowrate("He_mix", He_mix)
        elif Ar_mix is not None and Ar_mix > 0.0:
            self.set_flowrate("Ar_mix", Ar_mix)
        else:
            self.set_flowrate("N2_mix", N2_mix)

        if He_pulses is not None and He_pulses > 0.0:
            self.set_flowrate("He_pulses", He_pulses)
        elif Ar_pulses is not None and Ar_pulses > 0.0:
            self.set_flowrate("Ar_pulses", Ar_pulses)
        else:
            self.set_flowrate("N2_pulses", N2_pulses)

    def flowsms_status(self, delay=0.0):
        """Function that reads the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            delay (float): Delay time in seconds before reading the flow rates [default: 0.0]
        """

        # Node ID values assigned in the MFCs configuration
        ID_P_mix = 3
        ID_CO2 = 4
        ID_carrier_pulses = 5
        ID_CO = 6
        ID_carrier_mix = 7
        ID_P_pulses = 8
        ID_CH4 = 9
        ID_H2 = 10
        ID_O2 = 11

        # Carrier gas ID assigned in the MFCs configuration
        carrier_mix_He = 0
        carrier_mix_Ar = 1
        carrier_mix_N2 = 2
        carrier_pulses_He = 0
        carrier_pulses_Ar = 1
        carrier_pulses_N2 = 2

        # Setting a delay time before reading the actual flows
        # If non present zero delay will be applied before reading

        time.sleep(delay)

        # Parameters to be read from the Flow-SMS mass flow controllers
        params_co2 = [
            {
                "node": ID_CO2,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CO2,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
        ]
        params_co = [
            {
                "node": ID_CO,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CO,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
        ]
        params_ch4 = [
            {
                "node": ID_CH4,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_CH4,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
        ]
        params_h2 = [
            {
                "node": ID_H2,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_H2,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
        ]
        params_o2 = [
            {
                "node": ID_O2,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_O2,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
        ]
        params_carrier_mix = [
            {
                "node": ID_carrier_mix,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_carrier_mix,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_carrier_mix,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_carrier_pulses = [
            {
                "node": ID_carrier_pulses,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_carrier_pulses,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": ID_carrier_pulses,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]
        params_p_mix = [
            {
                "node": ID_P_mix,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            }
        ]
        params_p_pulses = [
            {
                "node": ID_P_pulses,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            }
        ]

        # Sending the specified parameters to the Flow-SMS
        values_co2 = self.mfc_master.read_parameters(params_co2)
        values_co = self.mfc_master.read_parameters(params_co)
        values_ch4 = self.mfc_master.read_parameters(params_ch4)
        values_h2 = self.mfc_master.read_parameters(params_h2)
        values_o2 = self.mfc_master.read_parameters(params_o2)
        values_carrier_mix = self.mfc_master.read_parameters(params_carrier_mix)
        values_carrier_pulses = self.mfc_master.read_parameters(params_carrier_pulses)
        values_p_mix = self.mfc_master.read_parameters(params_p_mix)
        values_p_pulses = self.mfc_master.read_parameters(params_p_pulses)

        # Creating induviduals lists for the read values from each MFC
        lst_co2 = []
        for value in values_co2:
            if "data" in value:
                flow = value.get("data")
            lst_co2.append(format(flow, ".2f"))

        lst_co = []
        for value in values_co:
            if "data" in value:
                flow = value.get("data")
            lst_co.append(format(flow, ".2f"))

        lst_ch4 = []
        for value in values_ch4:
            if "data" in value:
                flow = value.get("data")
            lst_ch4.append(format(flow, ".2f"))

        lst_h2 = []
        for value in values_h2:
            if "data" in value:
                flow = value.get("data")
            lst_h2.append(format(flow, ".2f"))

        lst_o2 = []
        for value in values_o2:
            if "data" in value:
                flow = value.get("data")
            lst_o2.append(format(flow, ".2f"))

        lst_carrier_mix = []
        for value in values_carrier_mix:
            if "data" in value:
                flow = value.get("data")
            lst_carrier_mix.append(format(flow, ".2f"))
        fluid_carrier_mix = float(lst_carrier_mix[2])
        if fluid_carrier_mix == 0:
            fluid_carrier_mix = "He"
        elif fluid_carrier_mix == 1:
            fluid_carrier_mix = "Ar"
        elif fluid_carrier_mix == 2:
            fluid_carrier_mix = "N2"

        lst_carrier_pulses = []
        for value in values_carrier_pulses:
            if "data" in value:
                flow = value.get("data")
            lst_carrier_pulses.append(format(flow, ".2f"))
        fluid_carrier_pulses = float(lst_carrier_pulses[2])
        if fluid_carrier_pulses == 0:
            fluid_carrier_pulses = "He"
        elif fluid_carrier_pulses == 1:
            fluid_carrier_pulses = "Ar"
        elif fluid_carrier_pulses == 2:
            fluid_carrier_pulses = "N2"

        lst_p_mix = []
        for value in values_p_mix:
            if "data" in value:
                pressure = value.get("data")
            lst_p_mix.append(format(pressure, ".2f"))

        lst_p_pulses = []
        for value in values_p_pulses:
            if "data" in value:
                pressure = value.get("data")
            lst_p_pulses.append(format(pressure, ".2f"))
        # Calculating percentage values for the actual flows

        total_flow_mix = float(
            format(
                float(lst_co[0])
                + float(lst_co2[0])
                + float(lst_ch4[0])
                + float(lst_h2[0])
                + float(lst_o2[0])
                + float(lst_carrier_mix[0]),
                ".2f",
            )
        )
        if total_flow_mix != 0:
            CO_percent = format((float(lst_co[0]) / total_flow_mix) * 100, ".1f")
            CO2_percent = format((float(lst_co2[0]) / total_flow_mix) * 100, ".1f")
            CH4_percent = format((float(lst_ch4[0]) / total_flow_mix) * 100, ".1f")
            H2_percent = format((float(lst_h2[0]) / total_flow_mix) * 100, ".1f")
            O2_percent = format((float(lst_o2[0]) / total_flow_mix) * 100, ".1f")
            # carrier_mix_percent = format((float(lst_carrier_mix[0])/total_flow_mix)*100, '.1f')

        # Creating and printing table with the actual and set flows, and line pressures
        print("------------")
        print("Flow (sccm):")
        print("------------")

        if float(lst_co2[1]) == 0:
            pass
        else:
            print(
                "CO2: meas. {}, sp. {}, {}%".format(lst_co2[0], lst_co2[1], CO2_percent)
            )

        if float(lst_ch4[1]) == 0:
            pass
        else:
            print(
                "CH4: meas. {}, sp. {}, {}%".format(lst_ch4[0], lst_ch4[1], CH4_percent)
            )

        if float(lst_co[1]) == 0:
            pass
        else:
            print("CO:  meas. {}, sp. {}, {}%".format(lst_co[0], lst_co[1], CO_percent))

        if float(lst_h2[1]) == 0:
            pass
        else:
            print("H2:  meas. {}, sp. {}, {}%".format(lst_h2[0], lst_h2[1], H2_percent))

        if float(lst_o2[1]) == 0:
            pass
        else:
            print("O2:  meas. {}, sp. {}, {}%".format(lst_o2[0], lst_o2[1], O2_percent))

        if float(lst_carrier_mix[1]) == 0:
            pass
        else:
            print(
                "{} mix:    meas. {}, sp. {}".format(
                    fluid_carrier_mix, lst_carrier_mix[0], lst_carrier_mix[1]
                )
            )

        if float(lst_carrier_pulses[1]) == 0:
            pass
        else:
            print(
                "{} pulses: meas. {}, sp. {} - Carrier".format(
                    fluid_carrier_pulses, lst_carrier_pulses[0], lst_carrier_pulses[1]
                )
            )

        print("Total mixing line: {} sccm".format(total_flow_mix))

        print("Total pulses line: {} sccm".format(float(lst_carrier_pulses[0])))

        print("----------------")
        print("Pressure (psig):")
        print("----------------")

        print("Pressure mixing: " + lst_p_mix[0])

        print("Pressure pulses: " + lst_p_pulses[0])
        print(
            "/nIf using labeled gases fix the reported flows/concentrations by their correspondent calibration factor/n"
        )
        print("------------------------------------------------------------")


if __name__ == "__main__":
    vc = ValveControl()
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
