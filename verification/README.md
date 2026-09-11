# Verification

This directory answers one question about the repository: **how much of what can go wrong would CI
actually stop?** It holds the gates CI runs and a benchmark that measures them by planting realistic
bugs one at a time, from a catalogue written by an agent that never saw the tests.

## The gates

| Gate | What a pass proves | CI | pre-commit | Benchmark |
|---|---|---|---|---|
| `unit-tests` | the 15 tests pass (no engine, no model, no network) | every push | | yes |
| `test-ratchet` | every recorded test still exists and every skip is on the allowed list | every push | | yes |
| `lint` | ruff finds nothing under the rule set in `pyproject.toml` (E, F, W) | every push | staged files | yes |
| `hostile-run` | every hostile turn in `adversarial/hostile_runs.py` is refused or dropped, and the control turn commits | every push | | yes |
| `atom-gate-selftest` | the atom gate's own self-test: fail-closed loader, single write site, composite effects, post-assert and halt | every push | | yes |
| `milestone-selftest` | a character gated by a world milestone keeps its baseline until the milestone fires; an ungated one is untouched | every push | | yes |
| `graph-current` | `knowledge/graph.json` is exactly what `knowledge/world.json` builds | every push | | yes |
| secret scan | no secret in any commit (gitleaks 8.30.1, checksum-verified, full history) | every push | staged changes | |
| dependency audit | no known vulnerability in the development tools pinned by `uv.lock` (the runtime has no dependencies) | every push, weekly | | |

The first seven are defined once, in `gates.py`; CI calls them one by one and the benchmark runs all
of them, so the benchmark measures exactly what CI enforces. Two of them are older than CI: the atom
gate and the milestone gate carried their own self-tests from the private repository
(`python -m arbiter.atom_gate`), and now CI runs them. The pre-commit gitleaks hook sees only staged
changes, which is why CI scans the history itself.

```bash
uv run python -m verification.gates                  # every gate
uv run python -m verification.gates --only lint      # one gate
```

### The test ratchet

A coding agent can turn a red suite green by deleting or skipping the tests that fail.
`test_ratchet.py` records every test id, and the allowed skips with their reasons, in
`test_inventory.json`. A recorded test that disappears, or a skip that is not on the list, fails the
gate. It tracks ids rather than counts: a deleted test replaced by a trivial one keeps the count.
Tests added, or a skip made on purpose: `uv run python -m verification.test_ratchet --update` in the
same commit, where a reviewer sees the inventory change.

## The agent layer

The gates stop what a check can express. The rest is left to review, done by agents under rules
they cannot skip:

- `AGENTS.md` is the source of truth for any coding agent: the commands, the eight invariants of the
  layer, the boundaries (never delete, skip or weaken a test or a hostile scenario; never change
  designer data or translate game-language strings as a side effect; no runtime dependency) and the
  definition of done, with the evidence marks [LIVE], [CODE] and [CLAIM]. `CLAUDE.md` imports it.
- `/review` (`.claude/skills/review/`) runs the gates, gives the diff to the `change-reviewer`
  subagent, which checks it against the invariants and has to prove every finding, and gives every
  serious finding to the `finding-skeptic` subagent, whose job is to refute it. Only confirmed
  findings reach the report in `verification/reviews/`.
- A Stop hook (`.claude/hooks/gates_before_stop.py`) does not let an agent that changed Python or
  JSON files finish while a gate is red, and tells it which gate.
- `.claude/settings.json` makes editing the test inventory, the catalogues, the reports, the gate
  list, CI or designer data (the atom registry, the state registry, the quests, the side-cars, the
  corpus), and pushing, ask a person first; reading `.env` is denied.

## The seeded-bug benchmark

`seeded_bugs/catalogue.py` lists twenty defects of the kind a coding agent introduces while fixing
or simplifying code or data, plus a canary. Each bug carries the story of how it plausibly happens
and its exact edits. `seeded_bugs/run.py` copies the working tree to a temporary directory and runs
every gate on the untouched copy first; a red baseline stops the run. Then, for each bug, it takes
a fresh copy, applies the edits and runs every gate again. A bug counts as caught when at least one
gate fails.

Rules that keep the number honest:

- **Written blind.** The catalogue was written by an agent that saw a copy of the code, the data
  and the documentation without the tests, and ran nothing but a checker that validates the edits.
  The gates were added before it was written, and nothing was tuned after it.
