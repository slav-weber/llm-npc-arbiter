# AGENTS.md

Instructions for coding agents, and for people, working in this repository. `CLAUDE.md` imports
this file; other agents read it directly.

## What this repository is

The write-control layer of an LLM-driven game mod, extracted from a private repository: the
chokepoint every durable change goes through, the whitelist of write atoms, the validated state
ledger, the response contract, the graded check and the knowledge graph the characters retrieve
from. Python 3.12 with uv; the runtime is standard library only. Start with `README.md` and
`docs/ARCHITECTURE.md`.

Everything written about the system (documentation, comments, docstrings, log lines) is English.
Everything the system matches on or produces (player-text patterns, text for the narrating model,
briefs, the corpus) stays in the game's language: translating it breaks the system.

## Commands

```bash
uv sync                                          # the locked environment (ruff is the only dev tool)
uv run python -m verification.gates              # every deterministic gate, exactly what CI runs
uv run python -m unittest discover -s tests -q   # the test suite alone
uv run python -m adversarial.hostile_runs        # the hostile scenario table
```

Nothing here needs an engine, a model or a network.

## Invariants: never propose a change that breaks one

1. **The model names things; it never authors an effect.** Its response is a strict function call
   from closed schemas (`arbiter/schemas.py`, no additional properties). It picks an atom id or an
   effect token from a closed set, and code resolves that to what a designer wrote.
2. **One chokepoint, in a fixed order.** `commit_effect` in `arbiter/atom_gate.py` is the only path
   to durable state. An empty effect is a refusal; the guard is evaluated on the state before the
   turn; every declared invariant must resolve to a registered predicate (an unknown name is a
   refusal) and pass on that state; only then is the single injected write site called, once. A
   refused turn never reaches the write site: no partial write, no rollback.
3. **What cannot be prevented is detected.** For effects that call an engine procedure the
   invariants are re-asserted on the state after the turn; a violation is reported and halts
   further commits until a reset.
4. **The loader fails closed, loudly.** An atom without invariants, without intent verification or
   without a non-empty design source is rejected and reported, never loaded quietly. An inactive
   atom is inert.
5. **The ledger stores only declared state.** A domain, predicate or value that the registry in
   `arbiter/registry/` does not declare is dropped; mutually exclusive predicates clear their
   siblings; a fact is superseded with its provenance, never silently overwritten.
   (`arbiter/ledger.py`)
6. **Code rolls the check.** The chance comes from the character's statistics and the difficulty
   and is clamped to 5..95; one roll decides one of four grades by a fixed critical margin; the
   model only narrates the grade it is given. (`arbiter/dice.py`)
7. **Optional layers degrade to a no-op, and uncertainty to the safe side.** A missing graph file
   leaves retrieval as it was; a character gated by a world milestone keeps its pre-milestone
   baseline while the milestone has not fired or its state is unknown. (`knowledge/graph.py`,
   `arbiter/milestone_gate.py`)
8. **Every rule records the failure that produced it.** Do not delete a comment that says why a
   rule exists, and do not remove a rule because its reason is not obvious.

## Boundaries: what an agent must not do here

- Do not delete, skip or weaken a test or a hostile scenario to make a run green. The test ratchet
  (`verification/test_ratchet.py`) fails on a removed or skipped test, and changing
  `verification/test_inventory.json` needs a human decision in the same commit.
- Do not change designer data as a side effect: the atom registry, the state registry, the quests,
  the milestone and dialect side-cars, the knowledge corpus. Each one carries its provenance.
- Do not translate strings the system matches on or produces.
- Do not add a runtime dependency: the runtime ships inside a game installation.
- Do not edit `verification/seeded_bugs/` or `verification/reports/` unless that is the task.
- Do not read or write `.env`, and never commit a secret.
- Do not change CI (`.github/workflows/`) or the gate list (`verification/gates.py`) as a side
  effect of another task.

## Definition of done

A change is done when `uv run python -m verification.gates` is green **and** the claim of what it
does is backed by evidence: a test that fails without the change, a gate's output, or a measured
run. In reports, mark each claim **[LIVE]** (observed at runtime), **[CODE]** (read in the source)
or **[CLAIM]** (asserted, not backed), and write "verified" only next to a link to a committed
artifact.

## Review

`/review` (Claude Code, `.claude/skills/review/`) runs the adversarial review of a change: a
reviewer reads the diff against the invariants above, an independent skeptic tries to refute each
finding, and the confirmed findings are written to `verification/reviews/`.
