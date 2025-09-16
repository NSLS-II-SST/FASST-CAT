import time
import socket
import serial
from abc import ABC, abstractmethod
from .utils import convert_com_port


class ValvesBase(ABC):
    """Base class for valve control implementing common valve logic.

    Communication is abstracted through read/write methods that must be
    implemented by subclasses.
    """

    def __init__(self, gas_config, out_terminator="\r"):
        """Initialize the valve controller.

        Args:
            out_terminator (str): Command termination character [default: "\r"]
        """
        self.out_terminator = out_terminator
        self.gas_config = gas_config

    @abstractmethod
    def write(self, command: str) -> None:
        """Write a command to the valve controller.

        Args:
            command (str): Command to send
        """
        pass

    @abstractmethod
    def read(self) -> str:
        """Read response from the valve controller.

        Returns:
            str: Response from the valve controller
        """
        pass

    def get_valve_position(self, valve):
        """Get the current position of a valve.

        Args:
            valve (str): Valve identifier (A-I)

        Returns:
            tuple: (valve_number, position_str)
        """
        self.write(f"/{valve}CP")
        time.sleep(0.01)
        current_position = self.read()
        valve_no = current_position[1]
        position = current_position[-2]
        if position == "A":
            return valve_no, "OFF"
        elif position == "B":
            return valve_no, "ON"
        else:
            return valve_no, "Unknown"

    def display_valve_positions(self, valve=None):
        """Display positions of all valves or a specific valve.

        Args:
            valve (str, optional): Specific valve to display
        """
        if valve:
            valve_no, position = self.get_valve_position(valve)
            print(f"Valve {valve_no} position is {position}")
        else:
            valves = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
            for v in valves:
                valve_no, position = self.get_valve_position(v)
                print(f"Valve {valve_no} position is {position}")

    def move_valve_to_position(self, valve, position):
        """Move a valve to the specified position.

        Args:
            valve (str): Valve identifier (A-I)
            position (str): Target position ("ON" or "OFF")
        """
        if position == "ON":
            command = "CC"
        elif position == "OFF":
            command = "CW"
        else:
            print("Invalid position specified.")
            return

        self.write(f"/{valve}{command}")
        time.sleep(0.3)

        # Verify position
        self.write(f"/{valve}CP")
        new_position = self.read()[-2]
        expected_position = "B" if position == "ON" else "A"

        if new_position != expected_position:
            self.write(f"/{valve}{command}")

    def valve_actuation_message(self, valve, message=None):
        """Set valve actuation message mode.

        Args:
            valve (str): Valve identifier (A-I)
            message (str, optional): Message mode ("no message", "short", "large")
        """
        if message == "no message":
            self.write(f"/{valve}IFM0")
        elif message == "short":
            self.write(f"/{valve}IFM1")
        elif message == "large":
            self.write(f"/{valve}IFM2")
        else:
            self.write(f"/{valve}IFM")

    def commands_list(self, valve):
        """Get list of available commands for a valve.

        Args:
            valve (str): Valve identifier (A-I)
        """
        self.write(f"/{valve}?")
        return self.read()

    def toggle_valve_position(self, valve):
        """Toggle the position of a valve.

        Args:
            valve (str): Valve identifier (A-I)
        """
        self.write(f"/{valve}TO")
        time.sleep(0.3)
        return self.read()

    def valve_controller_settings(self, valve):
        """Get controller settings for a valve.

        Args:
            valve (str): Valve identifier (A-I)
        """
        self.write(f"/{valve}STAT")
        return self.read()

    def valve_actuation_time(self, valve):
        """Get actuation time for a valve.

        Args:
            valve (str): Valve identifier (A-I)
        """
        self.write(f"/{valve}TM")
        return self.read()

    def valve_number_ports(self, valve):
        """Get number of ports for a valve.

        Args:
            valve (str): Valve identifier (A-I)
        """
        self.write(f"/{valve}NP")
        return self.read()

    def feed_gas(self, gas_name: str) -> None:
        """Set valve positions to feed specified gas.

        Args:
            gas_name (str): Name of gas to feed (must match config file)
        """
        if gas_name not in self.gas_config:
            raise ValueError(f"Unknown gas: {gas_name}")

        gas_settings = self.gas_config[gas_name]
        if "valve_settings" not in gas_settings:
            raise ValueError(f"No valve settings defined for gas: {gas_name}")

        # Apply all valve settings for this gas
        valve, position = gas_settings["valve_settings"]
        self.move_valve_to_position(valve, position)

        print(f"Feeding {gas_name}")


class SerialValves(ValvesBase):
    """Valve control over serial connection."""

    def __init__(self, gas_config, port, baudrate=9600, **kwargs):
        """Initialize serial connection to valve controller.

        Args:
            port (str): Serial port
            baudrate (int): Baud rate [default: 9600]
            **kwargs: Additional arguments passed to ValvesBase
        """
        super().__init__(gas_config, **kwargs)
        self.ser = serial.Serial()
        self.ser.baudrate = baudrate
        self.ser.port = port
        self.ser.timeout = 0.1
        self.connect()

    def connect(self):
        """Establish serial connection."""
        if not self.ser.is_open:
            self.ser.open()
        else:
            print(f"The Port is closed: {self.ser.portstr}")

    def write(self, command):
        """Write command over serial connection."""
        self.ser.write(f"{command}{self.out_terminator}".encode())

    def read(self):
        """Read response from serial connection."""
        return self.ser.readline().decode("utf-8").strip()


class EthernetValves(ValvesBase):
    """Valve control over Ethernet connection."""

    def __init__(self, gas_config, host, port, **kwargs):
        """Initialize Ethernet connection to valve controller.

        Args:
            host (str): Host address
            port (int): Port number
            **kwargs: Additional arguments passed to ValvesBase
        """
        super().__init__(gas_config, **kwargs)
        self.host = host
        self.port = port
        self.sock = None

    def get_read_socket(self):
        if not self.sock:
            return self.sock
        try:
            self.sock.getpeername()
            self.sock.settimeout(1.0)
        except Exception as e:
            print(f"Socket not open or connected: {e}")
            self.sock = None
            return self.sock
        if self.sock._closed:
            self.sock = None
            return self.sock
        return self.sock

    def get_write_socket(self):
        sock = self.get_read_socket()
        if not sock:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            self.sock = sock
        self.sock.settimeout(10)
        return self.sock

    def write(self, command):
        """Write command over Ethernet connection. Returns number of bits written"""
        sock = self.get_write_socket()
        try:
            return sock.sendall(f"{command}{self.out_terminator}".encode())
        except Exception as e:
            print(f"Failed to send command: {e}")
            self.sock = None
            if sock:
                sock.close()
            return 0

    def read(self):
        """Read response from Ethernet connection."""
        sock = self.get_read_socket()
        if sock:
            try:
                response = sock.recv(4096).decode().strip()
            except TimeoutError:
                response = ""
        else:
            response = ""
        return response


def create_valves(io_config, gas_config):
    """Factory function to create appropriate valve controller instance.

    Args:
        config (dict): Configuration dictionary

    Returns:
        ValvesBase: Configured valve controller instance
    """
    if "HOST_MOXA" not in io_config or "PORT_VALVES" not in io_config:
        port = convert_com_port(io_config["COM_VALVE"])
        return SerialValves(gas_config, port=port)
    else:
        return EthernetValves(
            gas_config, host=io_config["HOST_MOXA"], port=io_config["PORT_VALVES"]
        )
