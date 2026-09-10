"""State coherence: the runtime WORLD-MILESTONE gate. A handful of NPCs share ONE vanilla script across a
major catastrophe (Arroyo before/after the Enclave raid); the .msg distillation flattened both phases into one
present-tense pool, so the brain narrates the END-STATE on first contact. This gate binds such an NPC to a
milestone gvar (the engine surfaces the SET ones in snapshot pc.profile.milestones -> req["milestones"]) and,
while that milestone has NOT fired, swaps the contaminated facts/dossier for a clean BASELINE (pre-milestone).
Once the milestone fires, the original end-state flows again -> no late-game regression.

Engine owns NOW (the gvar), the distillate owns WHO, the AI owns HOW.

Pure read, graceful: no side-car / NPC not gated / milestone already set -> returns inputs unchanged (today's
behaviour). Fail-closed direction: when the live milestone state is UNKNOWN (old engine that doesn't emit the
block -> empty set), a gated NPC degrades to its BASELINE (withholds the unconfirmed catastrophe) rather than
asserting it — the same safe default as the sibling gate that withholds unconfirmed situational context.
"""
from __future__ import annotations

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "milestone_gates.json")
_GATES = None  # lazy, lowercased-by-script


def _load() -> dict:
    global _GATES
    if _GATES is None:
        try:
            with open(_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            _GATES = {k.lower(): v for k, v in raw.items() if not k.startswith("_")}
        except Exception:  # noqa: BLE001 — no side-car -> inert (today's behaviour)
            _GATES = {}
    return _GATES


def reload():
    """Drop the cache (after editing milestone_gates.json, and for tests)."""
    global _GATES
    _GATES = None


def _entry(script: str) -> dict | None:
    return _load().get((script or "").strip().lower().removesuffix(".int"))


def _milestone_set(milestones_csv: str) -> set:
    return {p.strip().lower() for p in str(milestones_csv or "").replace(";", ",").split(",") if p.strip()}


def _baseline_active(script: str, milestones_csv: str) -> dict | None:
    """Return the NPC's gate entry IFF it is gated by a milestone that has NOT fired (so the baseline applies);
    else None (use originals)."""
    e = _entry(script)
    if not e:
        return None
    gate = (e.get("gated_by") or "").strip().lower()
    if not gate:
        return None
    return e if gate not in _milestone_set(milestones_csv) else None


def apply_facts(script: str, facts: dict, milestones_csv: str) -> dict:
    """Overlay the BASELINE structured fields onto `facts` when the gating milestone hasn't fired. Returns a NEW
    dict (never mutates the cached npc_facts entry). Unchanged if not gated / milestone already set."""
    e = _baseline_active(script, milestones_csv)
    if not e or not isinstance(facts, dict):
        return facts
    base = e.get("baseline_facts") or {}
    return {**facts, **base} if base else facts


def apply_dossier(script: str, dossier: str, milestones_csv: str) -> str:
    """Return the clean BASELINE prose dossier when the gating milestone hasn't fired; else the original."""
    e = _baseline_active(script, milestones_csv)
    if not e:
        return dossier
    return e.get("baseline_dossier") or dossier


# --- deterministic self-test (no engine / no LLM): the reported Hakunin bug + the no-regression side --------
if __name__ == "__main__":
    reload()
    e = _entry("AHHakun")
    assert e, "AHHakun must be in milestone_gates.json"

    # 1) FIRST CONTACT (pre-raid): arroyo_captured NOT set -> baseline; NO raid/dying/Navarro content.
    facts = {"health": "тяжело ранен/при смерти после нападения; обожжён", "fear": "что чёрные духи уничтожат народ",
             "knows": "Наварро — место, куда улетели похитители; ГЭКК спасёт деревню"}
    fb = apply_facts("AHHakun", facts, milestones_csv="")
    blob = " ".join(str(v) for v in fb.values()).lower()
    assert "наварро" not in blob and "ранен" not in blob and "обожж" not in blob, f"baseline must be clean: {fb}"
    assert "засух" in fb["fear"].lower(), f"baseline fear should be drought: {fb['fear']!r}"
    db = apply_dossier("AHHakun", "raw dossier with Наварро and умирающим", milestones_csv="")
    assert "наварро" not in db.lower() and "умира" not in db.lower(), "baseline dossier must be clean"
    assert "гэкк" in db.lower() and "засух" in db.lower(), "baseline dossier keeps timeless lore (GECK/drought)"

    # 2) POST-RAID (no regression): arroyo_captured SET -> originals flow untouched.
    fb2 = apply_facts("AHHakun", facts, milestones_csv="arroyo_captured")
    assert fb2 is facts or "наварро" in " ".join(str(v) for v in fb2.values()).lower(), "post-raid keeps end-state"
    db2 = apply_dossier("AHHakun", "raw dossier with Наварро", milestones_csv="arroyo_captured")
    assert "наварро" in db2.lower(), "post-raid keeps end-state dossier"

    # 3) An un-gated NPC is inert (returns inputs unchanged).
    assert apply_facts("ZZNobody", facts, "") is facts
    assert apply_dossier("ZZNobody", "x", "") == "x"

    print("milestone_gate self-test OK")
    print("  baseline fear :", repr(fb["fear"]))
    print("  baseline knows:", repr(fb["knows"]))
