
import socket

class Network:

    def __init__(self) -> None:
        self.data = b""
        self._downloaded = 0
        self._uploaded = 0

    def get_socket(ip_address):
        # Determine if the IP address is IPv4 or IPv6
        try:
            socket.inet_pton(socket.AF_INET, ip_address)
            family = socket.AF_INET
        except socket.error:
            try:
                socket.inet_pton(socket.AF_INET6, ip_address)
                family = socket.AF_INET6
            except socket.error:
                raise ValueError("Invalid IP address")

        return socket.socket(family, socket.SOCK_STREAM)

    def receive_data(self, conn):

        while len(self.data) < 4:
            self.data += self._recv_data(conn)
        
        size = int.from_bytes(self.data[:4], byteorder='big')

        while len(self.data) < size:
            self.data += self._recv_data(conn)
        
        message = self.data[:4 + size]
        self.data = self.data[4 + size:]
        return message

    def receive_data_with_length(self, conn, length):

        while len(self.data) < length:
            self.data += self._recv_data(conn)
        
        message = self.data[:length]
        self.data = self.data[length:]
        return message


    def _recv_data(self, conn):

        tmp =  conn.recv(2**14)
        if len(tmp) == 0:
            raise ConnectionError("Connection was closed")
        
        self._downloaded += len(tmp)
        return tmp

    def send_data(self, conn, data):

        bytes_to_send = len(data)
        self._uploaded += bytes_to_send
        
        sent = 0
        while sent < bytes_to_send:
            sent += conn.send(data[sent:])

    def downloaded(self):
        return self._downloaded

    def uploaded(self):
        return self._uploaded
