"""main.py

Entry point with main menu, chess game loop, profile screen and shop screen.
"""

from __future__ import annotations

import sys
from typing import List, Optional, Tuple

import pygame

from board import ChessBoard, Move
from bot_engine import BotSettings, ChessBot
from economy import apply_game_result
from profile import load_profile, save_profile
from shop import ShopItem, apply_selection, catalog_by_category, purchase_item
from ui import UI


class GameApp:
    def __init__(self) -> None:
        self.ui = UI()
        self.profile = load_profile()
        self.state = "menu"  # menu | game | shop | profile | game_over

        # Runtime game state
        self.board: Optional[ChessBoard] = None
        self.bot: Optional[ChessBot] = None
        self.selected: Optional[Tuple[int, int]] = None
        self.legal_moves: List[Tuple[int, int]] = []
        self.last_result_text: str = ""
        self.last_reward_text: str = ""

        # Shop UI
        self.shop_category_keys = ["board", "piece_skin", "theme", "difficulty"]
        self.shop_category_idx = 0

    def run(self) -> None:
        while True:
            if self.state == "menu":
                self.loop_menu()
            elif self.state == "game":
                self.loop_game()
            elif self.state == "shop":
                self.loop_shop()
            elif self.state == "profile":
                self.loop_profile()
            elif self.state == "game_over":
                self.loop_game_over()

    def _handle_quit(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            save_profile(self.profile)
            pygame.quit()
            sys.exit(0)

    def loop_menu(self) -> None:
        theme = self.ui.clear(self.profile["selected_theme"])

        title_rect = self.ui.draw_text("Шахматы с ботом", self.ui.width // 2, 70, theme["text"], center=True)
        self.ui.draw_text(f"Coins: {self.profile['coins']}", self.ui.width - 160, 20, theme["text"], small=True)

        buttons = [
            ("Новая игра", pygame.Rect(self.ui.width // 2 - 160, 160, 320, 60), "start"),
            ("Магазин", pygame.Rect(self.ui.width // 2 - 160, 240, 320, 60), "shop"),
            ("Профиль", pygame.Rect(self.ui.width // 2 - 160, 320, 320, 60), "profile"),
            ("Выход", pygame.Rect(self.ui.width // 2 - 160, 400, 320, 60), "exit"),
        ]

        mouse = pygame.mouse.get_pos()
        for text, rect, _action in buttons:
            self.ui.draw_button(text, rect, theme, rect.collidepoint(mouse))

        pygame.display.flip()

        for event in pygame.event.get():
            self._handle_quit(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for _text, rect, action in buttons:
                    if rect.collidepoint(event.pos):
                        if action == "start":
                            self.start_new_game()
                        elif action == "shop":
                            self.state = "shop"
                        elif action == "profile":
                            self.state = "profile"
                        elif action == "exit":
                            save_profile(self.profile)
                            pygame.quit()
                            sys.exit(0)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                save_profile(self.profile)
                pygame.quit()
                sys.exit(0)

        self.ui.tick()

    def start_new_game(self) -> None:
        self.board = ChessBoard()
        difficulty = self.profile.get("selected_difficulty", 2)
        self.bot = ChessBot("black", BotSettings(depth=difficulty))
        self.selected = None
        self.legal_moves = []
        self.last_result_text = ""
        self.last_reward_text = ""
        self.state = "game"

    def loop_game(self) -> None:
        assert self.board is not None and self.bot is not None

        theme = self.ui.clear(self.profile["selected_theme"])
        board_rect = self.ui.draw_board(
            self.board,
            self.selected,
            self.legal_moves,
            self.profile["selected_board"],
            self.profile["selected_piece_skin"],
            top_left=(40, 40),
        )

        status = self.board.game_status()
        info = [
            f"Ход: {'Белые (Игрок)' if self.board.turn == 'white' else 'Черные (Бот)'}",
            f"Статус: {status}",
            f"Сложность бота: {self.profile['selected_difficulty']}",
            f"Coins: {self.profile['coins']}",
            "ESC: в меню",
            "R: новая партия",
        ]

        self.ui.draw_info_panel(pygame.Rect(680, 60, 250, 240), theme, info)

        pygame.display.flip()

        # Endgame check
        if status in ("checkmate", "stalemate"):
            self.finish_game(status)
            return

        for event in pygame.event.get():
            self._handle_quit(event)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    return
                if event.key == pygame.K_r:
                    self.start_new_game()
                    return

            if self.board.turn == "white" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_player_click(event.pos, board_rect)

        # Bot moves after player's actions
        if self.board.turn == "black":
            bot_move = self.bot.choose_move(self.board)
            if bot_move is None:
                self.finish_game(self.board.game_status())
                return
            self.board.make_move(bot_move)
            self.selected = None
            self.legal_moves = []

        self.ui.tick(30)

    def handle_player_click(self, pos: Tuple[int, int], board_rect: pygame.Rect) -> None:
        assert self.board is not None
        cell = self.ui.board_coord_from_mouse(pos, board_rect)
        if cell is None:
            self.selected = None
            self.legal_moves = []
            return

        if self.selected and cell in self.legal_moves:
            src = self.selected
            dst = cell
            piece = self.board.get_piece(src)
            promotion = "Q"
            if piece and piece.kind == "P" and dst[0] == 0:
                # Beginner-friendly: always auto-promote to queen.
                promotion = "Q"
            moved = self.board.make_move((src, dst, promotion))
            if moved:
                self.selected = None
                self.legal_moves = []
            return

        piece = self.board.get_piece(cell)
        if piece and piece.color == "white" and self.board.turn == "white":
            self.selected = cell
            self.legal_moves = self.board.legal_moves_for_piece(cell)
        else:
            self.selected = None
            self.legal_moves = []

    def finish_game(self, status: str) -> None:
        assert self.board is not None
        if status == "stalemate":
            outcome = "draw"
            result_text = "Ничья (пат)"
        else:
            # side to move got checkmated
            loser = self.board.turn
            if loser == "black":
                outcome = "player_win"
                result_text = "Вы победили! (мат)"
            else:
                outcome = "bot_win"
                result_text = "Победил бот (мат)"

        reward = apply_game_result(
            self.profile,
            outcome=outcome,
            difficulty=self.profile["selected_difficulty"],
            moves_played=len(self.board.move_history),
        )
        save_profile(self.profile)

        self.last_result_text = result_text
        self.last_reward_text = f"Награда: игрок +{reward['player']} coins, бот +{reward['bot']}"
        self.state = "game_over"

    def loop_game_over(self) -> None:
        theme = self.ui.clear(self.profile["selected_theme"])
        self.ui.draw_text("Конец партии", self.ui.width // 2, 120, theme["text"], center=True)
        self.ui.draw_text(self.last_result_text, self.ui.width // 2, 190, theme["text"], center=True)
        self.ui.draw_text(self.last_reward_text, self.ui.width // 2, 240, theme["text"], center=True, small=True)
        self.ui.draw_text(f"Текущий баланс: {self.profile['coins']} coins", self.ui.width // 2, 280, theme["text"], center=True)

        btn_menu = pygame.Rect(self.ui.width // 2 - 180, 360, 360, 60)
        btn_new = pygame.Rect(self.ui.width // 2 - 180, 440, 360, 60)
        mouse = pygame.mouse.get_pos()
        self.ui.draw_button("В главное меню", btn_menu, theme, btn_menu.collidepoint(mouse))
        self.ui.draw_button("Сыграть снова", btn_new, theme, btn_new.collidepoint(mouse))

        pygame.display.flip()

        for event in pygame.event.get():
            self._handle_quit(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_menu.collidepoint(event.pos):
                    self.state = "menu"
                    return
                if btn_new.collidepoint(event.pos):
                    self.start_new_game()
                    return

        self.ui.tick()

    def loop_profile(self) -> None:
        theme = self.ui.clear(self.profile["selected_theme"])
        self.ui.draw_text("Профиль игрока", self.ui.width // 2, 70, theme["text"], center=True)

        lines = [
            f"Имя: {self.profile['name']}",
            f"Coins: {self.profile['coins']}",
            f"Победы: {self.profile['wins']}",
            f"Поражения: {self.profile['losses']}",
            f"Ничьи: {self.profile['draws']}",
            f"Coins бота (статистика): {self.profile['bot_coins']}",
            f"Доска: {self.profile['selected_board']}",
            f"Скин фигур: {self.profile['selected_piece_skin']}",
            f"Тема: {self.profile['selected_theme']}",
            f"Сложность: {self.profile['selected_difficulty']}",
        ]
        y = 130
        for line in lines:
            self.ui.draw_text(line, 160, y, theme["text"])
            y += 38

        btn_back = pygame.Rect(self.ui.width // 2 - 150, 620, 300, 52)
        mouse = pygame.mouse.get_pos()
        self.ui.draw_button("Назад", btn_back, theme, btn_back.collidepoint(mouse))

        pygame.display.flip()

        for event in pygame.event.get():
            self._handle_quit(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = "menu"
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and btn_back.collidepoint(event.pos):
                self.state = "menu"
                return

        self.ui.tick()

    def loop_shop(self) -> None:
        theme = self.ui.clear(self.profile["selected_theme"])
        catalog = catalog_by_category()
        category = self.shop_category_keys[self.shop_category_idx]

        self.ui.draw_text("Магазин", self.ui.width // 2, 45, theme["text"], center=True)
        self.ui.draw_text(f"Coins: {self.profile['coins']}", self.ui.width - 180, 20, theme["text"], small=True)

        # Category tabs
        tabs = []
        names = {"board": "Доски", "piece_skin": "Скины", "theme": "Темы", "difficulty": "Сложность"}
        x = 70
        for idx, key in enumerate(self.shop_category_keys):
            rect = pygame.Rect(x, 90, 180, 45)
            tabs.append((key, rect))
            self.ui.draw_button(names[key], rect, theme, idx == self.shop_category_idx)
            x += 200

        items: List[ShopItem] = catalog[category]
        item_rects = []
        y = 170
        for item in items:
            rect = pygame.Rect(70, y, 820, 70)
            item_rects.append((item, rect))
            pygame.draw.rect(self.ui.screen, theme["panel"], rect, border_radius=8)
            pygame.draw.rect(self.ui.screen, theme["text"], rect, 2, border_radius=8)

            owned = self._is_owned(item)
            selected = self._is_selected(item)
            status = "Выбрано" if selected else ("Куплено" if owned else f"Цена: {item.price}")

            self.ui.draw_text(item.title, rect.x + 14, rect.y + 12, theme["text"])
            self.ui.draw_text(status, rect.right - 220, rect.y + 22, theme["text"], small=True)
            y += 84

        btn_back = pygame.Rect(self.ui.width // 2 - 150, 640, 300, 46)
        self.ui.draw_button("Назад в меню", btn_back, theme)

        pygame.display.flip()

        for event in pygame.event.get():
            self._handle_quit(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                save_profile(self.profile)
                self.state = "menu"
                return

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_back.collidepoint(event.pos):
                    save_profile(self.profile)
                    self.state = "menu"
                    return

                for idx, (_key, rect) in enumerate(tabs):
                    if rect.collidepoint(event.pos):
                        self.shop_category_idx = idx
                        break

                for item, rect in item_rects:
                    if rect.collidepoint(event.pos):
                        self._shop_click_item(item)
                        save_profile(self.profile)
                        break

        self.ui.tick()

    def _is_owned(self, item: ShopItem) -> bool:
        if item.category == "board":
            return item.item_id in self.profile["owned_boards"]
        if item.category == "piece_skin":
            return item.item_id in self.profile["owned_piece_skins"]
        if item.category == "theme":
            return item.item_id in self.profile["owned_themes"]
        if item.category == "difficulty":
            level = int(item.item_id.split("_")[1])
            return level in self.profile["unlocked_difficulties"]
        return False

    def _is_selected(self, item: ShopItem) -> bool:
        if item.category == "board":
            return self.profile["selected_board"] == item.item_id
        if item.category == "piece_skin":
            return self.profile["selected_piece_skin"] == item.item_id
        if item.category == "theme":
            return self.profile["selected_theme"] == item.item_id
        if item.category == "difficulty":
            level = int(item.item_id.split("_")[1])
            return self.profile["selected_difficulty"] == level
        return False

    def _shop_click_item(self, item: ShopItem) -> None:
        owned = self._is_owned(item)
        if not owned:
            purchase_item(self.profile, item)
            return

        apply_selection(self.profile, item.category, item.item_id)


if __name__ == "__main__":
    app = GameApp()
    app.run()
