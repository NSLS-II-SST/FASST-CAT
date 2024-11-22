"""Valves, temperature, and Mass flow control module

__author__ = "Jorge Moncada Vivas"
__version__ = "3.0"
__email__ = "moncadaja@gmail.com"
__date__ = "10/24/2024"

Notes:
By Jorge Moncada Vivas and contributions of Ryuichi Shimogawa
"""

import os
import time
import socket
import serial
from serial.tools import list_ports
from datetime import datetime
import logging
from functools import wraps
import threading

import propar

from serialTCP import serialTCP

import json
import platform

from valves import EthernetValves, SerialValves  # Import additional valve classes
from valves import create_valves
from eurothermSerial import EuroSerial
from eurothermTCP import EuroTCP

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# ███████╗ █████╗ ███████╗███████╗████████╗ ██████╗ █████╗ ████████╗
# ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗╚══██╔══╝
# █████╗  ███████║███████╗███████╗   ██║   ██║     ███████║   ██║
# ██╔══╝  ██╔══██║╚════██║╚════██║   ██║   ██║     ██╔══██║   ██║
# ██║     ██║  ██║███████║███████║   ██║   ╚██████╗██║  ██║   ██║
# ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝    ╚═════╝╚═╝  ╚═╝   ╚═╝


def pressure_alarm(low_threshold=10, high_threshold=30):
    """
    Decorator function that keeps track of pressure for safe operation. It will trigger
    an alarm if low or high pressure thresholds are exceeded. In the event of a trigger
    all shutoff valves will be closed and the process temperature will be taken down to 20C

    Args:
    low_threshold (int): lower pressure limit trigger value in case of working under vacuum
    high_theshold (int): higher pressure limit trigger value in case of a serious flow restriction event
    """

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Flag to signal when the monitored method has finished
            finished = threading.Event()

            # Define a background function to monitor the pressure
            def monitor_pressure():
                while not finished.is_set():
                    # Read the pressure values
                    p_a, p_b = self.pressure_report()
                    # Check if either pressure exceeds the threshold
                    if p_a > high_threshold or p_b > high_threshold:
                        self.flowsms_setpoints()  # Trigger adjustment if above threshold
                        print(
                            "!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n",
                            "!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!HIGH PRESSURE ALARM!!!!!!!!!!!!!!\n",
                            f"PRESSURE IN LINE A = {p_a} psia, PRESSURE IN LINE B = {p_b} psia.\n",
                            "CLOSING ALL SHUTOFF VALVES AND TAKING SYSTEM TO ROOM TEMPERATURE",
                        )
                        finished.set()  # Stop monitoring if alarm is triggered
                        self.setpoint_finish_experiment()
                        return
                    elif p_a < low_threshold or p_b < low_threshold:
                        self.flowsms_setpoints()  # Trigger adjustment if above threshold
                        print(
                            "!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n",
                            "!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n!!!!!!!!!!!!!!LOW PRESSURE ALARM!!!!!!!!!!!!!!\n",
                            f"PRESSURE IN LINE A = {p_a} psia, PRESSURE IN LINE B = {p_b} psia.\n",
                            "CLOSING ALL SHUTOFF VALVES AND TAKING SYSTEM TO ROOM TEMPERATURE",
                        )
                        finished.set()  # Stop monitoring if alarm is triggered
                        self.setpoint_finish_experiment()
                        return
                    time.sleep(1)  # Check every second

            # Start monitoring in a separate thread
            monitor_thread = threading.Thread(target=monitor_pressure)
            monitor_thread.start()

            try:
                # Execute the main function while monitoring continues in the background
                result = func(self, *args, **kwargs)
            finally:
                # Signal the monitor thread to stop after the function completes
                finished.set()
                monitor_thread.join()  # Ensure the monitor thread completes

            return result

        return wrapper

    return decorator


