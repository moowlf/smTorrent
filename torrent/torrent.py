import dataclasses
import queue
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
import torrent.Network as Network


@dataclasses.dataclass
class BlockPiece:
    piece_id: int
    block_id: int
    block_size: int
    data: List
    start_position: int


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
        self._to_complete_pieces = self.pieces_to_download.qsize()

        self.file_mutex = threading.Lock()

        # create file
        with open(self._metadata.file_name, "wb") as f:
            f.truncate(self._metadata.file_length)

    def is_complete(self):
        return self._to_complete_pieces == 0

    def download(self, own_peer_id: str, threads=1):
        # Start thread responsible for communicating with tracker
        tracker_comm = threading.Thread(target=self._get_peers, args=(own_peer_id,))
        tracker_comm.start()

        # Start threads responsible for downloading the pieces
        self._download(own_peer_id)

        # End threads
        tracker_comm.join()

    def _download(self, own_peer_id):

        threads = []

        while not self.is_complete():

            """
            Try to retrieve a peer ip
            """
            try:
                peer = self._peers.get(timeout=5)
            except Exception as e:
                continue

            """
            Get the actual work to be done
            """
            try:
                work = self.pieces_to_download.get(timeout=5)
            except queue.Empty:
                self._peers.put(peer)
                continue

            """
            We have reached a valid state for download to start
            """
            threads.append(
                threading.Thread(target=self._download_piece, args=(own_peer_id, peer, work), name=peer["ip"]))
            threads[-1].start()

        [thread.join() for thread in threads]

    def _get_peers(self, own_peer_id: str):

        while not self.is_complete():
            # Query the tracker
            params = connection.build_peer_request(self._metadata_infoHash, own_peer_id)
            req = requests.get(self._metadata.announce_url, params)

            # Decode the answer and wait for next call
            answer = bencode.decode_dictionary(req.content)[0]

            while not self._peers.empty():
                self._peers.get()

            for peer in answer["peers"]:
                self._peers.put({"ip": peer["ip"].decode(), "port": peer["port"]})

            # Sleep
            print(f"Peer request: Waiting for {answer['interval']}s")
            time.sleep(answer["interval"])

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
        current_position = 0

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
                    BlockPiece(piece_id=piece_id, start_position=current_position, block_id=block_id,
                               block_size=current_block_size,
                               data=b""))
                blocks_size += current_block_size
                block_id += 1
                current_position += current_block_size

            # Update piece id
            piece_id += 1

            # Add to queue
            q.put(piece)

        return q

    def _download_piece(self, own_peer_id, peer, piece: Piece):

        # Retrieve IP to connect (assuming every IP has all files)
        peer_ip, peer_port = peer["ip"], peer["port"]

        # Get Connection
        conn = Network.get_socket(peer_ip)
        conn.connect((peer_ip, peer_port))
        print(f"> Connected to {peer_ip}:{peer_port}")

        # Send Handshake and receive
        handshake = connection.build_handshake(self._metadata_infoHash, own_peer_id)
        Network.send_data(conn, handshake)
        _ = Network.receive_data(conn, 256)

        # Send interested
        interested = connection.build_interested()
        Network.send_data(conn, interested)

        # Download Piece
        total_piece = b""
        current_state = "chocked"

        for block_pieces in piece.blocks:

            # Helper variables
            piece_id = block_pieces.piece_id
            piece_offset = block_pieces.block_id * 2 ** 14
            piece_size = block_pieces.block_size

            # Build piece request
            piece_req = connection.build_request_piece(piece_id, piece_offset, piece_size)

            # Completed
            is_completed = False
            requested_piece = False

            while not is_completed:

                if not requested_piece:
                    requested_piece = True
                    Network.send_data(conn, piece_req)
                    continue

                # here all the received messages are prefixed with the length of the message
                # so, we are not passing any buffer size
                received_data = Network.receive_data(conn)
                length, bitfield, payload = connection.parse_peer_message(received_data)

                # Deal with the received data
                if length == 0:
                    continue

                if bitfield == 0:
                    current_state = "chocked"

                elif bitfield == 1:
                    current_state = "unchocked"

                elif bitfield == 5:
                    continue

                elif bitfield == 7:
                    i, b, bl = connection.parse_piece(payload)
                    total_piece += bl
                    break

                else:
                    print(f"Unknown bitfield {bitfield} received")

        # Downloaded all the blocks from the piece
        hash = sha1(total_piece)

        print(hash.hexdigest(), piece.hash.hex())
        if piece.hash.hex() != hash.hexdigest():
            print(f"{peer_ip} : Hashes do not match")
            self.pieces_to_download.put(piece)
            self._peers.put(peer)
            return

        with open(self._metadata.file_name, "r+b") as file:

            self.file_mutex.acquire()
            try:
                for bl in piece.blocks:
                    file.seek(bl.start_position)
                    file.write(bl.data)
            finally:
                self.file_mutex.release()

        self._peers.put(peer)
        self._to_complete_pieces -= 1
        conn.close()
