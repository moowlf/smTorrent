import dataclasses
import math
import threading
import time
import socket
import requests

from typing import List
from bencode import bencode
from hashlib import sha1
from torrent import connection
from queue import Queue

from torrent.TorrentInformation import TorrentInformation


@dataclasses.dataclass
class BlockPiece:
    piece_id: int
    block_id: int
    block_size: int
    data: []


@dataclasses.dataclass
class Piece:
    piece_id: int
    hash: bytearray
    blocks: List[BlockPiece]


class Torrent:

    def __init__(self, file_data):
        self._peers = Queue()
        self._metadata: TorrentInformation = file_data
        self._metadata_infoHash = self._calculate_encoded_info_hash()

        self._pieces = [self._metadata.pieces[i:i + 20] for i in range(0, len(self._metadata.pieces), 20)]
        self.data = []

        # Prepare all pieces to be downloaded for this torrent
        self.pieces_to_download = self._divide_into_blocks()

    def download(self, own_peer_id: str, threads=1):
        # Start thread responsible for communicating with tracker
        tracker_comm = threading.Thread(target=self._get_peers, args=(own_peer_id,))
        tracker_comm.start()

        # Start threads responsible for downloading the pieces
        workers = [threading.Thread(target=self._download_from_peer, args=(own_peer_id,)) for _ in range(threads)]
        [worker.start() for worker in workers]

        # End threads
        tracker_comm.join()
        [worker.join() for worker in workers]

        with open(self._metadata.file_name, "wb") as file:
            self.data.sort(key=lambda x: x[0])
            for piece in self.data:
                file.write(piece[1])

    def _get_peers(self, own_peer_id: str):

        while not self.pieces_to_download.empty():
            # Query the tracker
            params = connection.build_peer_request(self._metadata_infoHash, own_peer_id)
            req = requests.get(self._metadata.announce_url, params)

            # Decode the answer and wait for next call
            answer = bencode.decode_dictionary(req.content)[0]

            for peer in answer["peers"]:
                self._peers.put({"ip": peer["ip"].decode(), "port": peer["port"]})

            # Sleep
            # time.sleep(answer["interval"])
            time.sleep(5)

    def _download_from_peer(self, own_peer_id: str):

        while not self.pieces_to_download.empty():
            # Retrieve piece to be downloaded
            piece_to_download: Piece = self.pieces_to_download.get()

            # Retrieve IP to connect (assuming every IP has all files)
            peer = self._peers.get()
            peer_ip, peer_port = peer["ip"], peer["port"]

            # Start the connection with chosen peer
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((peer_ip, peer_port))

            # Send Handshake and receive
            handshake = connection.build_handshake(self._metadata_infoHash, own_peer_id)
            conn.send(handshake)
            _ = self._receive_data(conn, 256)

            # Send interested
            interested = connection.build_interested()
            conn.send(interested)

            # From here onwards, we can receive some messages "out of order".
            current_state = "chocked"

            for block_piece in piece_to_download.blocks:
                block_piece.data, current_state = self._download_state_machine(conn, block_piece, current_state)

            data = piece_to_download.blocks[0].data + piece_to_download.blocks[1].data
            res = sha1(data)

            if piece_to_download.hash.hex() != res.hexdigest():
                self.pieces_to_download.put(piece_to_download)

            self.data.append([piece_to_download.piece_id, data])

        return

    def _calculate_encoded_info_hash(self):
        info = {
            "length": self._metadata.file_length,
            "name": self._metadata.file_name,
            "piece length": self._metadata.file_piece_length,
            "pieces": self._metadata.pieces
        }

        return sha1(bencode.encode_dictionary(info)).digest()

    def _divide_into_blocks(self) -> Queue:
        """
        It takes the all pieces from the file and divide them into blocks of size up to 16KB
        :return: A Queue with all the pieces and information needed to request them
        """
        q = Queue()

        total_file_left = self._metadata.file_length
        piece_id = 0

        while total_file_left > 0:
            # We now have a piece to deal with. A piece will be divided into multiple blocks of a specified length by
            # the tracker
            piece = Piece(piece_id=piece_id, hash=self._pieces[piece_id], blocks=[])
            piece_size = min(self._metadata.file_piece_length, total_file_left)
            total_file_left -= piece_size

            # Split into blocks
            blocks_size = 0
            block_id = 0

            while blocks_size < piece_size:
                current_block_size = min(2 ** 14, piece_size - blocks_size)
                piece.blocks.append(
                    BlockPiece(piece_id=piece_id, block_id=block_id, block_size=current_block_size, data=b""))
                blocks_size += current_block_size
                block_id += 1

            # Update piece id
            piece_id += 1

            # Add to queue
            q.put(piece)

        return q

    @staticmethod
    def _receive_data(connection_socket, size_buffer):
        answer = bytearray()
        while True:
            downloaded_buffer = connection_socket.recv(size_buffer)
            answer += downloaded_buffer

            if len(downloaded_buffer) < size_buffer:
                break

        return answer

    @staticmethod
    def _download_state_machine(conn, block_piece: BlockPiece, current_state):

        # Prepare the blocks to be downloaded
        block_length = 2 ** 14

        # Specific Request
        piece = block_piece.piece_id
        offset = block_piece.block_id * block_length
        size = block_piece.block_size

        data = connection.build_request_piece(piece, offset, size)
        already_request_piece = False

        while True:

            if not already_request_piece and current_state == "unchocked":
                already_request_piece = True
                conn.send(data)
            time.sleep(2)

            answer = Torrent._receive_data(conn, block_length)
            _, bitfield, payload = connection.parse_peer_message(answer)

            # Keep alive message
            if _ == 0:
                print("received keep alive")
                continue

            # Chocked message
            if bitfield == 0:
                print("received chocked message")
                current_state = "chocked"
            elif bitfield == 1:
                print("received unchocked message")
                current_state = "unchocked"
            elif bitfield == 2:
                print("received interested message")
            elif bitfield == 3:
                print("received not interested message")
            elif bitfield == 4:
                print("received have message")
            elif bitfield == 5:
                print("received bitfield message")
                # Send that we're interested in this piece
                conn.send(connection.build_interested())
                continue
            elif bitfield == 6:
                print("received request message")

            elif bitfield == 7:
                print("received pieces message")
                i, b, bl = connection.parse_piece(payload)
                return bl, current_state

            elif bitfield == 8:
                print("received cancel message")

        return b"", current_state
