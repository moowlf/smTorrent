
import sys
from bencode import bencode
from torrent import session, torrent
from torrent.TorrentInformation import TorrentInformation

# Torrent file
if len(sys.argv) != 2:
    print("Usage: python smtorrent.py <path_to_torrent_file>")
    sys.exit(1)

filepath = sys.argv[1]
current_session = session.Session()

with open(filepath, 'rb') as f:
    d = bencode.decode_dictionary(f.read())[0]

    current_session.add_torrent(torrent.Torrent(TorrentInformation(d)))
    current_session.download()

