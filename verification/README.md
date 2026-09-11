# Verification

This directory answers one question about the repository: **how much of what can go wrong would CI
actually stop?** It holds the gates CI runs and a benchmark that measures them by planting realistic
bugs one at a time, from a catalogue written by an agent that never saw the tests.

## The gates

| Gate | What a pass proves | CI | pre-commit | Benchmark |
|---|---|---|---|---|
| `unit-tests` | the 34 tests pass (no engine, no model, no network) | every push | | yes |
| `test-ratchet` | every recorded test still exists and every skip is on the allowed list | every push | | yes |
| `lint` | ruff finds nothing under the rule set in `pyproject.toml` (E, F, W) | every push | staged files | yes |
| `hostile-run` | every hostile turn in `adversarial/hostile_runs.py` is refused or dropped, and the control turn commits | every push | | yes |
| `atom-gate-selftest` | the atom gate's own self-test: fail-closed loader, single write site, composite effects, post-assert and halt | every push | | yes |
| `milestone-selftest` | a character gated by a world milestone keeps its baseline until the milestone fires; an ungated one is untouched | every push | | yes |
| `graph-current` | `knowledge/graph.json` is exactly what `knowledge/world.json` builds | every push | | yes |
| `data-manifest` | every designer data file (each JSON under `arbiter/`, `quests/` and `knowledge/`) has the digest recorded in `data_manifest.json`; none was changed, added or removed | every push | | yes |
| secret scan | no secret in any commit (gitleaks 8.30.1, checksum-verified, full history) | every push | staged changes | |
| dependency audit | no known vulnerability in the development tools pinned by `uv.lock` (the runtime has no dependencies) | every push, weekly | | |

The first eight are defined once, in `gates.py`; CI calls them one by one and the benchmark runs all
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

### The data manifest

The suite loads the designer data but asserts little of what it says, so a guard in the atom
registry, an enumeration in the state registry, a quest's stage label or an entry of the dialect
allowlist can change as a side effect of another task while every other gate stays green.
`data_manifest.py` records the sha256 of every designer data file (each `*.json` under `arbiter/`,
`quests/` and `knowledge/`, hashed with its line endings normalised to LF) in `data_manifest.json`,
and fails, naming the files, when one is changed, added or removed. A deliberate data change runs
`uv run python -m verification.data_manifest --update` in the same commit, where a reviewer sees the
manifest change next to the data.

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
- `.claude/settings.json` makes editing the test inventory, the data manifest, the catalogues, the
  reports, the gate list, CI or designer data (the atom registry, the state registry, the quests, the
  side-cars, the corpus), and pushing, ask a person first; reading `.env` is denied.

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
turn to it, the vocabularies around it, the designer data and the run that grades it are not.

### After the fixes: 20 of 20, on what is now a training set

Report: [`reports/seeded-bugs-2026-09-11-after-fixes.md`](reports/seeded-bugs-2026-09-11-after-fixes.md).

| Group | Closed by |
|---|---|
| the halt check that passed for the wrong reason (A02) | a test that halts a valid commit after a failed post-assert and lets it through after the reset, and a self-test whose second commit can fail only on the halt |
| scenarios tried in one state (A03, A06) | tests, and two new hostile scenarios: a missing party size, the reward on a started quest |
| branches no test drove (A04, A09, A16) | the teacher exemption against seven other effect kinds; difficulties below 1; missing, empty, cut-off, non-text and wrongly shaped graph files |
| modules no test imported (A10–A13) | `tests/test_schemas.py`, `tests/test_result_facts.py`, `tests/test_atom_arbitration.py` |
| designer data nobody pinned (A15, A17–A19) | the `data-manifest` gate |
| the adversarial run's own verdict (A20) | tests that make the gate refuse everything, or reach the write site on a refusal, and expect the run to flag it |

All twenty are caught now. That shows the fixes work, not that the gates generalise: the tests were
written knowing the bugs, so the next honest number needs a second blind catalogue.

Closing the gaps also turned up four places where the documentation promised more than the code;
they are corrected or disclosed now. The schemas in `arbiter/schemas.py` are not closed by the module
itself: the caller, which is not in this extract, applies strict mode. No predicate shipped here
reads the post-state, so the post-assert has no shipped customer. The hostile run's recorder sees
variable writes and procedures, not map-variable, local-variable or skill effects. And a graph file
of the wrong shape still raised, which `knowledge/graph.py` now degrades like a missing one.

### Second blind catalogue: 12 of 20

Report: [`reports/seeded-bugs-2026-09-11-blind2.md`](reports/seeded-bugs-2026-09-11-blind2.md),
measured on git `236ad2f`. Its author saw the code, the data and the documentation as they are after
the fixes, and never the tests. The split below was fixed in the catalogue's commit message, before
the run.

| Second catalogue | Planted | Caught |
|---|---|---|
| repeats of a class the first catalogue already had | 10 | 9 |
| new classes | 10 | 3 |
| all | 20 | 12 |

Five of 20 became 12 of 20, and the shape of that gain is the finding: the classes the first
catalogue named are held 9 of 10, the classes nobody had planted before only 3 of 10. Tests close
the ground they were written for.

| Missed | Why nothing failed |
|---|---|
| B03: a guard clause the evaluator cannot parse is stepped over instead of refusing the commit | every guard in the tests and in the hostile table is one the evaluator understands; none is malformed |
| B08: the ledger's mutex pass is dropped, so a fact no longer clears its siblings | the ledger tests drop undeclared writes; none writes a predicate whose siblings must be cleared |
| B09: an empty source and region make every character perceive every object fact | nothing reads a fact back through the perception filter |
| B12: a registered quest is reported to the narrator as a closed one | the result-fact test pins the mercy mapping; the quest-state mapping has none |
| B13: the make-leave short-circuit is deleted from the intent classifier | the classifier tests pin the negation test and the job-seeking veto; this is a third guard nobody pinned |
| B15: the runtime belt sanitises the canon dialect speakers too | `dialect_guard.py` has no test, and the data manifest pins the allowlist, not the code that reads it |
| B16: graph name resolution falls back to any node sharing a prefix | the graph tests pin degradation on a broken file; nothing pins how a name resolves |
| B20: a missing atom becomes an empty stand-in instead of aborting the adversarial run | the run's verdict is tested; the lookup that must abort it when an atom is missing is not |

Seven of the eight sit in a module or a branch the new tests did not reach: the same lesson as the
first round, one layer further in. This catalogue is training data from here on.

## What these numbers are not

- They measure the deterministic gates only, not the review layer.
- They are not a quality score for the code. They are the share of these planted defects that CI
  would stop.
- The catalogue is small and was written by a coding agent, the same kind of author as the code, so
  it may lean towards bugs an agent can imagine. It is published so that it can be challenged.
- Each bug is a single planted change; real defects interact.
- The secret scan and the dependency audit run in CI but are outside the benchmark: there is no code
  bug to plant for them.
