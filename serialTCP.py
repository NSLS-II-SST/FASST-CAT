import socket
import time

class SerialTCP:
    def __init__(self, address, port, timeout=None, write_timeout=None, read_timeout=1, max_retries=3, retry_delay=1, verbose=False):
        """
        Initializes the SerialTCP class with the necessary parameters.
        
        :param address: Hostname or IP address of the TCP server.
        :param port: Port number of the TCP server.
        :param timeout: General timeout for socket connection (default is None).
        :param write_timeout: Timeout for writing to the socket (default is None).
        :param read_timeout: Timeout for reading from the socket (default is 1 second).
        :param max_retries: Maximum number of retry attempts for write operations (default is 3).
        :param retry_delay: Delay between retry attempts (default is 1 second).
        :param verbose: If True, logs will be printed for each action (default is False).
        """
        self.address = address
        self.port = port
        self.timeout = timeout
        self.write_timeout = write_timeout
        self._read_timeout = read_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._sock = None  # Persistent socket
        self.verbose = verbose
        self._last_read = b""

    def _log(self, message):
        """Log a message if verbose is enabled."""
        if self.verbose:
            print(message)

    def open_socket(self):
        """Open a persistent socket connection."""
        try:
            self._sock = socket.create_connection((self.address, self.port), timeout=self.timeout)
            self._log(f"Socket connected to {self.address}:{self.port}.")
        except (socket.timeout, socket.error) as e:
            self._log(f"Failed to connect: {e}")
            self._sock = None
            raise ConnectionError(f"Could not connect to {self.address}:{self.port}. Error: {e}")

    def close_socket(self):
        """Close the socket if it is open."""
        if self._sock:
            try:
                self._sock.close()
                self._log("Socket closed.")
            except Exception as e:
                self._log(f"Error closing socket: {e}")
            finally:
                self._sock = None

    def _read(self):
        """Read data from the socket."""
        if not self._sock:
            raise ConnectionError("Socket is not connected.")

        try:
            self._sock.settimeout(self._read_timeout)
            response = self._sock.recv(1024)  # Reading up to 1024 bytes
            if response:
                self._last_read += response
                self._log(f"Received data: {response}")
            else:
                self._log("No data received.")
        except socket.timeout:
            self._log("Read timeout occurred.")
        except Exception as e:
            self._log(f"Error during read: {e}")

    def read(self, size=1):
        """Return the last read data."""
        response = self._last_read[:size]
        self._last_read = self._last_read[size:]  # Remove the read portion from the buffer
        return response

    def write(self, data):
        """Write data to the socket with retry functionality."""
        if not self._sock:
            raise ConnectionError("Socket is not connected.")

        for attempt in range(self.max_retries):
            try:
                self._log(f"Attempting to write data: {data}")
                self._sock.settimeout(self.write_timeout)  # Set write timeout
                self._sock.sendall(data)
                self._log("Write successful.")
                self._read()  # Immediately read response after writing
                break  # Exit loop if successful
            except (socket.error, BrokenPipeError) as e:
                self._log(f"Write attempt {attempt + 1} failed: {e}")
                time.sleep(self.retry_delay)
                if attempt < self.max_retries - 1:
                    self._log("Retrying...")
                    self.open_socket()  # Reconnect and retry if retries are left
                else:
                    self._log("Max retries reached, raising ConnectionError.")
                    raise ConnectionError("Failed to write after multiple retries.")

    @property
    def in_waiting(self):
        """Return the number of bytes available for reading."""
        return len(self._last_read)
