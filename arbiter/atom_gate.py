"""The WRITE-atom enforcement backbone.

This is the MECHANISM only, never an atom's predicates. It gives the curated effect-atom layer one chokepoint
(`commit_effect`) through which EVERY durable mutation must pass, a fail-closed loader for the inert atom
whitelist (`atom_registry.json`), and the validate-before-commit + post-assert ordering. The Torr-specific
invariant predicates (monotonic_Q, not_if_dead, …) belong to the predicate layer above — here the registry
starts empty and `register_invariant` is how that layer plugs them in.

Hard rule #1 (don't break saves): an atom may write ONLY via `commit_effect`, and only after its guard AND every
declared invariant pass on the pre-state. Hard rule (inertness): an atom does nothing unless `active:true` AND
every name in `invariants` resolves to a registered predicate — anything else is a no-op (vanilla path untouched).

Fail-closed + ESCALATION (2026-06-26): the loader rejects — loudly, never silently — any atom missing
`invariants`, `intent_verification`, or a non-empty `intent_verification.design_source`. "No design source" is a
flag a human must clear, not a silent green: code-truth (what the gvar-guard does) without design-truth (what the
designer intended, with a citation) is exactly how a 'safety' invariant deletes intended content — the Torr
near-miss, where a plausible-looking guard would have removed a quest branch the designer meant to keep.

Side-car discipline (mirrors milestone_gate.py): no registry / unknown atom / inactive -> inert.
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "atom_registry.json")

_ATOMS = None          # id -> atom dict (schema-valid + active); the live whitelist
_REJECTS: list[tuple[str, str]] = []   # (atom_id, reason) — escalated, surfaced to humans/tests
_PREDICATES: dict[str, callable] = {}  # invariant name -> fn(ctx) -> bool  (the predicate layer fills this)


# ---- invariant predicate registry (the predicate layer fills it; the gate owns only the mechanism) -------
def register_invariant(name: str, fn) -> None:
    _PREDICATES[name] = fn


def reset_predicates() -> None:
    _PREDICATES.clear()


# ---- schema validation: the mandatory-field enforcement (fail-closed) ------------------------------------
def _schema_reason(atom_id: str, a: dict) -> str | None:
    """Return a rejection reason if the atom is not a well-formed definition, else None."""
    if not isinstance(a, dict):
        return "not an object"
    # Hardening before the scale-up (2026-06-28): identity + routing + deed-grounding are LOAD-BEARING at ×99
    # make them mandatory, fail-closed + escalated, exactly like design_source. A bad scope.script / intent loads
    # "active" but silently never binds/routes (dead atom); a missing offer_brief ships invention-prone (the reply
    # prompt falls back to the thin 2-word Pip-Boy journal title -> the ORIGINAL live bug). Reject, don't stamp.
    scope = a.get("scope")
    if not isinstance(scope, dict):
        return "scope missing (must be an object)"
    if not str(scope.get("script") or "").strip():
        return "scope.script missing/empty (the atom can't bind to an NPC)"
    if a.get("intent") not in ("accept", "go_now", "gate_pass", "train"):
        return "intent must be one of {accept, go_now, gate_pass, train} (routing key — a typo loads but never routes)"
    if not str(scope.get("offer_brief") or "").strip():
        return "scope.offer_brief missing/empty (deed-grounding mandatory — no faithful offer without it)"
    obs = scope.get("offer_brief_source")
    if not isinstance(obs, list) or not any(str(s).strip() for s in obs):
        return "scope.offer_brief_source missing/empty (the deed brief must cite a canon source)"
    eff = a.get("effect") or {}
    # Reusable effect = data over two GENERAL primitives: data_delta (gvar mutations) and/or proc{script,proc}
    # (invoked by the general exec_proc primitive). At least one must be present. NEVER per-atom code.
    has_data = isinstance(eff.get("data_delta"), list) and bool(eff.get("data_delta"))
    p = eff.get("proc")
    has_proc = isinstance(p, dict) and bool(p.get("script")) and bool(p.get("proc"))
    # map_var/local_var writes and skill trains are ALSO valid effects (an atom whose vanilla state lives in a
    # map_var/local_var, or a teacher whose effect is a skill raise, carries no gvar of its own).
    has_mapv = isinstance(eff.get("map_vars"), list) and bool(eff.get("map_vars"))
    has_localv = isinstance(eff.get("local_vars"), list) and bool(eff.get("local_vars"))
    has_skills = isinstance(eff.get("skills"), list) and bool(eff.get("skills"))
    if not (has_data or has_proc or has_mapv or has_localv or has_skills):
        return "effect must carry non-empty data_delta / proc{script,proc} / map_vars / local_vars / skills"
    # FRAMEWORK RELAXATION (the village-teacher training track): a once_per_npc atom whose effect is
    # SKILLS-ONLY (no gvar data_delta, no proc, no map_var/local_var write) needs NO durable gvar-guard.
    # Rationale: such an atom writes nothing engine-fakeable — train_skill is benign, engine-arbitrated,
    # halved-if-tagged, capped at 300 — and it is gated by (1) the memory one-shot (once_per_npc: fires once
    # per NPC, save-resident), (2) the intent grounding (only a «научи меня» / "teach me" intent routes here),
    # (3) scope.script (only THIS teacher). Village trainers (Jordan, SF Dragon) have no natural teaching-gvar
    # to guard on, so requiring one would force a guessed, weak guard. A durable guard STAYS MANDATORY for any
    # atom with a gvar/proc/map/local effect (those CAN fake quest/world state).
    # ALLOWLIST (from the adversarial review): the effect must hold EXACTLY `skills` (_-notes aside).
    # A denylist forgot stamp_time (a durable gvar write scoped to kAtomGuardGvars incl. dead/enemy flags) — an
    # allowlist is structurally faking-proof: ANY other effect kind (data_delta/proc/map/local/stamp_time/future)
    # makes this False, so the durable-guard requirement stands for anything that can write engine/quest state.
    _eff_keys = {k for k in eff if not str(k).startswith("_")}
    skills_only_oneshot = bool(a.get("once_per_npc")) and has_skills and _eff_keys == {"skills"}
    if not skills_only_oneshot and not (a.get("guard") or {}).get("durable"):
        return "guard.durable missing (required for any atom that writes gvar/proc/map/local; a skills-only once_per_npc teacher is exempt)"
    inv = a.get("invariants")
    if not isinstance(inv, list) or not inv:
        return "invariants missing/empty (no invariants -> no atom)"
    iv = a.get("intent_verification")
    if not isinstance(iv, dict):
        return "intent_verification missing"
    if not str(iv.get("code_truth") or "").strip():
        return "intent_verification.code_truth empty"
    if not str(iv.get("design_truth") or "").strip():
        return "intent_verification.design_truth empty"
    src = iv.get("design_source")
    if not isinstance(src, list) or not any(str(s).strip() for s in src):
        # 2026-06-26: design_truth WITHOUT a named source is a flag, not a silent green.
        return "intent_verification.design_source missing/empty (design intent must cite a source)"
    return None


def _escalate(atom_id: str, reason: str) -> None:
    _REJECTS.append((atom_id, reason))
    print(f"[ATOM-GATE REJECT] {atom_id}: {reason}", file=sys.stderr)


def _audit(msg: str) -> None:
    """Load-audibility line: the debug log (which rides along in tester session reports) plus stderr; it never
    raises. Added after the 0.69.0 ship-list bug: a MISSING registry was completely silent, so a whole test
    session went on chasing 'no active atom' with nothing in the report saying the whitelist was empty."""
    try:
        from core import _dbg  # lazy: the gate stays import-independent; the host never imports it back
        _dbg(msg)
    except Exception:  # noqa: BLE001 — logging must never take down the gate
        pass
    try:
        print(f"[{msg}]", file=sys.stderr, flush=True)
    except Exception:  # noqa: BLE001
        pass


def _load() -> dict:
    global _ATOMS
    if _ATOMS is None:
        _ATOMS = {}
        _REJECTS.clear()
        try:
            with open(_PATH, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:  # noqa: BLE001 — no registry -> inert (vanilla path), like milestone_gate
            _audit(f"ATOM-GATE | registry NOT loaded ({os.path.basename(_PATH)}: {e.__class__.__name__}) -> "
                   f"0 atoms; the curated-deed layer is INERT (no quest atom can fire on any NPC)")
            return _ATOMS
        for atom_id, a in raw.items():
            if atom_id.startswith("_"):
                continue
            reason = _schema_reason(atom_id, a)
            if reason:
                _escalate(atom_id, reason)     # fail-closed: rejected atoms never enter the whitelist
                continue
            if a.get("active") is True:
                _ATOMS[atom_id] = {**a, "atom_id": atom_id}
            # schema-valid but inactive -> validated reference, kept OUT of the live set (inert)
        _audit(f"ATOM-GATE | loaded {len(_ATOMS)} active atoms ({len(_REJECTS)} rejected) from atom_registry.json")
    return _ATOMS


def reload() -> None:
    """Drop caches (after editing atom_registry.json / for tests)."""
    global _ATOMS
    _ATOMS = None


def rejects() -> list[tuple[str, str]]:
    _load()
    return list(_REJECTS)


def active_atoms() -> dict:
    return dict(_load())


# ---- generic mechanism: durable-guard eval + data-delta mutation parse (NOT atom predicates) --------------
# Guard clause: gvar(N) / map_var(N) / local_var(N) / party_size(0) <op> V. Namespaces are disjoint (gvar(13)
# is NOT map_var(13)): gvar = engine global, map_var = per-map global (mapGetGlobalVar), local_var =
# per-critter-script (scriptGetLocalVar). The map_var/local_var kinds unblock atoms whose vanilla pass-state
# lives OUTSIDE quest gvars (the bridge keeper's LVAR_8, Navarro's MVAR_13).
# party_size(0) = the ESCORT size a vanilla gatekeeper sees — the engine emits it with the EXACT CCGGUARD
# formula (PARTY_COUNT - car - dude - K-9), so the vanilla rule "recruits arrive ALONE" becomes
# `party_size(0)==0`. Index is always 0 (one scalar); missing data evaluates FAIL-CLOSED (assume accompanied).
_CLAUSE = re.compile(r"(gvar|map_var|local_var|party_size)\(\s*(\d+)\s*\)\s*(==|!=|<=|>=|<|>)\s*(-?\d+)")
_OPS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}


def guard_var_refs(durable: str) -> set:
    """Every (kind, index) the durable guard references — so the firing layer injects EXACTLY those from the
    engine snapshot. kind ∈ {gvar, map_var, local_var}. Generic: any `<kind>(N) <op> V` clause set."""
    return {(m.group(1), int(m.group(2))) for m in _CLAUSE.finditer(durable or "")}


def guard_gvar_indices(durable: str) -> set:
    """Back-compat: just the gvar-kind indices (callers that only inject engine gvars). map_var/local_var
    indices are obtained via guard_var_refs."""
    return {idx for kind, idx in guard_var_refs(durable) if kind == "gvar"}


def guard_holds(durable: str, gvars: dict, map_vars: dict = None, local_vars: dict = None,
                party_size=None) -> bool:
    """Evaluate a durable guard `<kind>(N) <op> V (AND <kind>(M) <op> W)*`, kind ∈ {gvar,map_var,local_var,
    party_size}. Values come from index->value dicts (map_vars/local_vars default empty); party_size is the
    engine-emitted escort scalar — None (caller has no data) reads as 99 so a `party_size(0)==0` gate FAILS
    CLOSED rather than fire on an assumed "alone". Unparseable clause -> fail-closed."""
    _pick = {"gvar": gvars or {}, "map_var": map_vars or {}, "local_var": local_vars or {},
             "party_size": {0: (int(party_size) if party_size is not None else 99)}}
    clauses = [c.strip() for c in re.split(r"\bAND\b", durable or "") if c.strip()]
    if not clauses:
        return False
    for c in clauses:
        m = _CLAUSE.fullmatch(c)
        if not m:
            return False                       # don't understand it -> refuse (false-null > false-fire)
        kind, idx, op, val = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
        if not _OPS[op](int(_pick[kind].get(idx, 0)), val):
            return False
    return True


_MUT = re.compile(r"set\s+gvar\s+(\d+)\s*=\s*(-?\d+)")
_MUT_MAP = re.compile(r"set\s+map_var\s+(\d+)\s*=\s*(-?\d+)")
_MUT_LOCAL = re.compile(r"set\s+local_var\s+(\d+)\s*=\s*(-?\d+)")


def parse_mutations(atom: dict) -> list[tuple[int, int]]:
    """effect.data_delta -> [(gvar_index, value)] (the data-delta part; declarative, checkable before write)."""
    out = []
    for s in (atom.get("effect") or {}).get("data_delta") or []:
        m = _MUT.fullmatch(str(s).strip())
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return out


def parse_var_mutations(atom: dict) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(map_var_muts, local_var_muts) from effect.map_vars / effect.local_vars
    ('set map_var 13 = 1' / 'set local_var 8 = 20105') -> [(idx, val)]. Declarative, whitelist-gated in the engine
    (setmapvar/setlvar). Lets a non-gvar atom (the bridge keeper's LVAR_8, Navarro's MVAR_13) carry a real
    effect."""
    eff = atom.get("effect") or {}
    mm, lm = [], []
    for s in (eff.get("map_vars") or []):
        m = _MUT_MAP.fullmatch(str(s).strip())
        if m:
            mm.append((int(m.group(1)), int(m.group(2))))
    for s in (eff.get("local_vars") or []):
        m = _MUT_LOCAL.fullmatch(str(s).strip())
        if m:
            lm.append((int(m.group(1)), int(m.group(2))))
    return mm, lm


