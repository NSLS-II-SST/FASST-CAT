import socket
import time


class SerialTCP:
    def __init__(self, address, port, read_timeout=1, max_retries=3, retry_delay=1, verbose=False):
        self.address = address
        self.port = port
        self.out_terminator = "\r"
        self._read_timeout = read_timeout
        self._last_read = b""
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._sock = None  # Keep a persistent socket
        self.verbose = verbose

    def _log(self, message):
        """Log a message if verbose is enabled."""
        if self.verbose:
            print(message)

    def open_socket(self):
        """Open a persistent socket connection."""
        try:
            self._sock = socket.create_connection((self.address, self.port), timeout=self._read_timeout)
            self._log("Socket connected.")
        except Exception as e:
            self._log(f"Failed to connect: {e}")
            self._sock = None

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
            response = self._sock.recv(1024)
            self._last_read += response
            self._log(f"Received data: {response}")
        except socket.timeout:
            self._log("Read timeout occurred.")
        except Exception as e:
            self._log(f"Error during read: {e}")

    def read(self, size=1):
        """Return the last read data."""
        response = self._last_read[:size]
        self._last_read = self._last_read[size:]
        return response

    def write(self, data):
        """Write data to the socket."""
        if not self._sock:
            raise ConnectionError("Socket is not connected.")

        for attempt in range(self.max_retries):
            try:
                self._log(f"Attempting to write data: {data}")
                self._sock.sendall(data)
                self._read()  # Immediately read response
                self._log("Write successful.")
                break  # Exit loop if successful
            except (socket.error, BrokenPipeError) as e:
                self._log(f"Write attempt {attempt + 1} failed: {e}")
                time.sleep(self.retry_delay)
                if attempt < self.max_retries - 1:
                    self._log("Retrying...")
                    self.open_socket()  # Reconnect and retry
                else:
                    raise ConnectionError("Failed to write after multiple retries.")

    @property
    def in_waiting(self):
        """Return the number of bytes available for reading."""
        return len(self._last_read)
