"""shop.py

In-game store definitions and purchase/apply helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ShopItem:
    item_id: str
    title: str
    category: str
    price: int


BOARD_ITEMS = [
    ShopItem("classic", "Classic Board", "board", 0),
    ShopItem("walnut", "Walnut Board", "board", 180),
    ShopItem("emerald", "Emerald Board", "board", 220),
]

PIECE_SKINS = [
    ShopItem("classic", "Classic Pieces", "piece_skin", 0),
    ShopItem("neo", "Neo Pieces", "piece_skin", 150),
    ShopItem("pixel", "Pixel Pieces", "piece_skin", 170),
]

THEMES = [
    ShopItem("light", "Light UI", "theme", 0),
    ShopItem("dark", "Dark UI", "theme", 130),
    ShopItem("violet", "Violet UI", "theme", 140),
]

DIFFICULTY_UNLOCKS = [
    ShopItem("difficulty_1", "Difficulty 1", "difficulty", 0),
    ShopItem("difficulty_2", "Difficulty 2", "difficulty", 0),
    ShopItem("difficulty_3", "Difficulty 3", "difficulty", 200),
    ShopItem("difficulty_4", "Difficulty 4", "difficulty", 300),
    ShopItem("difficulty_5", "Difficulty 5", "difficulty", 450),
]


def all_items() -> List[ShopItem]:
    return BOARD_ITEMS + PIECE_SKINS + THEMES + DIFFICULTY_UNLOCKS


def _owned_list_key(category: str) -> str:
    return {
        "board": "owned_boards",
        "piece_skin": "owned_piece_skins",
        "theme": "owned_themes",
    }.get(category, "")


def purchase_item(profile: dict, item: ShopItem) -> Tuple[bool, str]:
    """Attempt to buy item. Returns (success, message)."""
    if item.category in ("board", "piece_skin", "theme"):
        owned_key = _owned_list_key(item.category)
        if item.item_id in profile[owned_key]:
            return False, "Уже куплено"
    elif item.category == "difficulty":
        level = int(item.item_id.split("_")[1])
        if level in profile["unlocked_difficulties"]:
            return False, "Уровень уже открыт"

    if profile["coins"] < item.price:
        return False, "Недостаточно coins"

    profile["coins"] -= item.price

    if item.category in ("board", "piece_skin", "theme"):
        profile[_owned_list_key(item.category)].append(item.item_id)
    elif item.category == "difficulty":
        level = int(item.item_id.split("_")[1])
        profile["unlocked_difficulties"].append(level)
        profile["unlocked_difficulties"] = sorted(set(profile["unlocked_difficulties"]))

    return True, f"Куплено: {item.title}"


def apply_selection(profile: dict, category: str, item_id: str) -> Tuple[bool, str]:
    """Apply a purchased cosmetic/option as current selection."""
    if category == "board":
        if item_id not in profile["owned_boards"]:
            return False, "Доска не куплена"
        profile["selected_board"] = item_id
        return True, "Доска применена"

    if category == "piece_skin":
        if item_id not in profile["owned_piece_skins"]:
            return False, "Скин фигур не куплен"
        profile["selected_piece_skin"] = item_id
        return True, "Скин фигур применен"

    if category == "theme":
        if item_id not in profile["owned_themes"]:
            return False, "Тема не куплена"
        profile["selected_theme"] = item_id
        return True, "Тема интерфейса применена"

    if category == "difficulty":
        level = int(item_id.split("_")[1])
        if level not in profile["unlocked_difficulties"]:
            return False, "Сложность не открыта"
        profile["selected_difficulty"] = level
        return True, "Сложность выбрана"

    return False, "Неизвестная категория"


def catalog_by_category() -> Dict[str, List[ShopItem]]:
    return {
        "board": BOARD_ITEMS,
        "piece_skin": PIECE_SKINS,
        "theme": THEMES,
        "difficulty": DIFFICULTY_UNLOCKS,
    }