def parse_skill_trains(atom: dict) -> list[tuple[str, int]]:
    """effect.skills ('Unarmed:10', 'Melee_Weapons:10') -> [(skill_name, points)] for the train_skill fx —
    a teacher's PERMANENT skill raise on the player (op_critter_mod_skill mirror). Faithful amount lives in the
    row; the engine halves a tagged skill + caps at 300. One-shot is the atom's guard (a local_var(taught)==0)."""
    out = []
    for s in (atom.get("effect") or {}).get("skills") or []:
        parts = str(s).strip().split(":")
        if len(parts) == 2 and parts[0].strip() and parts[1].strip().lstrip("-").isdigit():
            out.append((parts[0].strip(), int(parts[1].strip())))
    return out


def effect_proc(atom: dict):
    """The proc part: {script, proc} for the GENERAL exec_proc primitive, or None. The brain cannot run it —
    commit_effect returns it for the ENGINE to invoke (resolve script program + proc index by name ->
    _executeProcedure). This is data, not per-atom code; a new teleport-quest is a new row, not new code."""
    p = (atom.get("effect") or {}).get("proc")
    if isinstance(p, dict) and p.get("script") and p.get("proc"):
        return {"script": p["script"], "proc": p["proc"]}
    return None


# ---- THE CHOKEPOINT ---------------------------------------------------------------------------------------
class CommitResult:
    def __init__(self, committed, reason="", mutations=None, proc=None, post_ok=True):
        self.committed = committed
        self.reason = reason
        self.mutations = mutations or []   # data_delta gvar writes (idx,val)
        self.proc = proc                   # {script,proc} for the engine's exec_proc primitive, or None
        self.post_ok = post_ok

    def __repr__(self):
        return (f"CommitResult(committed={self.committed}, reason={self.reason!r}, mut={self.mutations}, "
                f"proc={self.proc}, post_ok={self.post_ok})")


