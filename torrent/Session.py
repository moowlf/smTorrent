

import logging
import threading

from random import randint

class Session:

    def __init__(self):

        # Register the signal handler
        self._should_terminate = False

        # List of torrents currently being downloaded / seeded
        self._torrent_files = []

        # Threads responsible for downloading the pieces
        self._downloading_threads = []

        # Prepare the peer ID for this session
        self._peerID = "-smtorren-" + "".join([str(randint(0, 9)) for _ in range(10)])
        logging.log(logging.INFO, f"Own Peer ID: {self._peerID}")


    def add_torrent(self, torrent_file):
        self._torrent_files.append(torrent_file)
        
    def download(self):

        for torrent in self._torrent_files:
            self._downloading_threads.append(threading.Thread(target=torrent.download, args=(self._peerID,)))
            self._downloading_threads[-1].start()
    
    def wait_to_close(self):
        for thread in self._downloading_threads:
            thread.join()

    def torrents(self):
        return self._torrent_files
    
    def terminate(self):
        self._should_terminate = True
        logging.log(logging.INFO, "Terminating session...")
        for torrent in self._torrent_files:
            torrent.terminate()
    
    def is_terminated(self):
        return self._should_terminate

