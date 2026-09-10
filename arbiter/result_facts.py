"""The closed RESULT-facts vocabulary — the consistency linchpin of the freeplay redesign.

The ENGINE resolves a free action (validate existence/reach, roll, apply fx) and emits the GROUND TRUTH as a
compact `;`-separated facts string. The NARRATE call is given a human rendering of these facts and may describe
ONLY them — so the prose can never claim an outcome that didn't happen (no phantom loot, no "spared" on a
refusal). This module is the single definition of that vocabulary + its parser + its Russian renderer.

Pure, deterministic, unit-tested.
"""
from __future__ import annotations

# The CLOSED set of fact keys the engine may emit. Anything outside this set is ignored (and a test guards it).
FACT_KEYS = {
    "tier",            # crit_success | success | failure | crit_failure | none
    "no_target",       # nothing under the cursor to act on (flag)
    "unreachable",     # target too far / no path (flag)
    "nothing_gained",  # a claimed pickup/find yielded nothing (flag)
    "item_gained",     # Name:qty — inventory actually increased
    "item_taken",      # Name — taken from a container/NPC
    "item_given",      # Name — handed to an NPC
    "caps_gained",     # int
    "caps_lost",       # int
    "target_hp",       # signed int — damage/heal actually applied to the target
    "self_hp",         # signed int — to the hero
    "flinch", "down", "ko", "dead",  # target state flags
    "npc",             # aggro | flee | joined | reaction+N | reaction-N
    "mercy",           # yielded | refused
    "combat",          # continues | ends | started
    "object",          # destroyed | opened | used | unchanged
    "consumed",        # Name — an inventory item was spent
    "check",           # free-text transparent roll line (kept verbatim)
    "quest_closed",    # id/title — a promise was turned in
    "quest_registered",# gvar — a quest just crossed its displayThreshold this turn (now tracked in the Pip-Boy)
    "area_revealed",   # area id — a worldmap location was just marked KNOWN this turn
    "party_joined",    # obj id — an NPC just joined the player's party this turn (escort/companion)
    "changes",         # engine-built free-text summary of what materially changed (freeFxLog), ', '-joined
}

_TIER_RU = {
    "crit_success": "критический успех", "success": "успех",
    "failure": "провал", "crit_failure": "критический провал", "none": "без броска",
}


def parse(facts: str) -> list[tuple[str, str]]:
    """`'tier:failure;mercy:refused'` -> [('tier','failure'), ('mercy','refused')]. Unknown keys dropped."""
    out: list[tuple[str, str]] = []
    for tok in (facts or "").split(";"):
        tok = tok.strip()
        if not tok:
            continue
        key, _, val = tok.partition(":")
        key = key.strip().lower()
        if key in FACT_KEYS:
            out.append((key, val.strip()))
    return out


def has(facts: str, key: str) -> bool:
    return any(k == key for k, _ in parse(facts))


def get(facts: str, key: str, default: str = "") -> str:
    for k, v in parse(facts):
        if k == key:
            return v
    return default