_HALTED = False  # a proc post-assert failure stops further commits (detect-not-prevent)


def reset_halt() -> None:
    global _HALTED
    _HALTED = False


def commit_effect(atom: dict, gvars: dict, applier, roll=None,
                  map_vars: dict = None, local_vars: dict = None, party_size=None) -> CommitResult:
    """The ONLY path that may mutate durable state for an atom. Order: compute -> guard -> invariants ->
    apply (single write site, injected) -> post-assert for proc atoms. Any failed gate = no write (reject).

    `gvars`   : pre-state map {gvar_index: value} (from the engine snapshot).
    `map_vars`/`local_vars` : same, for map_var(N)/local_var(N) guard clauses (default empty).
    `party_size` : the engine's escort scalar for `party_size(0)` clauses (None = no data -> fail-closed).
    `applier` : callable(mutations)->after_gvars — the engine-arbitrated write (tests inject a fake).
    """
    global _HALTED
    if _HALTED:
        return CommitResult(False, "halted: a prior proc post-assert failed")
    if not isinstance(atom, dict) or not atom.get("active"):
        return CommitResult(False, "inert: atom not active / not in whitelist")   # vanilla path untouched

    mutations = parse_mutations(atom)      # data_delta part
    map_muts, local_muts = parse_var_mutations(atom)  # the map_var/local_var part of the effect
    skill_trains = parse_skill_trains(atom)  # train_skill part (a teacher's skill raise)
    proc = effect_proc(atom)               # proc part (general exec_proc primitive), or None
    if not mutations and not proc and not map_muts and not local_muts and not skill_trains:
        return CommitResult(False, "empty effect (no data_delta, no proc, no map/local vars, no skills)")

    _durable = (atom.get("guard") or {}).get("durable")
    if _durable and not guard_holds(_durable, gvars, map_vars, local_vars, party_size):
        return CommitResult(False, "guard false")
    # (no durable == a skills-only once_per_npc teacher — the loader only accepts that shape; the memory one-shot +
    # intent + scope are its gate, so there is no engine-state guard to evaluate here.)

    # resolve every declared invariant to a registered predicate — unknown -> fail-closed, never a silent pass
    names = atom.get("invariants") or []
    fns = []
    for nm in names:
        fn = _PREDICATES.get(nm)
        if fn is None:
            return CommitResult(False, f"unresolved invariant predicate '{nm}' (no predicate is registered "
                                       f"under that name)")
        fns.append((nm, fn))

    ctx = {"atom": atom, "before": dict(gvars), "before_map": dict(map_vars or {}),
           "before_local": dict(local_vars or {}), "before_party": party_size,
           "mutations": mutations, "proc": proc, "after": None}
    for nm, fn in fns:
        if not fn(ctx):
            return CommitResult(False, f"invariant '{nm}' failed pre-commit")

    # the SINGLE side-effecting call: engine-arbitrated. Applies data_delta gvars AND invokes the proc (exec_proc).
    after = applier(mutations, proc)
    result = CommitResult(True, "committed", mutations, proc=proc, post_ok=True)

    if proc is not None:                   # proc-atom: detect-not-prevent — re-assert on the post-state
        ctx_post = {"atom": atom, "before": dict(gvars), "before_map": dict(map_vars or {}),
                    "before_local": dict(local_vars or {}), "before_party": party_size,
                    "mutations": mutations, "proc": proc, "after": dict(after or {})}
        for nm, fn in fns:
            if not fn(ctx_post):
                _HALTED = True
                _escalate(atom.get("atom_id", "?"), f"POST-ASSERT '{nm}' failed — halting further commits")
                result.post_ok = False
                break
    return result


