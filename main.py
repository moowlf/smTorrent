
import sys
from bencode import bencode
from torrent.TorrentInformation import TorrentInformation

from torrent.Session import Session
from torrent.Torrent import Torrent

# Torrent file
if len(sys.argv) != 2:
    print("Usage: python smtorrent.py <path_to_torrent_file>")
    sys.exit(1)

filepath = sys.argv[1]
current_session = Session()

with open(filepath, 'rb') as f:
    d = bencode.decode_dictionary(f.read())[0]

    current_session.add_torrent(Torrent(TorrentInformation(d)))
    current_session.download()

