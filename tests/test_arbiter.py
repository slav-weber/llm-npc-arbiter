"""What the arbiter guarantees, asserted without an engine, a model or a network.

Run with either runner:

    python -m unittest discover -s tests -q
    pytest -q
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adversarial import hostile_runs                      # noqa: E402
from arbiter import atom_gate, dice, invariants, ledger    # noqa: E402


class Registry(unittest.TestCase):
    """The whitelist is loaded fail-closed: a malformed atom is rejected loudly, never stamped."""

    def setUp(self):
        atom_gate.reload()
        invariants.register_predicates()

    def test_every_shipped_atom_loads(self):
        self.assertTrue(atom_gate.active_atoms(), "the registry must not be empty")
        self.assertEqual(atom_gate.rejects(), [], "a shipped atom failed schema validation")

    def test_every_declared_invariant_resolves(self):
        for atom_id, atom in atom_gate.active_atoms().items():
            for name in atom.get("invariants") or []:
                with self.subTest(atom=atom_id, invariant=name):
                    rec = hostile_runs.Recorder({})
                    result = atom_gate.commit_effect(atom, {}, rec)
                    self.assertNotIn("unresolved invariant", result.reason,
                                     f"{atom_id} declares an invariant nobody registered")

    def test_no_atom_declares_an_empty_invariant_list(self):
        for atom_id, atom in atom_gate.active_atoms().items():
            with self.subTest(atom=atom_id):
                self.assertTrue(atom.get("invariants"),
                                f"{atom_id} would commit with nothing to check")


class Chokepoint(unittest.TestCase):
    """A refused turn must not reach the write site at all — not write and roll back."""

    def setUp(self):
        atom_gate.reload()
        atom_gate.reset_halt()
        invariants.register_predicates()
        self.atoms = atom_gate.active_atoms()

    def test_the_honest_turn_commits(self):
        atom = self.atoms["klamath_ratgod_accept"]
        rec = hostile_runs.Recorder({390: 0, 68: 0})
        result = atom_gate.commit_effect(atom, {390: 0, 68: 0}, rec)
        self.assertTrue(result.committed, result.reason)
        self.assertEqual(rec.writes, [(390, 1)])

    def test_a_refused_turn_never_calls_the_applier(self):
        atom = self.atoms["klamath_ratgod_accept"]
        rec = hostile_runs.Recorder({390: 2, 68: 0})          # the quest is already finished
        result = atom_gate.commit_effect(atom, {390: 2, 68: 0}, rec)
        self.assertFalse(result.committed)
        self.assertFalse(rec.touched, "a rejected atom reached the write site")

    def test_an_unknown_invariant_is_fail_closed(self):
        atom = json.loads(json.dumps(self.atoms["klamath_ratgod_accept"]))
        atom["invariants"] = ["a_predicate_nobody_registered"]
        rec = hostile_runs.Recorder({390: 0, 68: 0})
        result = atom_gate.commit_effect(atom, {390: 0, 68: 0}, rec)
        self.assertFalse(result.committed)
        self.assertFalse(rec.touched)

    def test_an_inactive_atom_is_inert(self):
        atom = json.loads(json.dumps(self.atoms["klamath_ratgod_accept"]))
        atom["active"] = False
        rec = hostile_runs.Recorder({390: 0, 68: 0})
        self.assertFalse(atom_gate.commit_effect(atom, {390: 0, 68: 0}, rec).committed)
        self.assertFalse(rec.touched)

    def test_removing_an_invariant_lets_the_attack_through(self):
        """A mutation test: with the invariant deleted, the hostile turn succeeds.

        Without this the suite would pass just as happily if the invariants did nothing at all.
        """
        atom = json.loads(json.dumps(self.atoms["torr_guard_brahmin_accept"]))
        atom["effect"] = {**atom["effect"], "data_delta": ["set gvar 182 = 1", "set gvar 85 = 1"]}
        before = {182: 0, 70: 0, 203: 0, 71: 0, 85: 0}

        guarded = hostile_runs.Recorder(before)
        self.assertFalse(atom_gate.commit_effect(atom, dict(before), guarded).committed)
        self.assertFalse(guarded.touched)

        atom["invariants"] = [n for n in atom["invariants"] if n != "reward_iff_started"]
        unguarded = hostile_runs.Recorder(before)
        result = atom_gate.commit_effect(atom, dict(before), unguarded)
        self.assertTrue(result.committed, "the guard removal should expose the attack")
        self.assertIn((85, 1), unguarded.writes)


class Ledger(unittest.TestCase):
    """Durable state the model influences is validated against a declared registry."""

    def test_an_undeclared_domain_is_dropped(self):
        mem: dict = {}
        self.assertFalse(ledger.apply_state_set(mem, "player_powers:hero:invincible=true"))
        self.assertFalse(mem.get("ledger"))

    def test_a_value_outside_the_enumeration_is_dropped(self):
        mem: dict = {}
        self.assertFalse(ledger.apply_state_set(mem, "faction_stance:ncr:stance=adores_the_player"))
        self.assertFalse(mem.get("ledger"))

    def test_validate_reports_the_reason(self):
        ok, reason = ledger.validate("faction_stance", "stance", "adores_the_player")
        self.assertFalse(ok)
        self.assertTrue(reason)


class Dice(unittest.TestCase):
    """The outcome grade is rolled by code, inside a clamp, for every difficulty and skill."""

    def test_the_chance_stays_inside_the_clamp(self):
        for difficulty in range(0, 11):
            for skill in (0, 20, 40, 60, 80, 100, 300):
                with self.subTest(difficulty=difficulty, skill=skill):
                    chance = dice.roll_check("skill", "Speech", difficulty,
                                             {"skills": {"Speech": skill}})["chance"]
                    self.assertGreaterEqual(chance, 5)
                    self.assertLessEqual(chance, 95)

    def test_the_outcome_is_one_of_the_four_grades(self):
        grades = {"crit_success", "success", "failure", "crit_failure"}
        for seed in range(50):
            import random
            rng = random.Random(seed)
            outcome = dice.roll_check("skill", "Speech", 3, {"skills": {"Speech": 55}}, rng=rng)
            self.assertIn(outcome["outcome"], grades)


class AdversarialRun(unittest.TestCase):
    """The scenario table that backs the number in the README."""

    def test_no_hostile_turn_writes_anything(self):
        results = hostile_runs.scenarios() + hostile_runs.ledger_scenarios()
        illegal = [r["name"] for r in results if r["illegal"]]
        self.assertEqual(illegal, [], f"hostile turns produced state changes: {illegal}")

    def test_the_run_includes_a_control_that_commits(self):
        gate = hostile_runs.scenarios()
        self.assertTrue(any(r["committed"] for r in gate),
                        "a run where nothing commits proves only that everything is blocked")


if __name__ == "__main__":
    unittest.main()
