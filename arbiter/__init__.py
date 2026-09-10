"""The arbiter: the model decides, this code verifies and applies.

A language model driving a game character proposes what happens next. It may not make it happen.
Everything durable goes through one chokepoint, and each layer here owns one part of that:

``atom_gate``
    The chokepoint. ``commit_effect`` is the only path that may mutate durable state. It computes
    the effect, evaluates the atom's guard against the pre-state, resolves every declared invariant
    to a registered predicate (an unknown name is a refusal, not a warning), applies through a
    single injected write site, and re-asserts the invariants on the post-state for effects that run
    engine procedures. Any failed step means no write at all.

``invariants``
    The predicates the gate resolves by name: generic ones derived from an atom's own effect and
    guard, plus the named invariants a quest declares for itself.

``ledger``
    Durable state the model is allowed to influence, validated against an open registry of domains,
    predicates and value ranges. An undeclared domain, predicate or value is dropped, not stored;
    mutually exclusive predicates clear their siblings; every fact carries its provenance.

``schemas``
    The response contract. The model answers through strict function calling: an intent, prose, and
    effect tokens from a closed vocabulary, with one effect slot per outcome grade. Anything outside
    the schema cannot be expressed, let alone applied.

``dice``
    The four-grade check: a base chance from the character's own statistics, a difficulty penalty,
    a clamp, one hundred-sided roll, and a critical margin. The model never decides the outcome.

``result_facts``
    The closed vocabulary of facts that flow back from the engine to the narrator, so prose can only
    describe what actually happened.

``atom_arbitration``, ``milestone_gate``, ``dialect_guard``
    Deterministic classification of player intent, one-shot milestone gating, and an allowlist of
    characters whose broken speech is canon and must not be normalised.

Standard library only: this code ships inside a game installation, where a dependency tree is a
liability, and every part of it must be testable without the engine, the model or a network.
"""

from . import (  # noqa: F401
    atom_arbitration,
    atom_gate,
    dialect_guard,
    dice,
    invariants,
    ledger,
    milestone_gate,
    result_facts,
    schemas,
)

__all__ = [
    "atom_arbitration",
    "atom_gate",
    "dialect_guard",
    "dice",
    "invariants",
    "ledger",
    "milestone_gate",
    "result_facts",
    "schemas",
]
