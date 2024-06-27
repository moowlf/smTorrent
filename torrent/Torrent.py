
import logging
import threading

from torrent.PeerManager import PeerManager
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

        # Create files to be downloaded
        self._tmpfile = self._create_temp_file()

        # Prepare all pieces to be downloaded for this torrent
        self._pieces = PieceManager(self._metadata)

        # Prepare tracker manager
        self._peer_manager = PeerManager(self._metadata)

        self.file_mutex = threading.Lock()


    def _create_temp_file(self):

        # Generate the random filename
        random_filename = f"{self._metadata.info_hash().hex()}.tmp"

        # Create the file
        with open(random_filename, "wb") as file:
            file.seek(self._metadata.total_length() - 1)
            file.write(b"\0")

        return random_filename
    
    def download(self, own_peer_id: str):
        # Start thread responsible for communicating with tracker
        self._peer_manager.start(own_peer_id)

        # Start threads responsible for downloading the pieces
        self._download(own_peer_id)

        # Create the final file
        self._create_final_files()
        
        # End threads
        self._peer_manager.terminate()
    
    def _create_final_files(self):

        with open(self._tmpfile, "rb") as tmp_file:

            for file in self._metadata._files:

                # Create the directories
                path = "/".join(file.path[:-1])

                if path:
                    import os
                    os.makedirs(path, exist_ok=True)

                with open(file.path[-1], "wb") as final_file:
                    final_file.write(tmp_file.read(file.length))

    def _download(self, own_peer_id):

        threads = []

        while not self._pieces.download_complete() and not self._should_end:

            """
            Try to retrieve a peer ip
            """
            peer = self._peer_manager.get_peer()
            if peer is None:
                continue

            """
            We have reached a valid state for download to start
            """
            threads.append(threading.Thread(target=self._download_piece, args=(own_peer_id, peer), name=peer["ip"]))
            threads[-1].start()

        [thread.join() for thread in threads]

    def _download_piece(self, own_peer_id, peer):

        piece_to_download = None

        try:
            # Retrieve IP to connect (assuming every IP has all files)
            peer_ip, peer_port = peer["ip"], peer["port"]

            # Get Connection
            conn = Network.Network.get_socket(peer_ip)
            conn.connect((peer_ip, peer_port))
            logging.log(logging.INFO, f"Connected to {peer_ip}:{peer_port}")

            # Send Handshake and receive
            handshake = Connection.build_handshake(self._metadata.info_hash(), own_peer_id)
            self._network.send_data(conn, handshake)
            _ = self._network.receive_data_with_length(conn, len(handshake))
            logging.log(logging.INFO, f"Handshake sent and received")

            # Send interested
            interested = Connection.build_interested()
            self._network.send_data(conn, interested)
            logging.log(logging.INFO, f"Interested sent")

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
                    self._peers.put(peer)
                    return

                with open(self._tmpfile, "r+b") as file:

                    self.file_mutex.acquire()
                    try:
                        for bl in piece_to_download.blocks:
                            file.seek(bl.start_position)
                            file.write(bl.data)
                    finally:
                        self.file_mutex.release()

            self._peers.put(peer)
            conn.close()
        except Exception:
            if piece_to_download is not None:
                self._pieces.put_back(piece_to_download)

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
