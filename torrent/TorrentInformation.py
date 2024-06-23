
import dataclasses
from hashlib import sha1

from bencode import bencode
from torrent.TorrentException import TorrentException

@dataclasses.dataclass
class FileInformation:
    length: int
    path: list

class TorrentInformation:
    """
    Holds the metadata from the torrent file
    """

    def __init__(self, info):

        self._info = info

        # Calculate the info_hash
        self._info_hash = sha1(bencode.encode_dictionary(info['info'])).digest()

        # Process the files in the torrent
        self._files = self._process_files()

        # Split the pieces into 20 byte chunks
        pieces = TorrentInformation._get('pieces', info['info'])
        self._pieces = [pieces[i:i+20] for i in range(0, len(pieces), 20)]

    def announce_url(self):
        return TorrentInformation._get("announce", self._info).decode()

    def creation_date(self):
        return TorrentInformation._get('creation date', self._info)

    def author(self):
        return TorrentInformation._get("created by", self._info).decode()
    
    def comment(self):
        return TorrentInformation._get("comment", self._info).decode()
    
    def piece_length(self):
        return TorrentInformation._get("piece length", self._info['info'])

    def total_length(self):
        return sum([f.length for f in self._files])

    def name(self):
        return TorrentInformation._get("name", self._info['info']).decode()

    def pieces(self):
        return self._pieces

    def piece(self, index):
        return self._pieces[index]

    def file_length(self):

        if self.is_single_file():
            return TorrentInformation._get("length", self._info['info'])

        raise TorrentException("Torrent is not a single file torrent!")

    def info_hash(self):
        return self._info_hash

    def is_single_file(self):
        return 'length' in self._info['info']

    def is_multi_file(self):
        return 'files' in self._info['info']

    def _process_files(self):
        if self.is_single_file():
            return [FileInformation(TorrentInformation._get("length", self._info['info']), [TorrentInformation._get("name", self._info['info'])])]

        return [FileInformation(f['length'], f['path']) for f in TorrentInformation._get("files", self._info['info'])]

    def _get(val: str, data, forced=False):
        if val in data:
            return data[val]

        if forced:
            raise TorrentException(f"Dictionary has no {val}!")
        return b""
