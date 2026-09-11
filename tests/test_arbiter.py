"""What the arbiter guarantees, asserted without an engine, a model or a network.

Run with either runner:

    python -m unittest discover -s tests -q
    pytest -q
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adversarial import hostile_runs                      # noqa: E402
from arbiter import atom_gate, dice, invariants, ledger    # noqa: E402

_REGISTRY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "arbiter", "atom_registry.json")
_ESCORT = {182: 0, 70: 0, 203: 0, 71: 0, 85: 0}   # the escort quest: stage, dead, hostile, missing, reward


def _copy(atom: dict) -> dict:
    return json.loads(json.dumps(atom))


def _load_registry(raw: dict) -> tuple[dict, dict, str]:
    """Load `raw` through the real fail-closed loader, from a temporary file.

    Returns the live whitelist, the rejects by atom id and what the loader reported on stderr. The
    cache is dropped afterwards, so the next caller loads the committed registry again.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "atom_registry.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        report = io.StringIO()
        with mock.patch.object(atom_gate, "_PATH", path), contextlib.redirect_stderr(report):
            atom_gate.reload()
            try:
                return atom_gate.active_atoms(), dict(atom_gate.rejects()), report.getvalue()
            finally:
                atom_gate.reload()


def _run_hostile_main() -> tuple[int, str]:
    """`python -m adversarial.hostile_runs`, in process: the exit code and the printed table."""
    out = io.StringIO()
    with mock.patch.object(sys, "argv", ["hostile_runs"]), contextlib.redirect_stdout(out):
        code = hostile_runs.main()
    return code, out.getvalue()


class _ProcedureThatKills(hostile_runs.Recorder):
    """A write site whose engine procedure leaves the escorted character dead (gvar 70)."""

    def __call__(self, mutations, proc=None):
        after = super().__call__(mutations, proc)
        if proc:
            after[70] = 1
        return after


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

    def test_the_teacher_exemption_is_exact(self):
        """A once_per_npc teacher may go without a durable guard only if its effect is exactly `skills`.

        The loader's relaxation for village teachers is an allowlist from an adversarial review:
        underscore notes aside, the effect must hold `skills` and nothing else, because a skill raise
        is benign and engine-capped while every other effect kind can write engine or quest state. So
        a guard-free teacher row that also carries a quest variable, a procedure, a map or local
        variable, a timestamp, a post-assert list or an effect kind nobody has invented yet must be
        rejected, loudly, and stay out of the whitelist, while the row itself, and the row with a note
        added, still load. Every row is loaded from a copy of the real registry.
        """
        with open(_REGISTRY, encoding="utf-8") as f:
            raw = json.load(f)
        teacher_id = "arroyo_jordan_teach"
        teacher = raw[teacher_id]
        self.assertTrue(teacher.get("once_per_npc"))
        self.assertFalse((teacher.get("guard") or {}).get("durable"), "the teacher is meant to be guard-free")
        extras = {"data_delta": ["set gvar 10 = 2"],
                  "proc": {"script": "acjordan", "proc": "Node003"},
                  "map_vars": ["set map_var 13 = 1"],
                  "local_vars": ["set local_var 8 = 1"],
                  "stamp_time": {"gvar": 458, "unit": "hours"},
                  "post": ["gvar(10)==0"],
                  "party_add": ["1"]}                    # an effect kind nobody has invented yet
        for kind, value in extras.items():
            row = _copy(teacher)
            row["effect"][kind] = value
            raw[f"{teacher_id}+{kind}"] = row
        noted = _copy(teacher)
        noted["effect"]["_note"] = "a designer's note rides along"
        raw[f"{teacher_id}+_note"] = noted

        active, rejected, report = _load_registry(raw)
        self.assertIn(teacher_id, active)
        self.assertIn(f"{teacher_id}+_note", active)
        for kind in extras:
            atom_id = f"{teacher_id}+{kind}"
            with self.subTest(effect=f"skills + {kind}"):
                self.assertNotIn(atom_id, active)
                self.assertIn("guard.durable", rejected.get(atom_id, ""))
                self.assertIn(f"[ATOM-GATE REJECT] {atom_id}", report)


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

    def test_a_missing_party_size_fails_closed(self):
        """The Navarro sentry admits only a recruit who arrives alone: `party_size(0)==0`.

        When the engine reports no escort size, the guard must read the player as accompanied, never
        as alone: the pass is refused, as it is for a reported party of two. With every map variable in
        place, the same turn commits when the engine reports a party of zero, so the refusal is the
        missing party size and nothing else.
        """
        atom = self.atoms["navarro_gate_password"]
        gvars, map_vars = {511: 0}, {0: 1, 14: 0}      # enlisted by Chris, gate not passed, no alert
        alone = atom_gate.commit_effect(atom, dict(gvars), hostile_runs.Recorder(gvars),
                                        map_vars=dict(map_vars), party_size=0)
        self.assertTrue(alone.committed, alone.reason)
        for party_size in (None, 2):
            with self.subTest(party_size=party_size):
                result = atom_gate.commit_effect(atom, dict(gvars), hostile_runs.Recorder(gvars),
                                                 map_vars=dict(map_vars), party_size=party_size)
                self.assertFalse(result.committed, f"the gate opened for party_size={party_size!r}")
                self.assertEqual(result.reason, "guard false")
        self.assertFalse(atom_gate.guard_holds("party_size(0)==0", {}, party_size=None))

    def test_the_reward_flag_is_refused_at_every_stage_the_escort_fires_from(self):
        """An escort atom never writes the quest's success flag (gvar 85): that is the reward.

        reward_iff_started holds whatever the quest stage, so the attack is tried in every state an
        escort atom fires from: the accept atom at stage 0, and the go-now atom at stage 0 and at stage
        1, where the player accepted earlier and came back. In each, the honest turn commits, which
        shows the atom fires from that state, and the same turn with the success flag appended is
        refused by the reward invariant before it reaches the write site.
        """
        for atom_id, stage in (("torr_guard_brahmin_accept", 0), ("torr_guard_brahmin_goto", 0),
                               ("torr_guard_brahmin_goto", 1)):
            with self.subTest(atom=atom_id, stage=stage):
                atom, before = self.atoms[atom_id], {**_ESCORT, 182: stage}
                honest = atom_gate.commit_effect(atom, dict(before), hostile_runs.Recorder(before))
                self.assertTrue(honest.committed, honest.reason)
                forged = _copy(atom)
                forged["effect"]["data_delta"] = ["set gvar 182 = 1", "set gvar 85 = 1"]
                rec = hostile_runs.Recorder(before)
                result = atom_gate.commit_effect(forged, dict(before), rec)
                self.assertFalse(result.committed, f"the reward flag was written at stage {stage}")
                self.assertIn("reward_iff_started", result.reason)
                self.assertFalse(rec.touched)


