import os
import sys
import time
import signal
import base64
import logging

from bencode import bencode
from torrent.TorrentInformation import TorrentInformation

from torrent.Session import Session
from torrent.Torrent import Torrent

# Configure logging
LOG_FILE = "smtorrent.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] - %(message)s",
)

# Torrent file
if len(sys.argv) != 2:
    print("Usage: python smtorrent.py <path_to_torrent_file>")
    sys.exit(1)

filepath = sys.argv[1]
current_session = Session()

logging.log(logging.INFO, f"Opening file {filepath}")

# Register the signal handler
#signal.signal(signal.SIGINT, lambda signum, frame: current_session.terminate())

# Output the torrent information
def output_torrent_information_to_console():

    os.system("clear" if os.name == "posix" else "cls")

    # ==== Torrents =====
    cols = (120 - len(" Torrents ")) // 2
    history = "*" * cols + " Torrents " + "*" * cols
    history += "\n\n"

    # print torrents
    for torrent in current_session.torrents():
        history += str(torrent) + "\n"
    history += "\n"

    print(history)


with open(filepath, "rb") as f:
    d = bencode.decode_dictionary(f.read())[0]

    torrent_information = TorrentInformation(d)
    logging.log(
        logging.INFO,
        f"Torrent information: {base64.encodebytes(str(torrent_information).encode())}",
    )

    current_session.add_torrent(Torrent(torrent_information))
    current_session.download()

    while not current_session.is_terminated():
        output_torrent_information_to_console()
        time.sleep(1)
    
    current_session.wait_to_close()
