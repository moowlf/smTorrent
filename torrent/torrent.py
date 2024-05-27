import dataclasses
import math
import threading
import time

import requests
from bencode import bencode
from hashlib import sha1
import socket
from torrent import connection
from queue import Queue

from torrent.TorrentInformation import TorrentInformation


@dataclasses.dataclass
class BlockPiece:
    piece_id: int
    block_id: int
    block_size: int


class Torrent:

    def __init__(self, file_data):
        self._peers = Queue()
        self._pieces = []
        self._metadata: TorrentInformation = file_data
        self._metadata_infoHash = self._calculate_encoded_info_hash()

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
            for piece in self._pieces:
                file.write(piece)

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

        # Prepare the blocks to be downloaded
        block_length = 2 ** 14

        while not self.pieces_to_download.empty():

            if self._peers.empty():
                continue

            # Retrieve the piece to download
            piece_to_download: BlockPiece = self.pieces_to_download.get()

            # Get the peer IP
            peer = self._peers.get()
            peer_ip, peer_port = peer["ip"], peer["port"]

            # Start the connection with chosen peer
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((peer_ip, peer_port))

            # Send Handshake and receive
            handshake = connection.build_handshake(self._metadata_infoHash, own_peer_id)
            conn.send(handshake)
            answer = conn.recv(256)

            # Send that we're interested in this piece
            conn.send(connection.build_interested())

            # From here onwards, we can receive some messages "out of order".
            current_state = "chocked"

            while True:
                
                answer = bytearray()
                while True:
                    part = conn.recv(1024)
                    answer += part
                    if len(part) < 1024:
                        break
                _, bitfield, payload = connection.parse_peer_message(answer)

                # Keep alive message
                if _ == 0:
                    print("received keep alive")

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

                elif bitfield == 6:
                    print("received request message")

                elif bitfield == 7:
                    print("received pieces message")
                    print(len(payload))
                    i, b, bl = connection.parse_piece(payload)
                    self._pieces.append(bl)
                    break

                elif bitfield == 8:
                    print("received cancel message")

                if current_state != "unchocked":
                    continue

                piece = piece_to_download.piece_id
                offset = piece_to_download.block_id * (2 ** 14)
                size = piece_to_download.block_size

                print(f"Downloading {piece} -> {offset} -> {size}")
                data = connection.build_request_piece(piece, offset, size)
                conn.send(data)
                time.sleep(2)

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
            piece_size = min(self._metadata.file_piece_length, total_file_left)
            total_file_left -= piece_size

            # Split into blocks
            blocks_size = 0
            block_id = 0

            while blocks_size < piece_size:
                current_block_size = min(2**14, piece_size - blocks_size)
                q.put(BlockPiece(piece_id=piece_id, block_id=block_id, block_size=current_block_size))
                blocks_size += current_block_size
                block_id += 1

            # Update piece id
            piece_id += 1
            pass

        return q
