"""pieces.py

Defines chess pieces and shared movement helpers.
The board coordinates follow the convention:
- row 0 is Black's back rank
- row 7 is White's back rank
- col 0 is file 'a', col 7 is file 'h'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

Position = Tuple[int, int]


@dataclass(frozen=True)
class Piece:
    """Simple data object describing a chess piece.

    Attributes:
        color: 'white' or 'black'
        kind: one of 'K', 'Q', 'R', 'B', 'N', 'P'
    """

    color: str
    kind: str

    @property
    def symbol(self) -> str:
        """Return a compact text symbol (useful for debugging/logging)."""
        return f"{self.color[0].upper()}{self.kind}"


def inside_board(row: int, col: int) -> bool:
    """Return True if coordinates are inside the 8x8 board."""
    return 0 <= row < 8 and 0 <= col < 8


def linear_moves(
    board: List[List[Piece | None]], start: Position, color: str, deltas: List[Tuple[int, int]]
) -> List[Position]:
    """Generate line-based moves for bishops/rooks/queens.

    Stops when hitting a piece. Can capture enemy piece and then stop.
    """
    row, col = start
    moves: List[Position] = []
    for dr, dc in deltas:
        r, c = row + dr, col + dc
        while inside_board(r, c):
            target = board[r][c]
            if target is None:
                moves.append((r, c))
            else:
                if target.color != color:
                    moves.append((r, c))
                break
            r += dr
            c += dc
    return moves
