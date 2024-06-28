
import logging
import dataclasses
from hashlib import sha1
from base64 import encodebytes

from bencode import encode_dictionary, decode_dictionary
from parser.ParserException import ParserException

@dataclasses.dataclass
class FileInformation:
    length: int
    path: list


class TorrentInformation:
    """
    Holds the metadata from the torrent file
    """

    def __init__(self, filepath):

        logging.log(logging.INFO, f"Opening file {filepath}")
        with open(filepath, "rb") as f:
            self._info = decode_dictionary(f.read())[0]

        # Calculate the info_hash
        self._info_hash = sha1(encode_dictionary(self._info["info"])).digest()

        # Process the files in the torrent
        self._files = self._process_files()

        # Split the pieces into 20 byte chunks
        pieces = TorrentInformation._get("pieces", self._info["info"])
        self._pieces = [pieces[i : i + 20] for i in range(0, len(pieces), 20)]

        # Logging the torrent information
        self_data = str(self).encode()
        logging.log(logging.INFO, f"Torrent information: {encodebytes(self_data).decode()}")

    def announce_urls(self):
        trackers = [TorrentInformation._get("announce", self._info).decode()]

        for tracker in TorrentInformation._get("announce-list", self._info, False):
            trackers.append(tracker[0].decode())
        
        return trackers

    def creation_date(self):
        return TorrentInformation._get("creation date", self._info)

    def author(self):
        return TorrentInformation._get("created by", self._info).decode()

    def comment(self):
        return TorrentInformation._get("comment", self._info).decode()

    def piece_length(self):
        return TorrentInformation._get("piece length", self._info["info"])

    def total_length(self):
        return sum([f.length for f in self._files])

    def name(self):
        return TorrentInformation._get("name", self._info["info"]).decode()

    def pieces(self):
        return self._pieces

    def piece(self, index):
        return self._pieces[index]

    def file_length(self):
        if self.is_single_file():
            return TorrentInformation._get("length", self._info["info"])

        raise ParserException("Torrent is not a single file torrent!")

    def info_hash(self):
        return self._info_hash

    def is_single_file(self):
        return "length" in self._info["info"]

    def is_multi_file(self):
        return "files" in self._info["info"]

    def files(self):
        return self._files

    def _process_files(self):
        def convert_path(path):
            return "/".join([p.decode() for p in path])

        if self.is_single_file():
            length = TorrentInformation._get("length", self._info["info"])
            name = TorrentInformation._get("name", self._info["info"]).decode()
            return [FileInformation(length, name)]

        return [
            FileInformation(f["length"], convert_path(f["path"]))
            for f in TorrentInformation._get("files", self._info["info"])
        ]

    def _get(val: str, data, forced=False):
        if val in data:
            return data[val]

        if forced:
            raise ParserException(f"Dictionary has no {val}!")
        return b""

    def _information(self):
        return {
            "announce-list": self.announce_urls(),
            "creation date": self.creation_date(),
            "author": self.author(),
            "comment": self.comment(),
            "piece length": self.piece_length(),
            "total length": self.total_length(),
            "name": self.name(),
            "info hash": self.info_hash(),
            "is single file": self.is_single_file(),
            "is multi file": self.is_multi_file(),
            "files": self._files,
        }

    def __str__(self) -> str:
        return str(self._information())

    def print(self):
        data = self._information()
        for k,v in data.items():
            print(f"{k}: {v}")

