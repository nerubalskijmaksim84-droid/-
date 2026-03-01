"""bot_engine.py

Deterministic chess bot using Minimax + Alpha-Beta pruning.
No randomness and no ML/API usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from board import ChessBoard, Move


@dataclass
class BotSettings:
    depth: int = 2


class ChessBot:
    """Classic search-based chess bot.

    The bot evaluates positions with a handcrafted heuristic and chooses the
    move that maximizes its score.
    """

    piece_values: Dict[str, int] = {
        "P": 100,
        "N": 320,
        "B": 330,
        "R": 500,
        "Q": 900,
        "K": 20000,
    }

    def __init__(self, color: str, settings: Optional[BotSettings] = None) -> None:
        self.color = color
        self.settings = settings or BotSettings()

    @staticmethod
    def opponent(color: str) -> str:
        return "black" if color == "white" else "white"

    def choose_move(self, board: ChessBoard) -> Optional[Move]:
        """Pick best move via minimax search."""
        depth = max(1, min(5, self.settings.depth))
        moves = board.all_legal_moves(self.color)
        if not moves:
            return None

        best_move: Optional[Move] = None
        best_score = float("-inf")
        alpha = float("-inf")
        beta = float("inf")

        # Deterministic ordering: sort moves lexicographically for stable choices.
        moves = sorted(moves, key=lambda m: (m[0][0], m[0][1], m[1][0], m[1][1], m[2] or ""))

        for move in moves:
            child = board.clone()
            child.make_move(move)
            score = self._minimax(child, depth - 1, alpha, beta, maximizing=False)
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)

        return best_move

    def _minimax(self, board: ChessBoard, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
        to_move = self.color if maximizing else self.opponent(self.color)
        status = board.game_status(color_to_move=to_move)

        if status == "checkmate":
            return -999999 if to_move == self.color else 999999
        if status == "stalemate":
            return 0

        if depth == 0:
            return self.evaluate(board)

        legal = board.all_legal_moves(to_move)
        if not legal:
            return self.evaluate(board)

        legal = sorted(legal, key=lambda m: (m[0][0], m[0][1], m[1][0], m[1][1], m[2] or ""))

        if maximizing:
            value = float("-inf")
            for mv in legal:
                child = board.clone()
                child.make_move(mv)
                value = max(value, self._minimax(child, depth - 1, alpha, beta, False))
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value

        value = float("inf")
        for mv in legal:
            child = board.clone()
            child.make_move(mv)
            value = min(value, self._minimax(child, depth - 1, alpha, beta, True))
            beta = min(beta, value)
            if alpha >= beta:
                break
        return value

    def evaluate(self, board: ChessBoard) -> float:
        """Heuristic evaluation with material + simple positional factors.

        Positive score means advantage for bot color.
        """
        score = 0.0

        # 1) Material
        for r in range(8):
            for c in range(8):
                p = board.board[r][c]
                if not p:
                    continue
                val = self.piece_values[p.kind]
                score += val if p.color == self.color else -val

        # 2) Center control (d4,e4,d5,e5 squares and nearby influence)
        center = {(3, 3), (3, 4), (4, 3), (4, 4)}
        for sq in center:
            if board.is_square_attacked(sq, self.color):
                score += 12
            if board.is_square_attacked(sq, self.opponent(self.color)):
                score -= 12

        # 3) King safety: penalize being in check and reward castled king shape
        if board.in_check(self.color):
            score -= 80
        if board.in_check(self.opponent(self.color)):
            score += 80

        # Bonus if king is castled-like position (g-file or c-file)
        my_king = board.find_king(self.color)
        op_king = board.find_king(self.opponent(self.color))
        if my_king in [(7, 6), (7, 2), (0, 6), (0, 2)]:
            score += 25
        if op_king in [(7, 6), (7, 2), (0, 6), (0, 2)]:
            score -= 25

        # 4) Mobility / positional simplicity
        my_moves = len(board.all_legal_moves(self.color))
        op_moves = len(board.all_legal_moves(self.opponent(self.color)))
        score += 2 * (my_moves - op_moves)

        return score