class GasControl:
    def __init__(self, config_file="config.json") -> None:
        """Initialize the gas control system.

        Args:
            config_file (str): Path to configuration file [default: "config.json"]
        """
        with open(config_file, "r") as file:
            config = json.load(file)
        self.config = config
        # Initialize valve controller using factory function
        self.valves = create_valves(config)
        print(
            f"Connected to valves via {'Ethernet' if isinstance(self.valves, EthernetValves) else 'Serial'}"
        )

        # Detect the OS and adjust serial port naming with proper numbering
        if platform.system() == "Windows":
            self.valves_hid = config["HID_VALVE"]
            self.valves_comport = config["COM_VALVE"]
            self.mfc_hid = config["HID_MFC"]
            self.mfc_comport = config["COM_MFC"]
            self.tmp_hid = config["HID_TMP"]
            self.tmp_com = config["COM_TMP"]
        else:  # Assume Linux
            # Adjust the numbering: COMx in Windows -> /dev/ttyS(x-1) in Linux
            self.valves_hid = f"/dev/ttyS{int(config['HID_VALVE'][-1]) - 1}"
            self.valves_comport = f"/dev/ttyS{int(config['COM_VALVE'][-1]) - 1}"
            self.mfc_hid = f"/dev/ttyS{int(config['HID_MFC'][-1]) - 1}"
            self.mfc_comport = f"/dev/ttyS{int(config['COM_MFC'][-1]) - 1}"
            self.tmp_hid = f"/dev/ttyS{int(config['HID_TMP'][-1]) - 1}"
            self.tmp_com = f"/dev/ttyS{int(config['COM_TMP'][-1]) - 1}"

        self.baud_mfc = config["BAUD_MFC"]
        self.sub_add_tmp = config["SUB_ADD_TMP"]
        self.host_euro = config["HOST_EURO"]
        self.port_euro = config["PORT_EURO"]
        self.host_moxa = config["HOST_MOXA"]
        self.port_valves = config["PORT_VALVES"]
        self.port_mfc = config["PORT_MFC"]
        self.out_terminator = "\r"

        # self.init_mfc_comport()
        # print(f"MFC comport: {self.mfc_comport}")
        #
        if "HOST_MOXA" in config and "PORT_MFC" in config:
            self.mfc_master = propar.master(
                self.host_moxa, self.port_mfc, serial_class=serialTCP
            )
        else:
            self.init_mfc_comport()
            self.mfc_master = propar.master(self.mfc_comport, 38400)
        self.define_flowsms()

        if "HOST_EURO" in config and "PORT_EURO" in config:
            self.eurotherm = EuroTCP(config["HOST_EURO"], config["PORT_EURO"])
        else:
            euro_comport = self._convert_com_port(config["COM_TMP"])
            euro_sub = config["SUB_ADD_TMP"]
            self.eurotherm = EuroSerial(euro_comport, euro_sub)

        self.p_a = 0
        self.p_b = 0

    def _convert_com_port(self, com_port):
        """Convert between Windows and Linux style serial ports.

        Args:
            com_port (str): Windows-style COM port (e.g. 'COM1')

        Returns:
            str: Appropriate port name for current platform
        """
        if platform.system() != "Windows":
            # Convert Windows-style COM port to Linux-style
            return f"/dev/ttyS{int(com_port[-1]) - 1}"
        return com_port

    def send_command(self, command):
        try:
            self.sock.sendall((command + self.out_terminator).encode())
            response = self.sock.recv(4096)
            # print(f"Raw Response: {response}")  # Print raw response for debugging
            decoded_response = response.decode().strip()
            # print(decoded_response)
            # split_response = decoded_response.split("\t")
            # print(split_response)
            return decoded_response
        except Exception as e:
            print(f"Failed to send command: {e}")
            return None

    def close_socket(self):
        if self.sock:
            self.sock.close()
            print("Socket closed.")
        if self.data_sock:
            self.data_sock.close()
            print("Data socket closed.")

    def init_mfc_comport(self):
        """Initialize the comport of the mfc device
        It will print the available comports if no comport is specified
        """

        if self.mfc_hid:
            mfc_port = list_ports.grep(self.mfc_hid)
            mfc_port = list(mfc_port)

            if (len(mfc_port) == 0) and (self.mfc_comport is None):
                self.print_available_comports()

                raise ValueError(f"No comport found for mfc_hid: {self.mfc_hid}")
            elif len(mfc_port) == 1:
                self.mfc_comport = mfc_port[0].device
            else:
                self.print_available_comports()
                raise ValueError(f"Multiple comports found for mfc_hid: {self.mfc_hid}")

        if self.mfc_comport is None:
            self.print_available_comports()
            raise ValueError("No comport specified")

    def print_available_comports(self):
        """Prints the available comports along with their description and hardware id"""
        comports_available = list_ports.comports()
        print("Available comports:")
        for comport in comports_available:
            print(f"{comport.device}: {comport.description} [{comport.hwid}]")

    # ██╗   ██╗ █████╗ ██╗    ██╗   ██╗███████╗███████╗
    # ██║   ██║██╔══██╗██║    ██║   ██║██╔════╝██╔════╝
    # ██║   ██║███████║██║    ██║   ██║█████╗  ███████╗
    # ╚██╗ ██╔╝██╔══██║██║    ╚██╗ ██╔╝██╔══╝  ╚════██║
    #  ╚████╔╝ ██║  ██║███████╗╚████╔╝ ███████╗███████║
    #   ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═══╝  ╚══════╝╚══════╝

    def carrier_He_A(self):
        """Function that selects He as carrier gas for the Gas Line A"""
        self.valves.move_valve_to_position("G", "OFF")
        print("Feeding He to Gas Line A")

    def carrier_Ar_A(self):
        """Function that selects Ar as carrier gas for Gas Line A"""
        self.valves.move_valve_to_position("G", "ON")
        print("Feeding Ar to Gas Line A")

    def carrier_He_B(self):
        """Function that selects He as carrier gas for Gas Line B"""
        self.valves.move_valve_to_position("F", "ON")
        print("Feeding He to Gas Line B")

    def carrier_Ar_B(self):
        """Function that selects Ar as carrier gas for Gas Line B"""
        self.valves.move_valve_to_position("F", "OFF")
        print("Feeding Ar to Gas Line B")

    def feed_CO2_AB(self):
        """Function that selects CO2 as gas source for Gas Line A and B"""
        self.valves.move_valve_to_position("D", "ON")
        print("Feeding CO2 to Gas Line A and B")

    def feed_CO_AB(self):
        """Function that selects CO as gas source for Gas Line A and B"""
        self.valves.move_valve_to_position("D", "OFF")
        print("Feeding CO to Gas Line A and B")

    def feed_H2_A(self):
        """Function that selects hydrogen as gas source for Gas Line A"""
        self.valves.move_valve_to_position("I", "OFF")
        print("Feeding H2 to Gas Line A")

    def feed_D2_A(self):
        """Function that selects deuterium as gas source for Gas Line A"""
        self.valves.move_valve_to_position("I", "ON")
        print("Feeding D2 to Gas Line A")

    def feed_H2_B(self):
        """Function that selects hydrogen as gas source for Gas Line B"""
        self.valves.move_valve_to_position("H", "ON")
        print("Feeding H2 to Gas Line B")

    def feed_D2_B(self):
        """Function that selects deuterium as gas source for Gas Line B"""
        self.valves.move_valve_to_position("H", "OFF")
        print("Feeding D2 to Gas Line B")

    def feed_CH4_AB(self):
        """Fuction that selects methane as gas source for Gas Line A and B"""
        self.valves.move_valve_to_position("E", "ON")
        print("Feeding CH4 to Gas Line A and B")

    def feed_C2H6_AB(self):
        """Function that selects ethane as gas source for Gas Line A and B"""
        self.valves.move_valve_to_position("E", "OFF")
        print("Feeding C2H6 to Gas Line A and B")

    def feed_O2_AB(self):
        """Fuction that selects CO as carbon monoxide gas source for the mixing line
        This function is not implemented in the valve control module"""
        pass

    def valve_C(self, position: str):
        """Function that selects the position of Valve C (Reaction mode selection module)

        Args:
            position (str): Position of the valve, can be "off" or "on"
                            "off" means that the valve is in the position Gas Line A/B -> reactor
                            "on" means that the valve is in the position Gas Line A/B -> gas loop
        """
        if position == "OFF":
            self.valves.move_valve_to_position("C", position)
            print("Gas Line A/B valve position: off (Gas Line A/B -> reactor)")
        elif position == "ON":
            self.valves.move_valve_to_position("C", position)
            print("Gas Line A/B valve position: on (Gas Line A/B -> loop)")

    def valve_B(self, position: str):
        """Function that selects the position of Valve B (Reaction mode selection module)

        Args:
            position (str): Position of the valve, can be "off" or "on"
                            "off" means that the valve is in the position Gas Line A -> reactor
                            "on" means that the valve is in the position Gas Line B -> reactor
        """

        if position == "OFF":
            self.valves.move_valve_to_position("B", position)
            print(
                "Valve B position: off \n(Gas Line A -> reactor)\n(Gas Line B -> pulses)"
            )
        elif position == "ON":
            self.valves.move_valve_to_position("B", position)
            print(
                "Valve B position: off \n(Gas Line B -> reactor)\n(Gas Line A -> pulses)"
            )

    def valve_A(self, position: str):
        """Function that selects the position of Valve A (Reaction mode selection module)

        Args:
            position (str): Position of the valve, can be "off" or "on"
                            "off" means that the valve is in the loop 1 -> reactor, loop 2 -> vent
                            "on" means that the valve is in the loop 2 -> reactor, loop 1 -> vent
        """
        if position == "OFF":
            self.valves.move_valve_to_position("A", position)
            print(
                "Pulses line valve position: off (Gas Line A -> loop 1 -> vent / Gas Line B -> loop 2 -> reactor)"
            )
        elif position == "ON":
            self.valves.move_valve_to_position("A", position)
            print(
                "Pulses line valve position: on (Gas Line B -> loop 2 -> vent / Gas Line A -> loop 1 -> reactor)"
            )

    def cont_mode_A(self, verbose: bool = True):
        """Function that selects the position of the valves in the reaction mode selection
        module to the continuous mode gas line A mode

        Gas Line A -> reactor ... Gas Line B -> loops -> vent

        Args:
            verbose (bool): If True, prints the valve status [default: True]
        """
        self.valves.move_valve_to_position("A", "OFF")
        self.valves.move_valve_to_position("B", "OFF")
        self.valves.move_valve_to_position("C", "OFF")
        if verbose:
            print("Valves operation mode: continuous mode Gas Line A")
            print("Gas Line A -> reactor ... Gas Line B -> loops -> vent")

    def cont_mode_B(self, verbose: bool = True):
        """Function that selects the position of the valves in the reaction mode selection
        module to the continuous mode gas line B mode

        Gas Line B -> reactor ... Gas Line A -> loops -> waste

        Args:
            verbose (bool): If True, prints the valve status [default: True]
        """
        self.valves.move_valve_to_position("A", "OFF")
        self.valves.move_valve_to_position("B", "ON")
        self.valves.move_valve_to_position("C", "OFF")
        if verbose:
            print("Valves operation mode: continuous mode Gas Line B")
            print("Gas Line B -> reactor ... Gas Line A -> loops -> waste")

    def pulses_loop_mode_A(self, verbose=True):
        """Function that selects the position of the valves in the reaction mode selection
        module to the pulses loop mode

        Gas Line B -> loop 2 -> reactor ... Gas Line A -> loop 1 -> vent

        Args:
            verbose (bool): If True, prints the valve status [default: True]
        """
        self.valves.move_valve_to_position("A", "ON")
        self.valves.move_valve_to_position("B", "OFF")
        self.valves.move_valve_to_position("C", "ON")
        if verbose:
            print("Valves operation mode: pulses with gas loops")
            print("Gas Line B -> loop 2 -> reactor ... Gas Line A -> loop 1 -> vent")

    def pulses_loop_mode_B(self, verbose=True):
        """Function that selects the position of the valves in the reaction mode selection
        module to the pulses loop mode

        Gas Line B -> loop 2 -> reactor ... Gas Line A -> loop 1 -> vent

        Args:
            verbose (bool): If True, prints the valve status [default: True]
        """
        self.valves.move_valve_to_position("A", "ON")
        self.valves.move_valve_to_position("B", "ON")
        self.valves.move_valve_to_position("C", "ON")
        if verbose:
            print("Valves operation mode: pulses with gas loops")
            print("Gas Line B -> loop 2 -> reactor ... Gas Line A -> loop 1 -> vent")

    def send_pulses_loop_A(self, pulses, time_bp):
        # total_time_loop = float(pulses) * float(time_bp)
        # total_time.append(total_time_loop)
        # tmp.pulse_ON()
        self.pulses_loop_mode_A()
        int_pulses = int(pulses)
        float_time = float(time_bp)
        print("Valves operation mode: pulses (dual loop alternation)")
        print(
            f"Number of pulses (loop): {pulses}\nTime in between pulses (s): {time_bp}"
        )
        print(
            "Valve Position Off: Gas Line B -> loop 2 -> reactor /// Gas Line A -> loop 1 -> vent"
        )
        print(
            "Valve Position On: Gas line B -> loop 1 -> reactor /// Gas Line A -> loop 2 -> vent"
        )
        for pulse in range(0, int_pulses):
            # tmp.pulse_ON()
            self.valves.write(
                b"/ATO"
            )  # Comand that executes the pulses valve actuation
            print(
                f"Sending pulse number {pulse+1} of {int_pulses}", end="\r"
            )  # Pulse status message for terminal window
            time.sleep(float_time)  # Conversion of seconds to miliseconds
            # tmp.pulse_OFF()
        print("Pulses have finished")  # End of the pulses message

    def send_pulses_loop_B(self, pulses, time_bp):
        # total_time_loop = float(pulses) * float(time_bp)
        # total_time.append(total_time_loop)
        # tmp.pulse_ON()
        self.pulses_loop_mode_B()
        int_pulses = int(pulses)
        float_time = float(time_bp)
        print("Valves operation mode: pulses (dual loop alternation)")
        print(
            f"Number of pulses (loop): {pulses}\nTime in between pulses (s): {time_bp}"
        )
        print(
            "Valve Position Off: Gas Line A -> loop 2 -> reactor /// Gas Line B -> loop 1 -> vent"
        )
        print(
            "Valve Position On: Gas Line A -> loop 1 -> reactor /// Gas Line B -> loop 2 -> vent"
        )
        for pulse in range(0, int_pulses):
            # tmp.pulse_ON()
            self.valves.write(
                b"/ATO"
            )  # Comand that executes the pulses valve actuation
            print(
                f"Sending pulse number {pulse+1} of {int_pulses}", end="\r"
            )  # Pulse status message for terminal window
            time.sleep(float_time)  # Conversion of seconds to miliseconds
            # tmp.pulse_OFF()
        print("Pulses have finished")  # End of the pulses message

    def send_pulses_valve_A(self, pulses, time_vo, time_bp):
        # total_time_loop = (float(pulses) * float(time_bp)) + (float(pulses) * float(time_vo))
        # total_time.append(total_time_loop)
        valve_actuation_time = 0.145
        self.cont_mode_A()
        int_pulses = int(pulses)  # Preparing the integer input for the loop range
        float_time_vo = float(
            time_vo
        )  # Preparing the float input for the sleep function vo
        float_time_bp = float(
            time_bp
        )  # Preparing the float input for the sleep function bp
        print("Valves operation mode: pulses (valve)")
        print(
            f"Number of pulses (valve): {pulses}\nTime valve open (s): {time_vo}\nTime in between pulses (s): {time_bp}"
        )
        print(
            "Valve Position Off: mixing line -> reactor /// pulses line carrier -> loop 2 -> loop 1 -> waste"
        )
        print(
            "Valve Position On: pulses line carrier -> reactor /// mixing line -> loop 2 -> loop 1 -> waste"
        )
        for pulse in range(0, int_pulses):
            self.cont_mode_B()  # Comand that executes the pulses valve actuation
            time.sleep(
                float_time_vo + valve_actuation_time
            )  # Conversion of seconds to miliseconds
            self.cont_mode_A()  # Comand that executes the pulses valve actuation
            print(
                f"Sending pulse number {pulse+1} of {int_pulses}", end="\r"
            )  # Pulse status message for terminal window
            time.sleep(float_time_bp)  # Conversion of seconds to miliseconds
        print("Pulses have finished")  # End of the pulses message

    # ███████╗██╗      ██████╗ ██╗    ██╗      ███████╗███╗   ███╗███████╗
    # ██╔════╝██║     ██╔═══██╗██║    ██║      ██╔════╝████╗ ████║██╔════╝
    # █████╗  ██║     ██║   ██║██║ █╗ ██║█████╗███████╗██╔████╔██║███████╗
    # ██╔══╝  ██║     ██║   ██║██║███╗██║╚════╝╚════██║██║╚██╔╝██║╚════██║
    # ██║     ███████╗╚██████╔╝╚███╔███╔╝      ███████║██║ ╚═╝ ██║███████║
    # ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝       ╚══════╝╚═╝     ╚═╝╚══════╝

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
            "D2_A": 4,
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
            "D2_B": 13,
        }

        self.gas_cal = {
            "H2_A": 0,
            "H2_B": 0,
            "D2_A": 1,
            "D2_B": 1,
            "O2_A": 0,
            "O2_B": 0,
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
            "CO2_BL": 1.0,
            "He_A": 1.0,
            "He_B": 1.0,
            "Ar_A": 1.0,
            "Ar_B": 1.0,
            "N2_A": 1.0,
            "N2_B": 1.0,
        }

        self.feed_gas_functions = {
            "H2_A": self.feed_H2_A,
            "H2_B": self.feed_H2_B,
            "D2_A": self.feed_D2_A,
            "D2_B": self.feed_D2_B,
            "O2_A": self.feed_O2_AB,
            "O2_B": self.feed_O2_AB,
            "CO_AH": self.feed_CO_AB,
            "CO_AL": self.feed_CO_AB,
            "CO_BH": self.feed_CO_AB,
            "CO_BL": self.feed_CO_AB,
            "CH4_A": self.feed_CH4_AB,
            "CH4_B": self.feed_CH4_AB,
            "C2H6_A": self.feed_C2H6_AB,
            "C2H6_B": self.feed_C2H6_AB,
            "C3H8_A": self.feed_C2H6_AB,
            "C3H8_B": self.feed_C2H6_AB,
            "CO2_AH": self.feed_CO2_AB,
            "CO2_AL": self.feed_CO2_AB,
            "CO2_BH": self.feed_CO2_AB,
            "CO2_BL": self.feed_CO2_AB,
            "He_A": self.carrier_He_A,
            "He_B": self.carrier_He_B,
            "Ar_A": self.carrier_Ar_A,
            "Ar_B": self.carrier_Ar_B,
            "N2_A": self.carrier_Ar_A,
            "N2_B": self.carrier_Ar_B,
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
        H2_A: float = None,
        D2_A: float = None,
        O2_A: float = None,
        CO_AH: float = None,
        CO2_AH: float = None,
        CO_AL: float = None,
        CO2_AL: float = None,
        CH4_A: float = None,
        C2H6_A: float = None,
        C3H8_A: float = None,
        He_A: float = None,
        Ar_A: float = None,
        N2_A: float = None,
        He_B: float = None,
        Ar_B: float = None,
        N2_B: float = None,
        CH4_B: float = None,
        C2H6_B: float = None,
        C3H8_B: float = None,
        CO_BH: float = None,
        CO2_BH: float = None,
        CO_BL: float = None,
        CO2_BL: float = None,
        O2_B: float = None,
        H2_B: float = None,
        D2_B: float = None,
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

    def flowsms_setpoints2(self, **kwargs):
        """Function to set flow rates for gases with any unspecified gases defaulting to zero."""

        gas_params = {
            "H2_A": ("H2_A", "D2_A"),
            "H2_B": ("H2_B", "D2_B"),
            "O2_A": ("O2_A",),
            "O2_B": ("O2_B",),
            "CH4_A": ("CH4_A", "C2H6_A", "C3H8_A"),
            "CH4_B": ("CH4_B", "C2H6_B", "C3H8_B"),
            "CO_AH": ("CO_AH", "CO2_AH", "CO_AL", "CO2_AL"),
            "CO_BH": ("CO_BH", "CO2_BH", "CO_BL", "CO2_BL"),
            "He_A": ("He_A", "Ar_A", "N2_A"),
            "He_B": ("He_B", "Ar_B", "N2_B"),
        }

        # Loop to set each specified flow from kwargs
        for gas_key, options in gas_params.items():
            # Set flow for the specified gas, defaulting to the primary option if no specific choice
            for option in options:
                if option in kwargs and kwargs[option] is not None:
                    self.set_flowrate(option, kwargs[option])
                    break
            else:
                # No specified flowrate, set primary option to zero
                self.set_flowrate(options[0], 0.0)

    def generate_params(self, node_id):
        """Helper function that creates the dictionary with the values to pull from devices

        Args:
            node ID (int): MODBUS address for each device
        """
        return [
            {
                "node": node_id,
                "proc_nr": 33,
                "parm_nr": 0,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": node_id,
                "proc_nr": 33,
                "parm_nr": 3,
                "parm_type": propar.PP_TYPE_FLOAT,
            },
            {
                "node": node_id,
                "proc_nr": 1,
                "parm_nr": 16,
                "parm_type": propar.PP_TYPE_INT8,
            },
        ]

    def flowsms_status(self, delay=0.0, verbose=True):
        """Function that reads the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            delay (float): Delay time in seconds before reading the flow rates [default: 0.0]
        """

        time.sleep(delay)

        # Parameters to be read from the Flow-SMS mass flow controllers
        params_h2_d2_a = self.generate_params(self.gas_ID["H2_A"])
        params_h2_d2_b = self.generate_params(self.gas_ID["H2_B"])
        params_o2_a = self.generate_params(self.gas_ID["O2_A"])
        params_o2_b = self.generate_params(self.gas_ID["O2_B"])
        params_hc_a = self.generate_params(self.gas_ID["CH4_A"])
        params_hc_b = self.generate_params(self.gas_ID["CH4_B"])
        params_co_co2_a = self.generate_params(self.gas_ID["CO_AH"])
        params_co_co2_b = self.generate_params(self.gas_ID["CO_BH"])
        params_carrier_a = self.generate_params(self.gas_ID["He_A"])
        params_carrier_b = self.generate_params(self.gas_ID["He_B"])
        params_p_a = [
            {"node": 3, "proc_nr": 33, "parm_nr": 0, "parm_type": propar.PP_TYPE_FLOAT}
        ]
        params_p_b = [
            {"node": 14, "proc_nr": 33, "parm_nr": 0, "parm_type": propar.PP_TYPE_FLOAT}
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
            lst_h2_d2_a.append(f"{flow: .2f}")
        fluid_h2_d2_a = float(lst_h2_d2_a[2])
        if fluid_h2_d2_a == 0:
            fluid_h2_d2_a = "H2_A"
        elif fluid_h2_d2_a == 1:
            fluid_h2_d2_a = "D2_A"

        lst_h2_d2_b = []
        for value in values_h2_d2_b:
            if "data" in value:
                flow = value.get("data")
            lst_h2_d2_b.append(f"{flow: .2f}")
        fluid_h2_d2_b = float(lst_h2_d2_b[2])
        if fluid_h2_d2_b == 0:
            fluid_h2_d2_b = "H2_B"
        elif fluid_h2_d2_b == 1:
            fluid_h2_d2_b = "D2_B"

        lst_o2_a = []
        for value in values_o2_a:
            if "data" in value:
                flow = value.get("data")
            lst_o2_a.append(f"{flow: .2f}")

        lst_o2_b = []
        for value in values_o2_b:
            if "data" in value:
                flow = value.get("data")
            lst_o2_b.append(f"{flow: .2f}")

        lst_co_co2_a = []
        for value in values_co_co2_a:
            if "data" in value:
                flow = value.get("data")
            lst_co_co2_a.append(f"{flow: .2f}")
        fluid_co_co2_a = float(lst_co_co2_a[2])
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
            lst_co_co2_b.append(f"{flow: .2f}")
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
            lst_hc_a.append(f"{flow: .2f}")
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
            lst_hc_b.append(f"{flow: .2f}")
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
            lst_carrier_a.append(f"{flow: .2f}")
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
            lst_carrier_b.append(f"{flow: .2f}")
        fluid_carrier_b = float(lst_carrier_b[2])
        if fluid_carrier_b == 0:
            fluid_carrier_b = "He"
        elif fluid_carrier_b == 1:
            fluid_carrier_b = "Ar"
        elif fluid_carrier_b == 2:
            fluid_carrier_b = "N2"

        lst_p_a = []
        p_a_dict = values_p_a[0]
        p_a = f"{p_a_dict.get('data'): .2f}"
        lst_p_a.append(p_a)

        lst_p_b = []
        p_b_dict = values_p_b[0]
        p_b = f"{p_b_dict.get('data'): .2f}"
        lst_p_b.append(p_b)

        # Calculating percentage values for the actual flows

        total_flow_a = float(
            f"{(float(lst_h2_d2_a[0]) + float(lst_o2_a[0]) + float(lst_co_co2_a[0]) + float(lst_hc_a[0]) + float(lst_carrier_a[0])): .2f}"
        )
        if total_flow_a != 0:
            H2_D2_percent_a = f"{(float(lst_h2_d2_a[0]) / total_flow_a) * 100: .1f}"
            O2_percent_a = f"{(float(lst_o2_a[0]) / total_flow_a) * 100: .1f}"
            CO_CO2_percent_a = f"{(float(lst_co_co2_a[0]) / total_flow_a) * 100: .1f}"
            HC_percent_a = f"{(float(lst_hc_a[0]) / total_flow_a) * 100: .1f}"
            # carrier_a_percent = f"{(float(lst_carrier_a[0])/total_flow_a)*100: .1f}"

        total_flow_b = float(
            f"{(float(lst_h2_d2_b[0]) + float(lst_o2_b[0]) + float(lst_co_co2_b[0]) + float(lst_hc_b[0]) + float(lst_carrier_b[0])): .2f}"
        )
        if total_flow_b != 0:
            H2_D2_percent_b = f"{(float(lst_h2_d2_b[0]) / total_flow_b) * 100: .1f}"
            O2_percent_b = f"{(float(lst_o2_b[0]) / total_flow_b) * 100: .1f}"
            CO_CO2_percent_b = f"{(float(lst_co_co2_b[0]) / total_flow_b) * 100: .1f}"
            HC_percent_b = f"{(float(lst_hc_b[0]) / total_flow_b) * 100: .1f}"
            # carrier_b_percent = f"{(float(lst_carrier_b[0])/total_flow_b)*100: .1f}"

        # Creating and printing table with the actual and set flows, and line pressures

        if verbose:

            print(" ")
            print("------------------------------------------------------------")
            print("-------------------")
            print("--- Flow Report ---")
            print("-------------------")

            if float(lst_h2_d2_a[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_h2_d2_a}_A: measured flow is {lst_h2_d2_a[0]} sccm. Flow setpoint is {lst_h2_d2_a[1]} sccm. Concentration is {H2_D2_percent_a}%"
                )

            if float(lst_h2_d2_b[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_h2_d2_b}_B: measured flow is {lst_h2_d2_b[0]} sccm. Flow setpoint is {lst_h2_d2_b[1]} sccm. Concentration is {H2_D2_percent_b}%"
                )

            if float(lst_o2_a[1]) == 0:
                pass
            else:
                print(
                    f"O2_A: measured flow is {lst_o2_a[0]} sccm. Flow setpoint is {lst_o2_a[1]} sccm. Concentration is {O2_percent_a}%"
                )

            if float(lst_o2_b[1]) == 0:
                pass
            else:
                print(
                    f"O2_B: measured flow is {lst_o2_b[0]} sccm. Flow setpoint is {lst_o2_b[1]} sccm. Concentration is {O2_percent_b}%"
                )

            if float(lst_co_co2_a[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_co_co2_a}_A: measured flow is {lst_co_co2_a[0]} sccm. Flow setpoint is {lst_co_co2_a[1]} sccm. Concentration is {CO_CO2_percent_a}%"
                )

            if float(lst_co_co2_b[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_co_co2_b}_B: measured flow is {lst_co_co2_b[0]} sccm. Flow setpoint is {lst_co_co2_b[1]} sccm. Concentration is {CO_CO2_percent_b}%"
                )

            if float(lst_hc_a[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_hc_a}_A: measured flow is {lst_hc_a[0]} sccm. Flow setpoint is {lst_hc_a[1]} sccm. Concentration is {HC_percent_a}%"
                )

            if float(lst_hc_b[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_hc_b}_B: measured flow is {lst_hc_b[0]} sccm. Flow setpoint is {lst_hc_b[1]} sccm. Concentration is {HC_percent_b}%"
                )

            if float(lst_carrier_a[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_carrier_a}_A: measured flow is {lst_carrier_a[0]} sccm. Flow setpoint is {lst_carrier_a[1]} sccm"
                )

            if float(lst_carrier_b[1]) == 0:
                pass
            else:
                print(
                    f"{fluid_carrier_b}_B: measured flow is {lst_carrier_b[0]} sccm. Flow setpoint is {lst_carrier_b[1]} sccm"
                )

            print(f"Total flow line A: {total_flow_a} sccm")

            print(f"Total flow line B: {total_flow_b} sccm")

            print("-----------------------")
            print("--- Pressure Report ---")
            print("-----------------------")

            print(f"Pressure in line A: {lst_p_a[0]} psia")

            print(f"Pressure in line B: {lst_p_b[0]} psia")

            print("------------------------------------------------------------")

    def flowsms_status2(self, delay=0.0, verbose=True):
        """Function that reads the flow rates of the gases in the Flow-SMS mass flow controllers

        Args:
            delay (float): Delay time in seconds before reading the flow rates [default: 0.0]
        """
        time.sleep(delay)

        # Define gas parameters with respective gas IDs and names
        gas_params = {
            "H2_A": ("H2_A", "D2_A"),
            "H2_B": ("H2_B", "D2_B"),
            "O2_A": ("O2_A",),
            "O2_B": ("O2_B",),
            "CH4_A": ("CH4_A", "C2H6_A", "C3H8_A"),
            "CH4_B": ("CH4_B", "C2H6_B", "C3H8_B"),
            "CO_AH": ("CO_AH", "CO2_AH", "CO2_AL", "CO_AL"),
            "CO_BH": ("CO_BH", "CO2_BH", "CO2_BL", "CO_BL"),
            "He_A": ("He_A", "Ar_A", "N2_A"),
            "He_B": ("He_B", "Ar_B", "N2_B"),
        }

        # Initialize lists for storing the read values
        values_dict = {}

        # Read and store parameters for each gas
        for gas_key, fluid_types in gas_params.items():
            params = self.generate_params(self.gas_ID[gas_key])
            values = self.mfc_master.read_parameters(params)

            lst = []
            for value in values:
                if "data" in value:
                    flow = value.get("data")
                lst.append(f"{flow: .2f}")

            # Store the corresponding fluid type
            fluid_value = float(lst[2]) if len(fluid_types) > 1 else None
            if fluid_value is not None:
                fluid = fluid_types[int(fluid_value)]  # Pick based on the value
            else:
                fluid = fluid_types[0]

            values_dict[gas_key] = (lst, fluid)

        # Calculate percentage values for the actual flows
        total_flow_a = f'{(sum(float(values_dict[gas][0][0]) for gas in ["H2_A", "O2_A", "CO_AH", "CH4_A", "He_A"])): .2f}'
        total_flow_b = f'{(sum(float(values_dict[gas][0][0]) for gas in ["H2_B", "O2_B", "CO_BH", "CH4_B", "He_B"])): .2f}'

        # Concentration percentages for gases on line A and B
        percentages_a = {
            gas: f"{(float(values_dict[gas][0][0]) / float(total_flow_a)) * 100: .1f}"
            for gas in ["H2_A", "O2_A", "CO_AH", "CH4_A", "He_A"]
        }
        percentages_b = {
            gas: f"{(float(values_dict[gas][0][0]) / float(total_flow_b)) * 100: .1f}"
            for gas in ["H2_B", "O2_B", "CO_BH", "CH4_B", "He_B"]
        }

        # Creating and printing table with the actual and set flows, and line pressures
        if verbose:
            print(" ")
            print("------------------------------------------------------------")
            print("-------------------")
            print("--- Flow Report ---")
            print("-------------------")
            for gas_key, (lst, fluid) in values_dict.items():
                setpoint = lst[1]
                if float(setpoint) != 0:
                    concentration = (
                        percentages_a[gas_key]
                        if (
                            gas_key.endswith("_A")
                            or gas_key.endswith("_AH")
                            or gas_key.endswith("_AL")
                        )
                        else percentages_b[gas_key]
                    )
                    print(
                        f"{fluid}: measured flow is {lst[0]} sccm, Flow setpoint is {setpoint} sccm, Concentration is {concentration} %."
                    )

            print(f"Total flow line A: {total_flow_a} sccm")
            print(f"Total flow line B: {total_flow_b} sccm")
            print("-----------------------")
            print("--- Pressure Report ---")
            print("-----------------------")
            self.pressure_report(verbose=True)
            print("------------------------------------------------------------")

    def pressure_report(self, verbose: bool = False):
        values_p_a = self.mfc_master.read_parameters(
            [
                {
                    "node": 3,
                    "proc_nr": 33,
                    "parm_nr": 0,
                    "parm_type": propar.PP_TYPE_FLOAT,
                }
            ]
        )
        self.p_a = float(f"{values_p_a[0]['data']: .2f}")
        values_p_b = self.mfc_master.read_parameters(
            [
                {
                    "node": 14,
                    "proc_nr": 33,
                    "parm_nr": 0,
                    "parm_type": propar.PP_TYPE_FLOAT,
                }
            ]
        )
        self.p_b = float(f"{values_p_b[0]['data']: .2f}")
        if verbose is True:
            print(
                f"Pressure in Line A = {self.p_a} psia\nPressure in Line B = {self.p_b} psia"
            )
        return self.p_a, self.p_b

    # ███████╗██╗   ██╗██████╗  ██████╗ ████████╗██╗  ██╗███████╗██████╗ ███╗   ███╗
    # ██╔════╝██║   ██║██╔══██╗██╔═══██╗╚══██╔══╝██║  ██║██╔════╝██╔══██╗████╗ ████║
    # █████╗  ██║   ██║██████╔╝██║   ██║   ██║   ███████║█████╗  ██████╔╝██╔████╔██║
    # ██╔══╝  ██║   ██║██╔══██╗██║   ██║   ██║   ██╔══██║██╔══╝  ██╔══██╗██║╚██╔╝██║
    # ███████╗╚██████╔╝██║  ██║╚██████╔╝   ██║   ██║  ██║███████╗██║  ██║██║ ╚═╝ ██║
    # ╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝


if __name__ == "__main__":
    gc = GasControl()
    gc.cont_mode_A()
    gc.valves.display_valve_positions()

    gc.flowsms_setpoints(
        Ar_A=15,
        Ar_B=15,
    )

    gc.flowsms_status()
