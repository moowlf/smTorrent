from dataclasses import dataclass

from torrent.TorrentException import TorrentException


@dataclass
class TorrentInformation:
    """
    Holds the metadata from the torrent file
    """
    announce_url: str
    creation_date: str
    author: str

    file_length: int
    file_name: str
    file_piece_length: int
    file_pieces: bytes

    def __init__(self, info):
        self.announce_url = TorrentInformation.get("announce", info).decode()
        self.creation_date = TorrentInformation.get('creation date', info)
        self.author = TorrentInformation.get("created by", info).decode()
        self.comment = TorrentInformation.get("comment", info).decode()

        self.file_length = TorrentInformation.get('length', info['info'])
        self.file_name = TorrentInformation.get('name', info['info'])
        self.file_piece_length = TorrentInformation.get('piece length', info['info'])
        self.pieces = TorrentInformation.get('pieces', info['info'])

    @staticmethod
    def get(val: str, data, forced=False):
        if val in data:
            return data[val]

        if forced:
            raise TorrentException(f"Dictionary has no {val}!")
        return b""
