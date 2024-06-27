
import time
import logging
import requests
import threading

from torrent import Connection
from bencode import bencode

class PeerManager:

    def __init__(self, infodata) -> None:
        
        # Suppose to stop when variable is set to True
        self._should_end = False

        # Get the trackers from the torrent file
        self._trackers = infodata.announce_urls()
        logging.log(logging.INFO, f"Trackers: {self._trackers}")

        # Save the info hash
        self._info_hash = infodata.info_hash()

        # Prepare the threads
        self._threads = []

        # Thread Lock
        self._lock = threading.Lock()

        # Peer Data Structure
        self._peers = {}
        self._peers_array = []
    
    def start(self, own_peer_id):
        
        for id, tracker in enumerate(self._trackers):
            self._threads.append(threading.Thread(target=self._connect, args=(tracker, own_peer_id), name=f"Tracker-{id}"))
            self._threads[-1].start()

    def _connect(self, tracker_url, own_peer_id):

        while not self._should_end:

            # Query the tracker
            params = Connection.build_peer_request(self._info_hash, own_peer_id)

            try:
                req = requests.get(tracker_url, params)
            except Exception:
                break

            # Decode the answer and wait for next call
            answer = bencode.decode_dictionary(req.content)[0]

            # Add peers to the set
            with self._lock:
                for peer in answer["peers"]:
                    
                    peer_addr = f"{peer['ip'].decode()}:{peer['port']}"
                    if peer_addr in self._peers:
                        continue
                    
                    self._peers[peer_addr] = len(self._peers_array)
                    self._peers_array.append(peer_addr)

            # Sleep
            logging.log(logging.INFO, f"Peer request: Waiting for {answer['interval']}s")
            time.sleep(answer["interval"])
    

    def get_peer(self):

        with self._lock:
            if len(self._peers_array) == 0:
                return None

            peer = self._peers_array.pop()
            self._peers.pop(peer)
            return peer



    def wait_to_close(self):
        for thread in self._threads:
            thread.join()

    def terminate(self):
        self._should_end = True