"""The invariant predicates the gate resolves by name.

`atom_gate` is the mechanism and knows nothing about any particular atom: it refuses to commit an
atom whose declared invariant name does not resolve to a registered predicate. This module is the
other half — the predicates themselves, in two tiers:

1. **Generic**, atom-agnostic: they read the atom's own effect and guard out of the commit context,
   so any atom can declare them. `monotonic`, `idempotent_from_zero`, `guard_consistent` and
   `skills_only` are of this kind.
2. **Quest-specific**: the named invariants one escort quest declares, which hardcode that quest's
   variable indices. They are kept verbatim, because their whole point is that a designer wrote
   down what must never happen to that quest.

Registration is idempotent and cheap, so a caller may do it once per turn.

Extracted, unchanged in behaviour, from the mod's dialogue layer, which is where these predicates
were registered before the arbiter was carved out into a standalone package.
"""
from __future__ import annotations

from . import atom_gate

# The escort quest's variables: Q = quest stage, D = the escorted NPC is dead, E = the town turned
# hostile, M = the NPC is missing from the map, S = the quest's success flag.
_Q, _D, _E, _M, _S = 182, 70, 203, 71, 85


def _mut(ctx) -> dict:
    return dict(ctx.get("mutations") or [])


def register_predicates() -> None:
    """Register every invariant predicate into the gate. Safe to call repeatedly."""
    r = atom_gate.register_invariant

    # --- 1. Generic, atom-agnostic: derived from the atom's own mutations and guard -------------
    # A quest variable may only move forward. Written as "the value before is not greater than the
    # value this atom would write", so an atom that rewinds a quest is rejected before any write.
    r("monotonic", lambda c: all(c["before"].get(i, 0) <= v for i, v in c["mutations"]))

    # The atom fires only from the untouched state, so replaying it cannot advance anything twice.
    r("idempotent_from_zero", lambda c: all(c["before"].get(i, 0) == 0 for i, _v in c["mutations"]))

    # Backstop: re-assert the atom's full durable guard as an invariant. The guard is evaluated once
    # before the invariants, so this looks redundant — it is deliberate. It means every variable the
    # designer named in the guard (including flags such as "the town is hostile") is also an
    # invariant, and a future change to the firing path cannot quietly bypass it.
    r("guard_consistent",
      lambda c: (not ((c["atom"].get("guard") or {}).get("durable"))
                 or atom_gate.guard_holds(((c["atom"].get("guard") or {}).get("durable")),
                                          c["before"], c.get("before_map"), c.get("before_local"),
                                          c.get("before_party"))))

    # A teacher atom must be exactly a skill raise: no quest variable, procedure, map or local
    # variable, or timestamp may ride along, and each amount must be within the teaching range.
    # Without this the invariant list of a teacher would be vacuous — every declared predicate would
    # be trivially true — and "the atom declares invariants" would stop meaning anything.
    def _skills_only(c):
        eff = c["atom"].get("effect") or {}
        if (not eff.get("skills") or eff.get("data_delta") or eff.get("proc")
                or eff.get("map_vars") or eff.get("local_vars") or eff.get("stamp_time")):
            return False
        return all(1 <= p <= 20 for _s, p in atom_gate.parse_skill_trains(c["atom"]))

    r("skills_only", _skills_only)

    # --- 2. The escort quest's own invariants, verbatim -----------------------------------------
    r("monotonic_Q", lambda c: c["before"].get(_Q, 0) <= _mut(c).get(_Q, c["before"].get(_Q, 0)))
    # Accepting sets the quest to stage 1 and never to 2: stage 2 is earned at the destination.
    r("no_skip_to_2", lambda c: _mut(c).get(_Q, 0) != 2)
    # The atom must never touch the success flag — that is the reward, and it is not the atom's.
    r("reward_iff_started", lambda c: _S not in _mut(c))
    r("not_if_dead", lambda c: c["before"].get(_D, 0) == 0)
    r("not_if_enemy", lambda c: c["before"].get(_E, 0) == 0)
    r("not_if_missing", lambda c: c["before"].get(_M, 0) == 0)
    # Fire only from an untouched quest, so a repeated agreement cannot teleport the player twice.
    r("idempotent", lambda c: c["before"].get(_Q, 0) == 0)
