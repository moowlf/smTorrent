
import queue
import threading
import time
import requests

from torrent.PieceManager import PieceManager, Piece 
from bencode import bencode
from hashlib import sha1
from torrent import Connection, Network
from queue import Queue


class Torrent:

    def __init__(self, file_data):
        self._peers = Queue()
        self._metadata = file_data

        # Create files to be downloaded
        self._tmpfile = self._create_temp_file()

        # Prepare all pieces to be downloaded for this torrent
        self._pieces = PieceManager(self._metadata)

        self.file_mutex = threading.Lock()


    def _create_temp_file(self):

        # Generate the random filename
        random_filename = f"{self._metadata.info_hash().hex()}.tmp"

        # Create the file
        with open(random_filename, "wb") as file:
            file.seek(self._metadata.total_length() - 1)
            file.write(b"\0")

        return random_filename
    
    def download(self, own_peer_id: str, threads=1):
        # Start thread responsible for communicating with tracker
        tracker_comm = threading.Thread(target=self._get_peers, args=(own_peer_id,))
        tracker_comm.start()

        # Start threads responsible for downloading the pieces
        self._download(own_peer_id)

        # Create the final file
        self._create_final_files()

        # End threads
        tracker_comm.join()
    
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

        while not self._pieces.download_complete():

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
                work = self._pieces.get_next_piece()
            except queue.Empty:
                self._peers.put(peer)
                continue

            """
            We have reached a valid state for download to start
            """
            threads.append(threading.Thread(target=self._download_piece, args=(own_peer_id, peer, work), name=peer["ip"]))
            threads[-1].start()

        [thread.join() for thread in threads]

    def _get_peers(self, own_peer_id: str):

        info_hash = self._metadata.info_hash()
        announce_url = self._metadata.announce_url()

        while not self._pieces.download_complete():
            
            # Query the tracker
            params = Connection.build_peer_request(info_hash, own_peer_id)

            req = requests.get(announce_url, params)

            # Decode the answer and wait for next call
            answer = bencode.decode_dictionary(req.content)[0]

            while not self._peers.empty():
                self._peers.get()

            for peer in answer["peers"]:
                self._peers.put({"ip": peer["ip"].decode(), "port": peer["port"]})

            # Sleep
            print(f"Peer request: Waiting for {answer['interval']}s")
            time.sleep(answer["interval"])


    def _download_piece(self, own_peer_id, peer, piece: Piece):

        try:
            # Retrieve IP to connect (assuming every IP has all files)
            peer_ip, peer_port = peer["ip"], peer["port"]

            # Get Connection
            conn = Network.Network.get_socket(peer_ip)
            conn.connect((peer_ip, peer_port))
            network = Network.Network()
            print(f"> Connected to {peer_ip}:{peer_port}")

            # Send Handshake and receive
            handshake = Connection.build_handshake(self._metadata.info_hash(), own_peer_id)
            network.send_data(conn, handshake)
            _ = network.receive_data_with_length(conn, len(handshake))

            # Send interested
            interested = Connection.build_interested()
            network.send_data(conn, interested)

            # Download Piece
            total_piece = b""
            current_state = "chocked"

            for block_pieces in piece.blocks:

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
                        network.send_data(conn, piece_req)
                        continue

                    # here all the received messages are prefixed with the length of the message
                    # so, we are not passing any buffer size
                    received_data = network.receive_data(conn)
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

            print(hash.hexdigest(), piece.hash.hex())
            if piece.hash.hex() != hash.hexdigest():
                print(f"{peer_ip} : Hashes do not match")
                self.pieces_to_download.put(piece)
                self._peers.put(peer)
                return

            with open(self._tmpfile, "r+b") as file:

                self.file_mutex.acquire()
                try:
                    for bl in piece.blocks:
                        file.seek(bl.start_position)
                        file.write(bl.data)
                finally:
                    self.file_mutex.release()

            self._peers.put(peer)
            conn.close()
        except Exception as e:
            print(e)
