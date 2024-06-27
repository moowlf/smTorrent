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
signal.signal(signal.SIGINT, lambda signum, frame: current_session.terminate())


# Read n lines from the end of file
def tail_file(file, n):

    with open(file, "rb") as f:
        try:
            f.seek(-2, os.SEEK_END)
            
            while n > 0:

                if f.read(1) == b"\n":
                    n -= 1
    
                f.seek(-2, os.SEEK_CUR)

        except OSError:
            f.seek(0)

        return [line.decode() for line in f.readlines()]



# Output the torrent information
def output_torrent_information_to_console():

    os.system("clear" if os.name == "posix" else "cls")

    # ==== Torrents =====
    cols = (120 - len(" Torrents ")) // 2
    print("*" * cols + " Torrents " + "*" * cols)
    print()

    # print torrents
    for torrent in current_session.torrents():
        print(torrent)
    print()

    # ==== Logs =====
    cols = (120 - len(" Logs ")) // 2
    print("*" * cols + " Logs " + "*" * cols)
    print()

    log_lines = tail_file(LOG_FILE, 10)
    for line in log_lines:
        print(line.rstrip() if len(line) < 120 else line[:117] + "...")


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
        time.sleep(2)
    
    current_session.wait_to_close()
