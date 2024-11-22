"""Valves, temperature, and Mass flow control module

__author__ = "Jorge Moncada Vivas"
__version__ = "3.0"
__email__ = "moncadaja@gmail.com"
__date__ = "10/24/2024"

Notes:
By Jorge Moncada Vivas and contributions of Ryuichi Shimogawa
"""

import time
import logging


import json

from valves import create_valves
from eurothermSerial import EuroSerial
from eurothermTCP import EuroTCP
from flowSMS import FlowSMS
from utils import convert_com_port


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# ███████╗ █████╗ ███████╗███████╗████████╗ ██████╗ █████╗ ████████╗
# ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔════╝██╔══██╗╚══██╔══╝
# █████╗  ███████║███████╗███████╗   ██║   ██║     ███████║   ██║
# ██╔══╝  ██╔══██║╚════██║╚════██║   ██║   ██║     ██╔══██║   ██║
# ██║     ██║  ██║███████║███████║   ██║   ╚██████╗██║  ██║   ██║
# ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝    ╚═════╝╚═╝  ╚═╝   ╚═╝


def create_eurotherm(config, flowSMS):
    if "HOST_EURO" in config and "PORT_EURO" in config:
        return EuroTCP(config["HOST_EURO"], config["PORT_EURO"], flowSMS)
    else:
        euro_comport = convert_com_port(config["COM_TMP"])
        euro_sub = config["SUB_ADD_TMP"]
        return EuroSerial(euro_comport, euro_sub, flowSMS)


class GasControl:
    def __init__(self, config_file="config.json") -> None:
        """Initialize the gas control system.

        Args:
            config_file (str): Path to configuration file [default: "config.json"]
        """
        with open(config_file, "r") as file:
            config = json.load(file)
        self.config = config

        self.valves = create_valves(config)
        self.flowSMS = FlowSMS(config, self.valves)
        self.eurotherm = create_eurotherm(config, self.flowSMS)

    # ██╗   ██╗ █████╗ ██╗    ██╗   ██╗███████╗███████╗
    # ██║   ██║██╔══██╗██║    ██║   ██║██╔════╝██╔════╝
    # ██║   ██║███████║██║    ██║   ██║█████╗  ███████╗
    # ╚██╗ ██╔╝██╔══██║██║    ╚██╗ ██╔╝██╔══╝  ╚════██║
    #  ╚████╔╝ ██║  ██║███████╗╚████╔╝ ███████╗███████║
    #   ╚═══╝  ╚═╝  ╚═╝╚══════╝ ╚═══╝  ╚══════╝╚══════╝

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


if __name__ == "__main__":
    gc = GasControl()
    gc.cont_mode_A()
    gc.valves.display_valve_positions()

    gc.flowSMS.setpoints(
        Ar_A=15,
        Ar_B=15,
    )

    gc.flowSMS.status()
