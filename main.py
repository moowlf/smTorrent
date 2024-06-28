import os
import sys
import time
import signal
import logging
import argparse

from parser.TorrentInformation import TorrentInformation
from torrent.Session import Session
from torrent.Torrent import Torrent

# Configure logging
LOG_FILE = "smtorrent.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="[%(asctime)s][%(levelname)s] - %(message)s",
)

# Register the signal handler
#signal.signal(signal.SIGINT, lambda signum, frame: current_session.terminate())

# Output the torrent information
def output_torrent_information_to_console():

    #os.system("clear" if os.name == "posix" else "cls")

    # ==== Torrents =====
    cols = (120 - len(" Torrents ")) // 2
    history = "*" * cols + " Torrents " + "*" * cols
    history += "\n\n"

    # print torrents
    for torrent in current_session.torrents():
        history += str(torrent) + "\n"
    history += "\n"

    print(history)


# Parsing the command line arguments
parser = argparse.ArgumentParser(prog="smTorrent", description="BitTorrent client")
parser.add_argument("-t", "--torrent_file", help="Path to the torrent file")
parser.add_argument("-p", "--parse", help="Parse the torrent file", action='store_true', default=False)
args = parser.parse_args()

if not args.torrent_file:
    print("Please provide the path to the torrent file")
    sys.exit(1)

# Parse the torrent file
data = TorrentInformation(args.torrent_file)

if args.parse:
    data.print()
    sys.exit(0)

filepath = args.torrent_file
current_session = Session()

current_session.add_torrent(Torrent(data))
current_session.download()

while not current_session.is_terminated():
    output_torrent_information_to_console()
    time.sleep(1)

current_session.wait_to_close()
