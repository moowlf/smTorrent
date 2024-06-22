
from hashlib import sha1

from bencode import bencode
from torrent.TorrentException import TorrentException

class TorrentInformation:
    """
    Holds the metadata from the torrent file
    """

    def __init__(self, info):

        self._info = info

        # Calculate the info_hash
        self._info_hash = sha1(bencode.encode_dictionary(info['info'])).digest()

        self.pieces = TorrentInformation.get('pieces', info['info'])


    def announce_url(self):
        return TorrentInformation.get("announce", self._info).decode()

    def creation_date(self):
        return TorrentInformation.get('creation date', self._info)

    def author(self):
        return TorrentInformation.get("created by", self._info).decode()
    
    def comment(self):
        return TorrentInformation.get("comment", self._info).decode()
    
    def piece_length(self):
        return TorrentInformation.get("piece length", self._info['info'])

    def name(self):
        return TorrentInformation.get("name", self._info['info']).decode()

    def file_length(self):

        if self.is_single_file():
            return TorrentInformation.get("length", self._info['info'])

        raise TorrentException("Torrent is not a single file torrent!")

    def info_hash(self):
        return self._info_hash

    def is_single_file(self):
        return 'length' in self._info['info']

    def is_multi_file(self):
        return 'files' in self._info['info']

    def get(val: str, data, forced=False):
        if val in data:
            return data[val]

        if forced:
            raise TorrentException(f"Dictionary has no {val}!")
        return b""
