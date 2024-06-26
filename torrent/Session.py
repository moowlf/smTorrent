
import logging
import threading

from random import randint

class Session:

    def __init__(self):
        # List of torrents currently being downloaded / seeded
        self._torrent_files = []

        # Thread responsible for logging
        self._logging_thread = threading.Thread(target=self._status)
        self._logging_thread.start()

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
    
    def _status(self):

        from time import sleep

        while True:
            for torrent in self._torrent_files:
                print(torrent)
            
            # Sleep for 5 seconds
            sleep(1)
    
    def wait_to_close(self):
        self._logging_thread.join()
        for thread in self._downloading_threads:
            thread.join()

    def torrents(self):
        return self._torrents
