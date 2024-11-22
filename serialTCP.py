import socket


class SerialTCP:
    def __init__(self, address, port, **kwargs):
        # Initialize the port, port and baudrate can be controlled
        # in instrument and master initialization.
        print(address, port)
        self.address = address
        self.port = port
        self.out_terminator = "\r"
        self._read_timeout = 1
        self._last_read = b""

    def close(self):
        # Close the port
        print("close")

    def open(self):
        # Open the port
        print("open")

    def open_socket(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.address, self.port))
            # print("Socket connected.")
            return sock
            # Send a dummy status check to clear any initial data
            # self.send_command('-xStatus')  # Ignore the first response
        except Exception as e:
            print(f"Failed to connect: {e}")
            return None

    def close_socket(self, sock):
        if sock:
            sock.close()
            # print("Socket closed.")

    def _read(self, sock):
        # print("Reading from socket")
        sock.settimeout(1)
        try:
            response = sock.recv(1024)
            # print(f"Got response: {response}")
            self._last_read += response
            sock.close()
        except BlockingIOError:
            sock.close()

    def read(self, size=1):
        # Read data from port, return bytes object
        # print("Reading")
        response = self._last_read
        self._last_read = b""
        # print(response)
        return response

    def write(self, data):
        # print(f"Writing {data}")
        sock = self.open_socket()
        sock.sendall(data)
        # t = threading.Thread(target=self._read, args=[sock])
        # t.start()
        self._read(sock)
        # Write data to port, bytes object as input

    @property
    def in_waiting(self):
        # Return number of bytes available for reading
        return len(self._last_read)
