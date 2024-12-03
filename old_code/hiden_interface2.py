import socket
import time
import re

class RGADriver:
    def __init__(self):
        self.ip_address = "localhost"
        self.port = 5026
        self.out_terminator = "\r"
        self.in_terminator = "\r\n"
        self.mass_max = 5000  # Maximum number of mass values
        self.mass_string_len = 10
        self.val_string_len = 20
    
    def send_command(self, command):
        """Send a command to the RGA and return the response."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.ip_address, self.port))
            s.sendall((command + self.out_terminator).encode())
            response = s.recv(4096).decode()
            time.sleep(1)
            s.sendall((command + self.out_terminator).encode())
            response = s.recv(4096).decode()
            return response.strip(self.in_terminator)

    def get_device_id(self):
        """Retrieve the device ID from the RGA."""
        return self.send_command("pget ID")

    def process_raw_data(self, raw_data):
        """Process raw measurement data."""
        mass_values = []
        value_values = []

        # Split the input data into mass and value pairs
        matches = re.findall(r'(\d+\.\d+):\s*([\d\.\-E]+)', raw_data)

        if matches:
            for match in matches:
                mass_values.append(float(match[0]))
                value = float(match[1])
                if value < 0:
                    value = 0  # Filter out negative values
                value_values.append(value)

        return mass_values, value_values

    def start_measurement_cycle(self):
        """Starts a measurement cycle and processes the data."""
        raw_data = self.send_command("data all")  # Example command to get measurement data
        mass_values, value_values = self.process_raw_data(raw_data)

        if len(mass_values) > 0:
            print(f"Processed {len(mass_values)} mass/value pairs:")
            for mass, val in zip(mass_values, value_values):
                print(f"Mass: {mass}, Value: {val:e}")
        else:
            print("No valid data received.")

    def stop_scan(self):
        """Stop the current scan."""
        self.send_command("stop 1 1")
        self.send_command("data stop")
        self.send_command("lset mode 0")

    def shutdown(self):
        """Shutdown the RGA."""
        self.send_command("lset mode 0")


# Example Usage
if __name__ == "__main__":
    rga = RGADriver()

    # Get device ID
    device_id = rga.get_device_id()
    print(f"Device ID: {device_id}")

    # Start measurement and process the data
    # rga.start_measurement_cycle()

    # Stop scan
    # rga.stop_scan()

    # Shutdown
    # rga.shutdown()
