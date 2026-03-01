"""board.py

Main chess rules engine:
- Move generation for all pieces
- Legal move filtering (king safety)
- Special moves: castling, en passant, promotion
- Game state detection: check, checkmate, stalemate
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from pieces import Piece, inside_board, linear_moves

Position = Tuple[int, int]
Move = Tuple[Position, Position, Optional[str]]  # ((r1,c1), (r2,c2), promotion_kind)


@dataclass
class MoveResult:
    """Detailed info about an executed move (useful for UI and undo)."""

    captured: Optional[Piece]
    was_en_passant: bool = False
    en_passant_captured_pos: Optional[Position] = None
    was_castle: bool = False
    rook_from: Optional[Position] = None
    rook_to: Optional[Position] = None
    promoted_from: Optional[str] = None


class ChessBoard:
    """Stateful chess board and rules controller."""

    def __init__(self) -> None:
        self.board: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self.turn: str = "white"
        self.castling_rights: Dict[str, bool] = {
            "white_kingside": True,
            "white_queenside": True,
            "black_kingside": True,
            "black_queenside": True,
        }
        self.en_passant_target: Optional[Position] = None
        self.halfmove_clock: int = 0
        self.fullmove_number: int = 1
        self.move_history: List[Move] = []
        self.reset()

    def reset(self) -> None:
        """Set initial chess position."""
        self.board = [[None for _ in range(8)] for _ in range(8)]

        order = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        for c, kind in enumerate(order):
            self.board[0][c] = Piece("black", kind)
            self.board[7][c] = Piece("white", kind)
        for c in range(8):
            self.board[1][c] = Piece("black", "P")
            self.board[6][c] = Piece("white", "P")

        self.turn = "white"
        self.castling_rights = {
            "white_kingside": True,
            "white_queenside": True,
            "black_kingside": True,
            "black_queenside": True,
        }
        self.en_passant_target = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_history = []

    def clone(self) -> "ChessBoard":
        """Deep-copy board state for search algorithms."""
        copy = ChessBoard.__new__(ChessBoard)
        copy.board = [[self.board[r][c] for c in range(8)] for r in range(8)]
        copy.turn = self.turn
        copy.castling_rights = dict(self.castling_rights)
        copy.en_passant_target = self.en_passant_target
        copy.halfmove_clock = self.halfmove_clock
        copy.fullmove_number = self.fullmove_number
        copy.move_history = list(self.move_history)
        return copy

    @staticmethod
    def opposite(color: str) -> str:
        return "black" if color == "white" else "white"

    def get_piece(self, pos: Position) -> Optional[Piece]:
        r, c = pos
        return self.board[r][c]

    def set_piece(self, pos: Position, piece: Optional[Piece]) -> None:
        r, c = pos
        self.board[r][c] = piece

    def find_king(self, color: str) -> Optional[Position]:
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p and p.color == color and p.kind == "K":
                    return (r, c)
        return None

    def is_square_attacked(self, square: Position, by_color: str) -> bool:
        """Check whether `square` is attacked by `by_color`.

        Uses pseudo-legal moves (ignoring whether attacker's king is in check).
        """
        target_r, target_c = square

        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p is None or p.color != by_color:
                    continue
                for mr, mc in self._pseudo_moves_for_piece((r, c), include_castling=False, attacks_only=True):
                    if mr == target_r and mc == target_c:
                        return True
        return False

    def in_check(self, color: str) -> bool:
        king_pos = self.find_king(color)
        if king_pos is None:
            return False
        return self.is_square_attacked(king_pos, self.opposite(color))

    def _pseudo_moves_for_piece(
        self,
        pos: Position,
        include_castling: bool = True,
        attacks_only: bool = False,
    ) -> List[Position]:
        """Generate pseudo-legal target squares for one piece.

        attacks_only:
            - For pawns, includes diagonal attack squares even if empty.
            - For kings, castling is excluded.
        """
        r, c = pos
        piece = self.board[r][c]
        if piece is None:
            return []

        color = piece.color
        enemy = self.opposite(color)
        kind = piece.kind
        moves: List[Position] = []

        if kind == "P":
            direction = -1 if color == "white" else 1
            start_row = 6 if color == "white" else 1

            # Forward moves (not in attack-only mode)
            if not attacks_only:
                nr = r + direction
                if inside_board(nr, c) and self.board[nr][c] is None:
                    moves.append((nr, c))
                    nr2 = r + 2 * direction
                    if r == start_row and self.board[nr2][c] is None:
                        moves.append((nr2, c))

            # Captures / attack squares
            for dc in (-1, 1):
                nr, nc = r + direction, c + dc
                if not inside_board(nr, nc):
                    continue
                target = self.board[nr][nc]
                if attacks_only:
                    moves.append((nr, nc))
                else:
                    if target is not None and target.color == enemy:
                        moves.append((nr, nc))
                    elif self.en_passant_target == (nr, nc):
                        moves.append((nr, nc))

        elif kind == "N":
            jumps = [
                (-2, -1),
                (-2, 1),
                (-1, -2),
                (-1, 2),
                (1, -2),
                (1, 2),
                (2, -1),
                (2, 1),
            ]
            for dr, dc in jumps:
                nr, nc = r + dr, c + dc
                if not inside_board(nr, nc):
                    continue
                target = self.board[nr][nc]
                if target is None or target.color != color:
                    moves.append((nr, nc))

        elif kind == "B":
            moves.extend(linear_moves(self.board, pos, color, [(-1, -1), (-1, 1), (1, -1), (1, 1)]))

        elif kind == "R":
            moves.extend(linear_moves(self.board, pos, color, [(-1, 0), (1, 0), (0, -1), (0, 1)]))

        elif kind == "Q":
            moves.extend(
                linear_moves(
                    self.board,
                    pos,
                    color,
                    [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
                )
            )

        elif kind == "K":
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if not inside_board(nr, nc):
                        continue
                    target = self.board[nr][nc]
                    if target is None or target.color != color:
                        moves.append((nr, nc))

            if include_castling and not attacks_only:
                moves.extend(self._castle_moves(color))

        return moves

    def _castle_moves(self, color: str) -> List[Position]:
        """Return king destination squares available for castling."""
        row = 7 if color == "white" else 0
        enemy = self.opposite(color)
        king_pos = (row, 4)
        king = self.board[row][4]
        if king is None or king.kind != "K" or king.color != color:
            return []

        if self.in_check(color):
            return []

        destinations: List[Position] = []

        # Kingside: squares between king and rook: f,g (5,6)
        if self.castling_rights[f"{color}_kingside"]:
            if self.board[row][5] is None and self.board[row][6] is None:
                rook = self.board[row][7]
                if rook and rook.kind == "R" and rook.color == color:
                    if not self.is_square_attacked((row, 5), enemy) and not self.is_square_attacked((row, 6), enemy):
                        destinations.append((row, 6))

        # Queenside: between king and rook: b,c,d (1,2,3)
        if self.castling_rights[f"{color}_queenside"]:
            if self.board[row][1] is None and self.board[row][2] is None and self.board[row][3] is None:
                rook = self.board[row][0]
                if rook and rook.kind == "R" and rook.color == color:
                    if not self.is_square_attacked((row, 3), enemy) and not self.is_square_attacked((row, 2), enemy):
                        destinations.append((row, 2))

        return destinations

    def legal_moves_for_piece(self, pos: Position) -> List[Position]:
        """Return legal destination squares for a piece (respecting king safety)."""
        piece = self.get_piece(pos)
        if piece is None or piece.color != self.turn:
            return []

        legal: List[Position] = []
        for dst in self._pseudo_moves_for_piece(pos):
            test_board = self.clone()
            test_board._apply_move_no_turn_change((pos, dst, None))
            if not test_board.in_check(piece.color):
                legal.append(dst)
        return legal

    def all_legal_moves(self, color: str) -> List[Move]:
        """Return all legal moves for the given color."""
        original_turn = self.turn
        self.turn = color
        moves: List[Move] = []

        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p is None or p.color != color:
                    continue
                from_pos = (r, c)
                for dst in self.legal_moves_for_piece(from_pos):
                    if p.kind == "P" and (dst[0] == 0 or dst[0] == 7):
                        for promo in ["Q", "R", "B", "N"]:
                            moves.append((from_pos, dst, promo))
                    else:
                        moves.append((from_pos, dst, None))

        self.turn = original_turn
        return moves

    def _apply_move_no_turn_change(self, move: Move) -> MoveResult:
        """Apply move without switching turn. Internal helper for simulation."""
        src, dst, promotion = move
        sr, sc = src
        dr, dc = dst
        piece = self.board[sr][sc]
        assert piece is not None

        result = MoveResult(captured=self.board[dr][dc])

        # En passant capture
        if piece.kind == "P" and self.en_passant_target == dst and self.board[dr][dc] is None and sc != dc:
            cap_r = sr
            cap_c = dc
            result.captured = self.board[cap_r][cap_c]
            result.was_en_passant = True
            result.en_passant_captured_pos = (cap_r, cap_c)
            self.board[cap_r][cap_c] = None

        # Move piece
        self.board[sr][sc] = None
        self.board[dr][dc] = piece

        # Castling move (king moves two squares)
        if piece.kind == "K" and abs(dc - sc) == 2:
            row = sr
            result.was_castle = True
            if dc == 6:  # kingside
                rook_from, rook_to = (row, 7), (row, 5)
            else:  # queenside
                rook_from, rook_to = (row, 0), (row, 3)
            rook = self.board[rook_from[0]][rook_from[1]]
            self.board[rook_from[0]][rook_from[1]] = None
            self.board[rook_to[0]][rook_to[1]] = rook
            result.rook_from = rook_from
            result.rook_to = rook_to

        # Promotion
        if piece.kind == "P" and (dr == 0 or dr == 7):
            new_kind = promotion or "Q"
            result.promoted_from = "P"
            self.board[dr][dc] = Piece(piece.color, new_kind)

        # Update castling rights (king or rook moved / rook captured)
        self._update_castling_rights_after_move(src, dst, piece, result.captured)

        # Update en-passant target
        self.en_passant_target = None
        if piece.kind == "P" and abs(dr - sr) == 2:
            middle = ((sr + dr) // 2, sc)
            self.en_passant_target = middle

        # Halfmove clock
        if piece.kind == "P" or result.captured is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        return result

    def _update_castling_rights_after_move(
        self, src: Position, dst: Position, piece: Piece, captured: Optional[Piece]
    ) -> None:
        sr, sc = src
        dr, dc = dst

        if piece.kind == "K":
            self.castling_rights[f"{piece.color}_kingside"] = False
            self.castling_rights[f"{piece.color}_queenside"] = False

        if piece.kind == "R":
            if piece.color == "white" and (sr, sc) == (7, 0):
                self.castling_rights["white_queenside"] = False
            if piece.color == "white" and (sr, sc) == (7, 7):
                self.castling_rights["white_kingside"] = False
            if piece.color == "black" and (sr, sc) == (0, 0):
                self.castling_rights["black_queenside"] = False
            if piece.color == "black" and (sr, sc) == (0, 7):
                self.castling_rights["black_kingside"] = False

        # Capturing rook on original squares also removes rights
        if captured and captured.kind == "R":
            if (dr, dc) == (7, 0):
                self.castling_rights["white_queenside"] = False
            if (dr, dc) == (7, 7):
                self.castling_rights["white_kingside"] = False
            if (dr, dc) == (0, 0):
                self.castling_rights["black_queenside"] = False
            if (dr, dc) == (0, 7):
                self.castling_rights["black_kingside"] = False

    def make_move(self, move: Move) -> bool:
        """Validate and execute move for current turn.

        Returns True if move was legal and applied.
        """
        src, dst, promotion = move
        piece = self.get_piece(src)
        if piece is None or piece.color != self.turn:
            return False

        legal_dsts = self.legal_moves_for_piece(src)
        if dst not in legal_dsts:
            return False

        if piece.kind == "P" and (dst[0] == 0 or dst[0] == 7):
            if promotion not in ["Q", "R", "B", "N"]:
                promotion = "Q"

        self._apply_move_no_turn_change((src, dst, promotion))
        self.move_history.append((src, dst, promotion))

        if self.turn == "black":
            self.fullmove_number += 1
        self.turn = self.opposite(self.turn)
        return True

    def game_status(self, color_to_move: Optional[str] = None) -> str:
        """Return one of: ongoing, check, checkmate, stalemate."""
        color = color_to_move or self.turn
        legal = self.all_legal_moves(color)
        in_check = self.in_check(color)

        if legal:
            return "check" if in_check else "ongoing"
        return "checkmate" if in_check else "stalemate"
