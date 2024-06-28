import logging
import threading

from torrent.PeerManager import PeerManager
from torrent.FileManager import FileManager
from torrent.PieceManager import PieceManager

from hashlib import sha1
from torrent import Connection, Network


class Torrent:
    def __init__(self, file_data):
        self._metadata = file_data

        # Should end the download
        self._should_end = False

        # Network data
        self._network = Network.Network()

        # Prepare all pieces to be downloaded for this torrent
        self._pieces = PieceManager(self._metadata)

        # Prepare the FileManager
        self._file_manager = FileManager(self._metadata)

        # Prepare tracker manager
        self._peer_manager = PeerManager(self._metadata)

    def download(self, own_peer_id: str):
        # Start thread responsible for communicating with tracker
        self._peer_manager.start(own_peer_id)

        # Start threads responsible for downloading the pieces
        self._download(own_peer_id)

        # End threads
        self._peer_manager.terminate()
        self._peer_manager.wait_to_close()

    def _download(self, own_peer_id):
        threads = []

        while not self._pieces.download_complete() and not self._should_end:
            """
            Try to retrieve a peer ip
            """
            peer = self._peer_manager.get_peer()
            if peer is None:
                continue

            peer_ip, peer_port = peer.split(":")

            """
            We have reached a valid state for download to start
            """
            threads.append(
                threading.Thread(
                    target=self._download_piece,
                    args=(own_peer_id, peer_ip, peer_port),
                    name=peer_ip,
                )
            )
            threads[-1].start()
            break # TODO(DELETE AFTER TEST)

        [thread.join() for thread in threads]

    def _download_piece(self, own_peer_id, peer_ip, peer_port):
        piece_to_download = None

        try:
            # Get Connection
            conn = Network.Network.get_socket(peer_ip)
            conn.connect((peer_ip, int(peer_port)))
            logging.log(logging.INFO, f"Connected to {peer_ip}:{peer_port}")

            # Send Handshake and receive
            handshake = Connection.build_handshake(self._metadata.info_hash(), own_peer_id)
            self._network.send_data(conn, handshake)
            _ = self._network.receive_data_with_length(conn, len(handshake))
            logging.log(logging.INFO, "Handshake sent and received")

            # Send interested
            interested = Connection.build_interested()
            self._network.send_data(conn, interested)
            logging.log(logging.INFO, "Interested sent")

            # Receive bitfield
            received_data = self._network.receive_data(conn)
            _, bitfield, payload = Connection.parse_peer_message(received_data)
            logging.log(logging.INFO, f"Received bitfield {bitfield == 5}")
            bitfield = list(bin(int(payload.hex(), base=16))[2:]) if bitfield == 5 else []
            
            if len(bitfield) == 0:
                logging.log(logging.INFO, "Peer has no pieces. Leaving them")
                conn.close()
                return

            current_state = "chocked"

            # Try to download a piece the user has and we don't
            while True:

                # Get a piece to download
                piece_to_download = self._pieces.get_next_piece(bitfield)
                if piece_to_download is None:
                    logging.log(logging.INFO, "No piece to download. Leaving")
                    break

                current_piece = b""
                # Send requests

                for block in piece_to_download.blocks:
                    piece_id = block.piece_id
                    piece_offset = block.block_id * 2**14
                    piece_size = block.block_size

                    # Build piece request
                    piece_req = Connection.build_request_piece(piece_id, piece_offset, piece_size)
                    data, current_state = self._download_block(conn, piece_req, current_state)
                    current_piece += data

                # Check if the piece is valid
                if sha1(current_piece).hexdigest() == piece_to_download.hash.hex():
                    logging.log(logging.INFO, f"Piece {piece_to_download.piece_id} is valid. Writing it to disk")
                    self._file_manager.write(piece_to_download.offset, current_piece)
                    #self._pieces.mark_piece_as_downloaded(piece_to_download.piece_id)
                else:
                    logging.log(logging.ERROR, f"Piece {piece_to_download.piece_id} is invalid. Putting it back")
                    self._pieces.put_back(piece_to_download)
 


        except Exception as e:
            if piece_to_download is not None:
                logging.log(logging.ERROR, f"Error downloading piece {piece_to_download.piece_id} from {peer_ip}. {e}")
                self._pieces.put_back(piece_to_download)
            else:
                logging.log(logging.ERROR, f"Error downloading piece from {peer_ip}. {e}")





    def _download_block(self, conn, piece_req, current_state):
        # Completed
        requested_piece = False


        while True:
            if not requested_piece and current_state != "chocked":
                requested_piece = True
                self._network.send_data(conn, piece_req)
                continue

            # here all the received messages are prefixed with the length of the message
            # so, we are not passing any buffer size
            received_data = self._network.receive_data(conn)
            length, bitfield, payload = Connection.parse_peer_message(received_data)

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
                i, b, data = Connection.parse_piece(payload)
                return data, current_state

            else:
                print(f"Unknown bitfield {bitfield} received")

    def terminate(self):
        self._should_end = True

    def __str__(self):
        from math import trunc

        downloaded_megabytes = self._network.downloaded() / 1024 / 1024
        uploaded_megabytes = self._network.uploaded() / 1024 / 1024

        percentage = (
            100
            * (self._pieces.total_pieces() - self._pieces.yet_to_download())
            / self._pieces.total_pieces()
        )
        arr = "#" * trunc(percentage)
        arr += "-" * (100 - trunc(percentage))

        arr = f"[{arr}] {percentage:.2f}% {downloaded_megabytes:.2f}MB {uploaded_megabytes:.2f}MB"
        return f"{self._metadata.name()} - {arr}"
