
from typing import List
from dataclasses import dataclass
from queue import Queue

from torrent.TorrentInformation import TorrentInformation

@dataclass
class BlockPiece:
    piece_id: int
    block_id: int
    block_size: int
    data: List
    start_position: int


@dataclass
class Piece:
    piece_id: int
    offset: int
    hash: bytearray
    blocks: List[BlockPiece]


class PieceManager:

    def __init__(self, torrent_information: TorrentInformation) -> None:
        
        self._pieces = []
        
        # Create pieces from hashes
        for i, piece_hash in enumerate(torrent_information.pieces()):
            self._pieces.append(Piece(piece_id=i, hash=piece_hash, blocks=[], offset=i * torrent_information.piece_length()))

        # Split pieces into blocks
        self._split_pieces_into_blocks(torrent_information)

        # Create Queue with pieces
        self._download_queue = self._create_queue()

    def have_piece(self, piece_id):
        return self._have_pieces[piece_id]

    def _split_pieces_into_blocks(self, torrent_information: TorrentInformation):
        """
        It takes the all pieces from the file and divide them into blocks of size up to 16KB
        :return: A Queue with all the pieces and information needed to request them
        """
        total_file_left = torrent_information.total_length()
        current_position = 0

        for id, piece in enumerate(self._pieces):
            piece_size = min(torrent_information.piece_length(), total_file_left)
            total_file_left -= piece_size

            # Split into blocks
            blocks_size = 0
            block_id = 0

            while blocks_size < piece_size:
                current_block_size = min(2 ** 14, piece_size - blocks_size)
                piece.blocks.append(
                    BlockPiece(piece_id=id, start_position=current_position, block_id=block_id,
                               block_size=current_block_size,
                               data=b""))
                blocks_size += current_block_size
                block_id += 1
                current_position += current_block_size

    def _create_queue(self):
        q = Queue()
        for piece in self._pieces:
            q.put(piece)
        return q

    def get_next_piece(self):
        return self._download_queue.get()

    def put_back(self, piece):
        self._download_queue.put(piece)
    
    def download_complete(self):
        return self._download_queue.empty()
    
    def yet_to_download(self):
        return self._download_queue.qsize()

    def total_pieces(self):
        return len(self._pieces)