class PostAssert(unittest.TestCase):
    """What cannot be prevented is detected: a failed post-assert is reported and halts the gate."""

    def setUp(self):
        atom_gate.reload()
        atom_gate.reset_halt()
        invariants.register_predicates()
        # Run in reverse: clear the halt, drop this test's predicate, register the shipped set again,
        # and reload so that the post-assert's escalation does not linger in the loader's rejects.
        self.addCleanup(atom_gate.reload)
        self.addCleanup(invariants.register_predicates)
        self.addCleanup(atom_gate.reset_predicates)
        self.addCleanup(atom_gate.reset_halt)
        self.atoms = atom_gate.active_atoms()

    def test_a_failed_post_assert_halts_the_next_valid_commit(self):
        """After a procedure breaks an invariant, the next commit is refused because the gate halted.

        An engine procedure cannot be checked before it runs, so the invariants of an atom that calls
        one are re-asserted on the state after it. The shipped predicates read only the state before
        the turn and the planned writes, so the go-now escort atom declares one more here, which reads
        the state after, and its procedure leaves the escorted character dead. The next commit is an
        unrelated, valid quest accept whose invariants are all registered: it must be refused with a
        reason saying the gate halted, without reaching the write site, and it must go through once
        the halt is reset, which shows that the halt, and nothing else, refused it.
        """
        atom_gate.register_invariant(
            "escort_survives_the_procedure",
            lambda c: (c["after"] if c["after"] is not None else c["before"]).get(70, 0) == 0)
        goto = _copy(self.atoms["torr_guard_brahmin_goto"])
        goto["invariants"] = [*goto["invariants"], "escort_survives_the_procedure"]
        before = {182: 0, 70: 0, 203: 0, 71: 0}
        report = io.StringIO()
        with contextlib.redirect_stderr(report):
            first = atom_gate.commit_effect(goto, dict(before), _ProcedureThatKills(before))
        self.assertTrue(first.committed, first.reason)
        self.assertFalse(first.post_ok, "the post-assert did not detect the dead escort")
        self.assertIn("POST-ASSERT 'escort_survives_the_procedure' failed", report.getvalue())

        accept, state = self.atoms["klamath_ratgod_accept"], {390: 0, 68: 0}
        rec = hostile_runs.Recorder(state)
        refused = atom_gate.commit_effect(accept, dict(state), rec)
        self.assertFalse(refused.committed, "a commit went through after a failed post-assert")
        self.assertIn("halted", refused.reason)
        self.assertFalse(rec.touched, "a halted gate reached the write site")

        atom_gate.reset_halt()
        resumed = atom_gate.commit_effect(accept, dict(state), hostile_runs.Recorder(state))
        self.assertTrue(resumed.committed, resumed.reason)


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

    def test_a_difficulty_below_one_gives_no_bonus(self):
        """Difficulty 1 is the easiest check: answering a lower one buys the model nothing.

        The chance is the character's ability minus a penalty that is zero at difficulty 1. The schema
        lets the model answer any integer, so difficulty 0 or -9 must give exactly the chance of
        difficulty 1 at the same skill; otherwise the model, not the character's statistics, would
        choose the chance (at -9 a character with no skill would go from 5 % to 95 %).
        """
        for skill in (0, 20, 40, 60, 80, 100, 300):
            character = {"skills": {"Speech": skill}}
            easiest = dice.roll_check("skill", "Speech", 1, character)["chance"]
            for difficulty in (0, -1, -9, -100):
                with self.subTest(skill=skill, difficulty=difficulty):
                    self.assertEqual(dice.roll_check("skill", "Speech", difficulty, character)["chance"],
                                     easiest)


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

    def test_a_control_that_no_longer_commits_is_illegal(self):
        """A gate that refuses everything must fail the run, not pass it.

        The run's "illegal" flag is its only verdict, and the tests above reuse it. The control is the
        honest turn that must still commit, so under a gate that refuses every turn, which is what a
        broken gate that blocks everything looks like, the control must be flagged illegal and the
        command must exit 1, while the refused hostile turns stay legal.
        """
        def refuse_everything(atom, gvars, applier, *args, **kwargs):
            return atom_gate.CommitResult(False, "refused: this gate refuses every turn")

        with mock.patch.object(atom_gate, "commit_effect", refuse_everything):
            rows = hostile_runs.scenarios()
            code, out = _run_hostile_main()
        controls = [r for r in rows if r["expected_commit"]]
        self.assertTrue(controls, "the run has no control turn")
        self.assertTrue(all(r["illegal"] for r in controls), "a control that did not commit passed")
        self.assertFalse(any(r["illegal"] for r in rows if not r["expected_commit"]))
        self.assertEqual(code, 1, out)
        self.assertIn("<-- ILLEGAL", out)

    def test_a_refused_turn_that_reached_the_write_site_is_illegal(self):
        """A refusal after a write is still a write: the run flags it.

        A refused turn must never reach the write site: no partial write, no rollback. Here the real
        gate is wrapped so that every turn it refuses calls the write site anyway before the refusal
        is reported. Every refused turn that wrote must be flagged illegal although it reports a
        refusal, the honest control must stay legal, and the command must exit 1.
        """
        real_commit = atom_gate.commit_effect

        def write_then_refuse(atom, gvars, applier, *args, **kwargs):
            result = real_commit(atom, gvars, applier, *args, **kwargs)
            if not result.committed:
                applier(atom_gate.parse_mutations(atom), atom_gate.effect_proc(atom))
            return result

        with mock.patch.object(atom_gate, "commit_effect", write_then_refuse):
            rows = hostile_runs.scenarios()
            code, out = _run_hostile_main()
        leaked = [r for r in rows if not r["committed"] and (r["writes"] or r["procs"])]
        self.assertTrue(leaked, "the wrapper never reached the write site on a refused turn")
        for r in leaked:
            with self.subTest(scenario=r["name"]):
                self.assertTrue(r["illegal"], "a refused turn that wrote passed as legal")
        self.assertFalse(any(r["illegal"] for r in rows if r["expected_commit"]))
        self.assertEqual(code, 1, out)


if __name__ == "__main__":
    unittest.main()