def render_ru(facts: str, completion_in_frame: bool = False) -> str:
    """Render the facts as a short Russian ground-truth the NARRATE prompt reads. The model describes THIS.

    Root-caused 2026-07-19: `completion_in_frame` says the SAME turn's frame carries an engine-satisfied
    quest deliverable. These facts describe ONE free-action/dialogue TRANSFER — they are silent about quest
    state — but the closing "nothing happened" / "nothing gained" sentence reads as a verdict on the whole
    turn, and on a turn-in turn it flatly contradicts the completion the frame carries. So the sentence is
    SCOPED (to this action's material transfer) rather than removed: with no completion in frame the output
    is byte-identical to before."""
    parsed = parse(facts)
    _scope = (" Это про ЭТОТ ход и его материальный обмен — оно НЕ отменяет и НЕ ставит под сомнение "
              "завершённое дело из блоков выше." if completion_in_frame else "")
    if not parsed:
        return "Ничего не произошло." + _scope
    lines: list[str] = []
    for key, val in parsed:
        if key == "tier":
            lines.append(f"Исход броска: {_TIER_RU.get(val, val)}.")
        elif key == "no_target":
            lines.append("Под курсором/рукой ничего нет — действовать не на что.")
        elif key == "unreachable":
            lines.append("Слишком далеко — не дотянуться.")
        elif key == "nothing_gained":
            # Neutral: means only "no loot/material change" — NOT "a search for an item came up empty".
            # The old loot framing pushed the narrator to invent a search-the-cabinets scene on plain
            # emotes/gestures. Describe the player's actual intent, not an imagined hunt.
            lines.append("Ничего не получено — никаких материальных изменений." + _scope)
        elif key == "item_gained":
            lines.append(f"ПОЛУЧЕНО в инвентарь: {val}.")
        elif key == "item_taken":
            lines.append(f"Забрано: {val}.")
        elif key == "item_given":
            lines.append(f"Отдано NPC: {val}.")
        elif key == "consumed":
            lines.append(f"Израсходовано: {val}.")
        elif key == "caps_gained":
            lines.append(f"Получено крышек: {val}.")
        elif key == "caps_lost":
            lines.append(f"Отдано крышек: {val}.")
        elif key == "target_hp":
            lines.append(f"Цели нанесено по HP: {val}.")
        elif key == "self_hp":
            lines.append(f"Герою по HP: {val}.")
        elif key in ("flinch", "down", "ko", "dead"):
            lines.append({"flinch": "Цель дёрнулась от удара.", "down": "Цель сбита с ног.",
                          "ko": "Цель без сознания.", "dead": "Цель убита."}[key])
        elif key == "npc":
            lines.append(f"Состояние NPC: {val}.")
        elif key == "mercy":
            lines.append("Враг СОГЛАСИЛСЯ пощадить." if val == "yielded" else "Враг ОТКАЗАЛ в пощаде.")
        elif key == "combat":
            lines.append({"continues": "Бой продолжается.", "ends": "Бой окончен.",
                          "started": "Начался бой."}.get(val, f"Бой: {val}."))
        elif key == "object":
            lines.append({"destroyed": "Объект разрушен.", "opened": "Объект открыт.",
                          "used": "Объект использован.", "unchanged": "Объект цел."}.get(val, f"Объект: {val}."))
        elif key == "quest_closed":
            lines.append(f"Квест закрыт ({val}).")
        elif key == "quest_registered":
            # The quest is NOW tracked in the Pip-Boy as of this turn, so the narrator may confirm it
            # was accepted.
            lines.append("Задание ЗАРЕГИСТРИРОВАНО — теперь оно в Пип-бое (отслеживается).")
        elif key == "area_revealed":
            # A worldmap location was marked KNOWN this turn, so the narrator may confirm it went on the map.
            lines.append("Место ОТМЕЧЕНО на карте мира (теперь видно).")
        elif key == "party_joined":
            # An NPC joined the party this turn, so the narrator may confirm the companion is travelling
            # with the player.
            lines.append("Спутник ПРИСОЕДИНИЛСЯ к отряду.")
        elif key == "changes":
            # Translate the few engine fx-log sub-tokens that carry an outcome the narrator must not invert.
            v2 = (val.replace("party_add=1", "НПС присоединился к отряду")
                     .replace("party_join_refused=charisma_cap",
                              "НПС НЕ присоединился — предел Харизмы достигнут (отряд полон)"))
            lines.append(f"Что изменилось: {v2}.")
        elif key == "check":
            lines.append(f"Проверка: {val}.")
    return " ".join(lines)


def build(*pairs: tuple[str, str]) -> str:
    """Helper for the engine-side/tests: build a facts string from (key, value) pairs (unknown keys skipped)."""
    return ";".join(f"{k}:{v}" if v != "" else k for k, v in pairs if k in FACT_KEYS)
