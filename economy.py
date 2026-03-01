"""economy.py

Coins and reward formulas for game outcomes.
"""

from __future__ import annotations

from typing import Dict, Literal

Outcome = Literal["player_win", "bot_win", "draw"]


def calculate_reward(outcome: Outcome, difficulty: int, moves_played: int) -> Dict[str, int]:
    """Return reward mapping for player and bot.

    Reward depends on difficulty and game duration.
    Longer games grant a slight bonus.
    """
    difficulty = max(1, min(5, difficulty))
    duration_bonus = min(30, moves_played // 4)

    if outcome == "player_win":
        player_gain = 40 + difficulty * 25 + duration_bonus
        bot_gain = 0
    elif outcome == "bot_win":
        player_gain = 5 + duration_bonus // 2
        bot_gain = 30 + difficulty * 20
    else:  # draw
        player_gain = 18 + difficulty * 8 + duration_bonus // 2
        bot_gain = 10 + difficulty * 6

    return {"player": player_gain, "bot": bot_gain}


def apply_game_result(profile: dict, outcome: Outcome, difficulty: int, moves_played: int) -> Dict[str, int]:
    """Apply rewards + statistics in-place and return reward details."""
    reward = calculate_reward(outcome, difficulty, moves_played)

    profile["coins"] += reward["player"]
    profile["bot_coins"] += reward["bot"]

    if outcome == "player_win":
        profile["wins"] += 1
    elif outcome == "bot_win":
        profile["losses"] += 1
    else:
        profile["draws"] += 1

    return reward