- **Exact edits.** Every edit is a find → replace that must match the current code exactly once.
  When the code moves on, the runner stops with an error instead of measuring a bug that no longer
  exists.
- **A canary.** The catalogue has one bug that crashes a module at import. If the canary is not
  caught, the runner is broken and nothing is reported.
- **No tuning.** The catalogue was committed before its first measured run, and a miss stays in it
  as a documented gap. Once tests are written against its misses, it becomes training data and the
  next honest number needs a new blind catalogue.
- **Provenance.** Every report records the git revision and the state of the tree when the snapshot
  was taken, a sha256 digest of the measured tree and the sha256 of the catalogue. Reports are never
  overwritten; a second report on the same day needs its own `--label`.

```bash
uv run python -m verification.seeded_bugs.run                  # full run, writes the report
uv run python -m verification.seeded_bugs.run --only A01,A07   # a subset, prints only
```

## Measurements

### First measurement: 5 of 20

Report: [`reports/seeded-bugs-2026-09-11.md`](reports/seeded-bugs-2026-09-11.md), measured on git
`1a7a4c7`. The catalogue was written blind, so this first number was not measured on a training set.

| Area | Planted | Caught |
|---|---|---|
| gate | 3 | 1 |
| loader | 2 | 1 |
| invariants | 2 | 1 |
| ledger | 1 | 1 |
| milestones | 1 | 1 |
| arbitration | 2 | 0 |
| registry | 2 | 0 |
| adversarial run, dialect, dice, knowledge, quests, result facts, schemas | 1 each | 0 |

What stopped the five. The hostile table and the tests caught the three bugs their scenarios
exercise directly: an unregistered invariant skipped instead of refused (A01), a lesson of 300
points (A07), an undeclared predicate stored (A08). The other two were caught only by the self-tests
that CI started running in this round: the atom gate's (A05, a design source made of blank strings)
and the milestone gate's (A14, the baseline no longer overriding the contaminated fields).

What the gates missed, grouped by the reason nothing failed:

| Why nothing failed | Bugs |
|---|---|
| **An assertion that passes for the wrong reason.** The atom gate's self-test proves that a failed post-assert halts further commits by trying a second commit, but that commit declares an invariant the test has just unregistered, so it is refused as unresolved whether the gate halted or not. | A02 |
| **A scenario that tries an attack in one state only.** "Walk through a closed gate" always passes a party size, so a missing one is never tried (A03). "Grant the reward flag" runs on an untouched quest, so the reward invariant is never tried on a started one (A06). | A03, A06 |
| **A branch no test drives:** the loader's exemption for guard-free teachers (A04); the difficulty floor (A09: the clamp test checks only that the chance stays within 5..95, and it still does); the graph loader's degradation on a corrupt file (A16). | A04, A09, A16 |
| **A module no test imports:** the response schemas (A10), the result-fact vocabulary (A11), the intent classifier (A12, A13). The tests and the hostile run import only the atom gate, the dice, the invariants and the ledger. | A10, A11, A12, A13 |
| **Designer data nobody pins:** the dialect allowlist (A15), a quest's stage labels (A17), a guard in the atom registry (A18), an enumeration in the state registry (A19). The suite loads the data; nothing asserts what it says. | A15, A17, A18, A19 |
| **The verdict of the adversarial run itself.** Its "illegal" flag is the run's only verdict and the tests reuse it, so loosening it hides two failure modes without changing today's output: a control turn that no longer commits, and a refused turn that still reached the write site. | A20 |

The split is the finding, as in legal-rag-evals: the gates stop the attacks somebody wrote down and
the properties the self-tests assert. The chokepoint's refusal paths are well covered; what routes a
turn to it, the vocabularies around it, the designer data and the run that grades it are not. Tests
for these groups are the next step; after them this catalogue is training data, and the next honest
number needs a new blind catalogue.

## What these numbers are not

- They measure the deterministic gates only, not the review layer.
- They are not a quality score for the code. They are the share of these planted defects that CI
  would stop.
- The catalogue is small and was written by a coding agent, the same kind of author as the code, so
  it may lean towards bugs an agent can imagine. It is published so that it can be challenged.
- Each bug is a single planted change; real defects interact.
- The secret scan and the dependency audit run in CI but are outside the benchmark: there is no code
  bug to plant for them.
