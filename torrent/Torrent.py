
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
            threads.append(threading.Thread(target=self._download_piece, args=(own_peer_id, peer_ip, peer_port), name=peer_ip))
            threads[-1].start()

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

            # Download Piece
            current_state = "chocked"

            while not self._pieces.download_complete():

                # Retrieve the next piece to download
                piece_to_download = self._pieces.get_next_piece()
                total_piece = b""
                
                for block_pieces in piece_to_download.blocks:

                    # Helper variables
                    piece_id = block_pieces.piece_id
                    piece_offset = block_pieces.block_id * 2 ** 14
                    piece_size = block_pieces.block_size

                    # Build piece request
                    piece_req = Connection.build_request_piece(piece_id, piece_offset, piece_size)

                    # Completed
                    is_completed = False
                    requested_piece = False

                    while not is_completed:

                        if not requested_piece  and current_state != "chocked":
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
                            i, b, block_pieces.data = Connection.parse_piece(payload)
                            total_piece += block_pieces.data
                            break

                        else:
                            print(f"Unknown bitfield {bitfield} received")

                # Downloaded all the blocks from the piece
                hash = sha1(total_piece)

                if piece_to_download.hash.hex() != hash.hexdigest():
                    print(f"{peer_ip} : Hashes do not match")
                    self._pieces.put_back(piece_to_download)
                    return

                self._file_manager.write(piece_to_download.offset, total_piece)

            conn.close()
        except Exception as e:

            if piece_to_download is not None:
                logging.log(logging.ERROR, f"Error downloading piece {piece_to_download.piece_id} from {peer_ip}. {e}")
                self._pieces.put_back(piece_to_download)
            else:
                logging.log(logging.ERROR, f"Error downloading piece from {peer_ip}. {e}")

    def terminate(self):
        self._should_end = True

    def __str__(self):
        
        from math import trunc

        downloaded_megabytes = self._network.downloaded() / 1024 / 1024
        uploaded_megabytes = self._network.uploaded() / 1024 / 1024

        percentage = 100 * (self._pieces.total_pieces() - self._pieces.yet_to_download()) / self._pieces.total_pieces()
        arr = "#" * trunc(percentage)
        arr += "-" * (100 - trunc(percentage))
        
        arr = f"[{arr}] {percentage:.2f}% {downloaded_megabytes:.2f}MB {uploaded_megabytes:.2f}MB"
        return f"{self._metadata.name()} - {arr}"
