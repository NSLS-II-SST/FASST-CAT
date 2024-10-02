import socket
import threading
import time
import matplotlib.pyplot as plt
import numpy as np

class HidenHPR20Interface:
    def __init__(self, host='localhost', port=5026):
        self.host = host
        self.port = port
        self.sock = None
        self.data_sock = None
        self.file_path = None
        self.x_data = []
        self.y_data = []
        plt.ion()

    # Establish a socket connection
    def create_socket_connection(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print("Socket connected.")
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.sock = None

    # Send a command through the socket
    def send_command(self, command):
        try:
            self.sock.sendall(command.encode() + b'\n')
            response = self.sock.recv(1024).decode().strip()
            return response
        except Exception as e:
            print(f"Failed to send command: {e}")
            return None

    # Open the file and run the experiment
    def open_file_and_run(self, file_path):
        self.file_path = file_path
        if self.sock:
            response = self.send_command(f'-f "{self.file_path}" -d20')
            print(f"File Open Response: {response}")
            if response == '1':  # File opened successfully
                response = self.send_command('-xGo -odt -d20')
                print(f"Run File Response: {response}")
            else:
                print("Failed to open file.")
        else:
            print("Socket not connected.")

    # Close the experiment file
    def close_file(self):
        if self.sock:
            response = self.send_command('-xClose -d20')
            print(f"Close File Response: {response}")
        else:
            print("Socket not connected.")

    # Monitor the status of the MSIU
    def monitor_status(self):
        status_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            status_sock.connect((self.host, self.port))
            response = self.send_command(f'-f "{self.file_path}" -d20')
            print(f"Status Socket File Association: {response}")
            response = self.send_command('-lStatus -v1 -d20')
            print(f"Status Hotlink Response: {response}")

            while True:
                status = status_sock.recv(1024).decode().strip()
                if status:
                    print(f"Status: {status}")
                    if "StoppedShutdown" in status:
                        break  # Experiment stopped, exit loop
        except Exception as e:
            print(f"Failed to monitor status: {e}")
        finally:
            status_sock.close()

    # Real-time data retrieval in a separate thread
    def data_thread(self):
        self.data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.data_sock.connect((self.host, self.port))
            print("Data socket connected.")
        except Exception as e:
            print(f"Failed to connect data socket: {e}")
            return

        if self.file_path:
            # Associate the socket with the open file
            response = self.send_command(f'-f "{self.file_path}" -d20')
            print(f"Data Thread File Association: {response}")
            
            # Create a data hotlink
            response = self.send_command('-lData -v1 -d20')
            print(f"Data Hotlink Response: {response}")
            
            # Continuously receive data
            while True:
                try:
                    data = self.data_sock.recv(1024).decode().strip()
                    if data:
                        print(f"Data: {data}")
                        self.update_plot(data)
                except:
                    break
        self.data_sock.close()

    # Start the data thread to retrieve data in real-time
    def start_data_thread(self):
        data_thread = threading.Thread(target=self.data_thread)
        data_thread.start()

    # Update the plot in real-time
    def update_plot(self, new_data):
        self.x_data.append(time.time())  # Assuming time as x-axis
        self.y_data.append(float(new_data))  # New data for y-axis
        
        plt.clf()  # Clear the current figure
        plt.plot(self.x_data, self.y_data)
        plt.pause(0.05)  # Pause to allow the plot to update

    # Get the current filename associated with the socket
    def get_filename(self):
        if self.sock:
            response = self.send_command('-xFilename')
            print(f"Current Filename: {response}")
        else:
            print("Socket not connected.")

    # Set a logical device value using LSet command
    def set_logical_device(self, device_name, value):
        if self.sock:
            command = f'-xLSet {device_name} {value} -v1'
            response = self.send_command(command)
            print(f"Logical Device Set Response: {response}")
        else:
            print("Socket not connected.")

    # Export the acquired data
    def export_data(self, view=1):
        if self.sock:
            command = f'-xExport -v{view}'
            response = self.send_command(command)
            print(f"Data Export Response: {response}")
        else:
            print("Socket not connected.")

    # Close the main socket connection
    def close_socket(self):
        if self.sock:
            self.sock.close()
            print("Socket closed.")
        if self.data_sock:
            self.data_sock.close()
            print("Data socket closed.")

# Example usage
if __name__ == "__main__":
    # Initialize the interface
    hiden_interface = HidenHPR20Interface()

    # Establish the connection
    hiden_interface.create_socket_connection()

    # Open the file and run the experiment
    hiden_interface.open_file_and_run(r'C:\Data Files\Hiden Analytical\MASsoft11\SocketTemplate\MID-Ar-He-Trend.exp')

    # Start retrieving data in real-time
    hiden_interface.start_data_thread()

    # Monitor status in a separate thread
    threading.Thread(target=hiden_interface.monitor_status).start()

    # Simulate for 60 seconds (replace with actual experiment duration)
    time.sleep(60)

    # Export the data from view 1
    hiden_interface.export_data(view=1)

    # Get the current filename
    hiden_interface.get_filename()

    # Close the file and socket when done
    hiden_interface.close_file()
    hiden_interface.close_socket()