# ---- deterministic self-test (no engine / no LLM): the gate's unit matrix --------------------------------
if __name__ == "__main__":
    # The registry's Torr atom is active:false -> it is schema-valid but stays OUT of the live whitelist.
    reload()
    rj = dict(rejects())
    assert "torr_guard_brahmin_accept" not in rj, f"well-formed Torr atom must NOT be rejected: {rj}"
    # The Torr atom is ACTIVE: schema-valid AND in the live whitelist (active:false = valid but absent).
    assert "torr_guard_brahmin_accept" in active_atoms(), "active Torr atom must be live"
    print("registry load OK: Torr atom schema-valid + ACTIVE; rejects =", rj)

    # --- schema fail-closed: each missing mandatory field -> rejected (escalated), not loaded ---
    base = {
        "active": True,
        "intent": "accept",
        "scope": {"script": "kctorr", "offer_brief": "помоги Торру охранять стадо браминов",
                  "offer_brief_source": ["KCTORR.MSG {150} 'guard our family's brahmin herd'"]},
        "guard": {"durable": "gvar(182)==0"},
        "effect": {"data_delta": ["set gvar 182 = 1"]},
        "invariants": ["dummy"],
        "intent_verification": {"code_truth": "x", "design_truth": "y", "design_source": ["doc"]},
    }
    def reason(mut):
        a = json.loads(json.dumps(base))
        mut(a)
        return _schema_reason("t", a)
    assert reason(lambda a: a.update(effect={})), "effect with neither data_delta nor proc must reject"
    assert _schema_reason("t", {**json.loads(json.dumps(base)), "effect": {"proc": {"script": "s", "proc": "N"}}}) is None, \
        "proc-only effect must pass schema"
    assert reason(lambda a: a.pop("invariants")), "missing invariants must reject"
    assert reason(lambda a: a.update(invariants=[])), "empty invariants must reject"
    assert reason(lambda a: a.pop("intent_verification")), "missing intent_verification must reject"
    assert reason(lambda a: a["intent_verification"].pop("design_source")), "missing design_source must reject"
    assert reason(lambda a: a["intent_verification"].update(design_source=[])), "empty design_source must reject"
    assert reason(lambda a: a["intent_verification"].update(design_source=["", "  "])), "blank-only source must reject"
    assert reason(lambda a: a["intent_verification"].pop("design_truth")), "missing design_truth must reject"
    assert _schema_reason("t", base) is None, "fully-formed atom must pass schema"
    print("schema fail-closed OK (incl. design_source-required escalation)")

    # --- the hardening pass: identity (scope.script), routing (intent), grounding (offer_brief+source) are
    #     each MANDATORY now -> a missing/bad field is rejected with its OWN distinct, human-readable reason ---
    cases = [
        ("missing scope",                 lambda a: a.pop("scope")),
        ("empty scope.script",            lambda a: a["scope"].update(script="  ")),
        ("bad intent",                    lambda a: a.update(intent="rumble")),
        ("missing intent",                lambda a: a.pop("intent")),
        ("missing offer_brief",           lambda a: a["scope"].pop("offer_brief")),
        ("blank offer_brief",             lambda a: a["scope"].update(offer_brief="   ")),
        ("missing offer_brief_source",    lambda a: a["scope"].pop("offer_brief_source")),
        ("blank-only offer_brief_source", lambda a: a["scope"].update(offer_brief_source=["", "  "])),
    ]
    for label, mut in cases:
        rr = reason(mut)
        assert rr, f"{label} must reject"
        print(f"  reject [{label}] -> {rr}")
    print("schema hardening OK (scope.script + intent + offer_brief + its source required, fail-closed)")

    # --- commit_effect mechanism: guard + invariants + single write site + inertness ---
    reset_predicates()
    reset_halt()
    writes = {}
    procs_run = []
    def applier(muts, proc):                 # the injected single side-effect site (fake engine)
        for idx, val in muts:
            writes[idx] = val
        if proc:
            procs_run.append(proc)           # the engine's exec_proc would run here
        return {**state, **writes}
    state = {182: 0, 70: 0, 203: 0, 71: 0}
    torr = {**base, "atom_id": "torr", "guard": {"durable": "gvar(182)==0 AND gvar(70)==0"},
            "invariants": ["monotonic_Q"]}

    # (1) unresolved predicate -> fail-closed, no write
    r = commit_effect(torr, state, applier)
    assert not r.committed and "unresolved" in r.reason and not writes, f"unknown predicate must block: {r}"

    # (2) predicate registered + passes -> commits via applier (the only writer)
    register_invariant("monotonic_Q", lambda c: c["before"].get(182, 0) <= dict(c["mutations"]).get(182, 0))
    r = commit_effect(torr, state, applier)
    assert r.committed and writes == {182: 1}, f"valid atom must commit Q=1: {r}, {writes}"

    # (3) invariant fails -> rejected, NO write (start from a clean sink)
    writes = {}
    register_invariant("monotonic_Q", lambda c: False)
    r = commit_effect(torr, state, applier)
    assert not r.committed and not writes, f"failed invariant must block the write: {r}, {writes}"

    # (4) inert: inactive atom / guard false -> no-op
    assert not commit_effect({**torr, "active": False}, state, applier).committed, "inactive must be inert"
    register_invariant("monotonic_Q", lambda c: True)
    assert not commit_effect(torr, {182: 1}, applier).committed, "guard false (Q!=0) -> no-op"

    # (5) COMPOSITE proc-atom (the Torr shape): data_delta + general proc -> sets gvar AND emits exec_proc
    writes = {}
    procs_run.clear()
    reset_predicates()
    reset_halt()
    register_invariant("monotonic_Q", lambda c: True)
    torr_proc = {**base, "atom_id": "torr_proc", "active": True, "invariants": ["monotonic_Q"],
                 "guard": {"durable": "gvar(182)==0"},
                 "effect": {"data_delta": ["set gvar 182 = 1"], "proc": {"script": "kctorr", "proc": "Node020"},
                            "post": ["cur_map==14"]}}
    r = commit_effect(torr_proc, {182: 0}, applier)
    assert (r.committed and writes == {182: 1} and r.proc == {"script": "kctorr", "proc": "Node020"}
            and procs_run == [{"script": "kctorr", "proc": "Node020"}]), \
        f"composite must set gvar AND emit proc for the engine: {r}, writes={writes}, procs={procs_run}"

    # (6) proc-atom post-assert FAILS -> committed but flagged + HALTS further commits (detect-not-prevent)
    writes = {}
    procs_run.clear()
    reset_predicates()
    reset_halt()
    register_invariant("after_is_none", lambda c: c["after"] is None)   # true pre (after=None), false post
    bad = {**torr_proc, "invariants": ["after_is_none"]}
    r = commit_effect(bad, {182: 0}, applier)
    assert r.committed and not r.post_ok, f"proc post-assert failure must be DETECTED: {r}"
    assert not commit_effect(torr_proc, {182: 0}, applier).committed, "post-assert fail must HALT further commits"
    reset_halt()

    print("commit_effect mechanism OK (inert default, single write site, composite data+proc, post-assert/halt)")
    print("atom_gate self-test OK")
