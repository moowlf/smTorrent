
def parse_peer_message(message: bytes):
    length = message[0:4]
    bitfield = message[4:5]
    payload = message[5:]

    return int.from_bytes(length, "big"), int.from_bytes(bitfield, "big"), payload


def parse_piece(message: bytes):

    index = message[0:4]
    begin = message[4:8]
    block = message[8:]

    return int.from_bytes(index, "big"), int.from_bytes(begin, "big"), block


def build_peer_request(info_hash: bytes, peer_id: str):
    return {
        'info_hash': info_hash,
        'peer_id': peer_id,
        'port': 1111,
        'uploaded': 0,
        'downloaded': 0,
        'left': 1000,
        "event": "started"
    }


def build_request_piece(current_piece_id, piece_offset, size):
    data = bytearray()
    data += (17).to_bytes(4, "big")
    data += (6).to_bytes(1, "big")
    data += current_piece_id.to_bytes(4, "big")
    data += (piece_offset).to_bytes(4, "big")
    data += size.to_bytes(4, "big")
    return data


def build_handshake(info_hash: bytes, peer_id: str):
    data = bytearray()
    data += len(b"BitTorrent protocol").to_bytes(1, "big")
    data += b"BitTorrent protocol"
    data += bytearray(8)
    data += info_hash
    data += peer_id.encode()

    return data


def build_choke():
    return (0).to_bytes()


def build_unchoke():
    return (1).to_bytes()


def build_interested():
    return (4).to_bytes(4, "big") + (2).to_bytes(1, "big")


def build_not_interested():
    return (3).to_bytes()
