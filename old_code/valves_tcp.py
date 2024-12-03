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
import minimalmodbus
from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import encode_ieee, decode_ieee, \
                              long_list_to_word, word_list_to_long

import json
import platform

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class GasControl:
    def __init__(
        self,
        config_file = "config.json"
    ) -> None:
        """Initialize the valve control device
        You can specify the HID or the comport of the valve control device
        It will print the available comports if no comport is specified

        Args:
            valves_hid (str): HID of the valve control device, you can also specify the name or hid of the comport [default: HID_VALVE]
            valves_comport (str): Comport of the valve control device [default: None]
            num_valves (int): Number of valves connected to the valve control device [default: 9]
            mfc_hid (str): HID of the mfc device, you can also specify the name or hid of the comport [default: HID_MFC]
            mfc_comport (str): Comport of the mfc device [default: None]
            tmp_hid (str): HID of the temperature controller device, you can also specify the name or hid of the comport [default: HID_TMP]
            tmp_comport (str): Comport of the temperature controller device [default: None]
        """

        with open(config_file, "r") as file:
            config = json.load(file)

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
        self.out_terminator = "\r"

    def open_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host_moxa, self.port_valves))
            print("Socket connected.")
            # Send a dummy status check to clear any initial data
            # self.send_command('-xStatus')  # Ignore the first response
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.sock = None

    def send_command(self, command):
        self.open_socket()
        try:
            self.sock.sendall((command + self.out_terminator).encode())
            response = self.sock.recv(4096)
            print(f"Raw Response: {response}")  # Print raw response for debugging
            decoded_response = response.decode().strip()
            print(decoded_response)
            split_response = decoded_response.split("\r")
            print(split_response)
            # return decoded_response
        except Exception as e:
            print(f"Failed to send command: {e}")
            return None
        self.close_socket()
        
    def close_socket(self):
        if self.sock:
            self.sock.close()
            print("Socket closed.")
