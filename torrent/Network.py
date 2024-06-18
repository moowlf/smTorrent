
import socket

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


def send_data(conn, data):

    bytes_to_send = len(data)
    sent = 0

    while sent < bytes_to_send:
        sent += conn.send(data[sent:])


def receive_data(conn, buffer_size=None):
    # We know the size is enough
    if buffer_size is not None:
        downloaded_buffer = conn.recv(buffer_size)
        return downloaded_buffer

    # the size comes in the first 4 bytes
    answer = conn.recv(1024)
    size = int.from_bytes(answer[:4], byteorder='big')

    while len(answer) < size:
        answer += conn.recv(2 ** 14)

    return answer
