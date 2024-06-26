
import sys
import base64
import logging

from bencode import bencode
from torrent.TorrentInformation import TorrentInformation

from torrent.Session import Session
from torrent.Torrent import Torrent

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s][%(levelname)s] - %(message)s')


# Torrent file
if len(sys.argv) != 2:
    print("Usage: python smtorrent.py <path_to_torrent_file>")
    sys.exit(1)

filepath = sys.argv[1]
current_session = Session()

logging.log(logging.INFO, f"Opening file {filepath}")

with open(filepath, 'rb') as f:
    d = bencode.decode_dictionary(f.read())[0]

    torrent_information = TorrentInformation(d)
    logging.log(logging.INFO, f"Torrent information: {base64.encodebytes(str(torrent_information).encode())}")

    current_session.add_torrent(Torrent(torrent_information))
    current_session.download()

