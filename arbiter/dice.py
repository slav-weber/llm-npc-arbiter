"""A skill check on Fallout's native d100 system, graded into four outcomes.

This is the REFERENCE implementation in Python — it exists so the brain can be debugged apart from
the game, against a fake character. Inside the game the engine (C++) does the same thing with the
player's REAL stats via statGetValue / skillGetValue. The two formulas have to agree.

The model:
  base   = the player's real ability in % (a skill as-is; a SPECIAL stat = stat * 10)
  chance = clamp(base - difficulty_penalty, 5, 95)   # always leave a window for a miracle or a fumble
  roll d100 (1 is the best); margin = chance - roll
  crit success : margin >= CRIT_MARGIN or roll <= 5
  success      : roll <= chance
  failure      : roll >  chance
  crit failure : -margin >= CRIT_MARGIN or roll >= 96
"""
import random

SPECIAL = {"STR", "PER", "END", "CHA", "INT", "AGI", "LCK"}
CRIT_MARGIN = 50


def base_chance(check: str, skill_name: str, character: dict) -> int:
    """The base chance in %, taken from the character's real ability."""
    if check == "none":
        return 95
    if check in SPECIAL:
        return character.get("special", {}).get(check, 5) * 10  # stat 1..10 -> %
    if check == "skill":
        return character.get("skills", {}).get(skill_name, 0)    # a skill is already a %
    return 50


def difficulty_penalty(difficulty) -> int:
    """1 (easy) -> no penalty … 10 (near-impossible) -> a 90-point penalty."""
    try:
        d = int(difficulty)
    except (TypeError, ValueError):
        d = 5
    return max(0, (d - 1) * 10)


def roll_check(check: str, skill_name: str, difficulty, character: dict, rng=random) -> dict:
    base = base_chance(check, skill_name, character)
    chance = max(5, min(95, base - difficulty_penalty(difficulty)))
    roll = rng.randint(1, 100)
    margin = chance - roll
    if roll <= chance:
        outcome = "crit_success" if (margin >= CRIT_MARGIN or roll <= 5) else "success"
    else:
        outcome = "crit_failure" if (-margin >= CRIT_MARGIN or roll >= 96) else "failure"
    return {"outcome": outcome, "roll": roll, "chance": chance, "base": base}
