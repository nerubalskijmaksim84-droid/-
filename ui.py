"""ui.py

Pygame rendering helpers for menu, board, and screens.
"""

from __future__ import annotations

import pygame
from typing import Dict, List, Optional, Tuple

from board import ChessBoard

Position = Tuple[int, int]

BOARD_PALETTES = {
    "classic": ((240, 217, 181), (181, 136, 99)),
    "walnut": ((234, 214, 184), (119, 78, 55)),
    "emerald": ((220, 235, 220), (70, 140, 110)),
}

THEMES = {
    "light": {"bg": (245, 245, 245), "text": (20, 20, 20), "panel": (225, 225, 225), "accent": (40, 110, 220)},
    "dark": {"bg": (28, 30, 34), "text": (238, 238, 238), "panel": (47, 50, 56), "accent": (88, 150, 255)},
    "violet": {"bg": (41, 32, 52), "text": (241, 236, 250), "panel": (70, 55, 88), "accent": (185, 120, 255)},
}

PIECE_GLYPHS = {
    "K": "♔",
    "Q": "♕",
    "R": "♖",
    "B": "♗",
    "N": "♘",
    "P": "♙",
}


class UI:
    def __init__(self, width: int = 960, height: int = 720):
        pygame.init()
        pygame.display.set_caption("Шахматы с ботом")
        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()
        self.width = width
        self.height = height

        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 18)
        self.piece_font = pygame.font.SysFont("dejavusans", 56)

    def tick(self, fps: int = 60) -> None:
        self.clock.tick(fps)

    def clear(self, theme_id: str) -> Dict[str, Tuple[int, int, int]]:
        theme = THEMES.get(theme_id, THEMES["light"])
        self.screen.fill(theme["bg"])
        return theme

    def draw_text(self, text: str, x: int, y: int, color=(0, 0, 0), center: bool = False, small: bool = False) -> pygame.Rect:
        font = self.small_font if small else self.font
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        self.screen.blit(surf, rect)
        return rect

    def draw_button(self, text: str, rect: pygame.Rect, theme: dict, hovered: bool = False) -> None:
        color = theme["accent"] if hovered else theme["panel"]
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, theme["text"], rect, 2, border_radius=8)
        self.draw_text(text, rect.centerx, rect.centery, theme["text"], center=True)

    def draw_board(
        self,
        board: ChessBoard,
        selected: Optional[Position],
        legal_moves: List[Position],
        selected_board: str,
        selected_piece_skin: str,
        top_left: Tuple[int, int] = (40, 40),
        cell_size: int = 76,
    ) -> pygame.Rect:
        """Draw board, pieces, selected piece, legal-move markers.

        Returns board rectangle for click hit-testing.
        """
        x0, y0 = top_left
        light, dark = BOARD_PALETTES.get(selected_board, BOARD_PALETTES["classic"])

        board_rect = pygame.Rect(x0, y0, cell_size * 8, cell_size * 8)

        for r in range(8):
            for c in range(8):
                cell = pygame.Rect(x0 + c * cell_size, y0 + r * cell_size, cell_size, cell_size)
                color = light if (r + c) % 2 == 0 else dark
                pygame.draw.rect(self.screen, color, cell)

                if selected == (r, c):
                    pygame.draw.rect(self.screen, (255, 215, 0), cell, 4)

                if (r, c) in legal_moves:
                    marker = pygame.Rect(cell.centerx - 8, cell.centery - 8, 16, 16)
                    pygame.draw.ellipse(self.screen, (30, 170, 70), marker)

                piece = board.board[r][c]
                if piece:
                    self._draw_piece(piece.kind, piece.color, cell.centerx, cell.centery, selected_piece_skin)

        pygame.draw.rect(self.screen, (20, 20, 20), board_rect, 3)
        return board_rect

    def _draw_piece(self, kind: str, color: str, x: int, y: int, skin: str) -> None:
        """Draw unicode piece with small style tweaks per skin."""
        glyph = PIECE_GLYPHS[kind]
        text = glyph if color == "white" else glyph.translate(str.maketrans("♔♕♖♗♘♙", "♚♛♜♝♞♟"))

        if skin == "pixel":
            fg = (240, 240, 240) if color == "white" else (35, 35, 35)
            shadow = self.piece_font.render(text, True, (0, 0, 0))
            srect = shadow.get_rect(center=(x + 2, y + 2))
            self.screen.blit(shadow, srect)
        elif skin == "neo":
            fg = (230, 230, 245) if color == "white" else (25, 35, 55)
        else:
            fg = (250, 250, 250) if color == "white" else (10, 10, 10)

        surf = self.piece_font.render(text, True, fg)
        rect = surf.get_rect(center=(x, y))
        self.screen.blit(surf, rect)

    def draw_info_panel(self, rect: pygame.Rect, theme: dict, lines: List[str]) -> None:
        pygame.draw.rect(self.screen, theme["panel"], rect, border_radius=8)
        pygame.draw.rect(self.screen, theme["text"], rect, 2, border_radius=8)
        y = rect.y + 14
        for line in lines:
            self.draw_text(line, rect.x + 12, y, theme["text"], small=True)
            y += 26

    def board_coord_from_mouse(
        self, mouse_pos: Tuple[int, int], board_rect: pygame.Rect, cell_size: int = 76
    ) -> Optional[Position]:
        x, y = mouse_pos
        if not board_rect.collidepoint(x, y):
            return None
        col = (x - board_rect.x) // cell_size
        row = (y - board_rect.y) // cell_size
        return (row, col)
