
import logging
from random import randint

class Session:

    def __init__(self):
        self._torrents = []
        self._peerID = "-smtorren-" + "".join([str(randint(0, 9)) for _ in range(10)])
        logging.log(logging.INFO, f"Own Peer ID: {self._peerID}")

    def add_torrent(self, torrent_file):
        self._torrents.append(torrent_file)

    def download(self):
        torrent = self._torrents[0].download(self._peerID)

    @property
    def torrents(self):
        return self._torrents
