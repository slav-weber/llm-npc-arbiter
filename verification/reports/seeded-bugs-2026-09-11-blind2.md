# Seeded-bug benchmark · 2026-09-11 · blind2

**The deterministic gates caught 12 of 20 planted bugs (60 %).** The canary (B00) was caught by unit-tests, test-ratchet, hostile-run, atom-gate-selftest, milestone-selftest.

| | |
|---|---|
| Measured | 2026-09-11T23:10:04Z · git `236ad2f` · Windows · Python 3.12.13 |
| Tree | sha256 `fe04149bc730148b2a612415ce2b52e12d8054efa25a46814e7ed8d3c920efd1` over 78 files |
| Catalogue | `verification/seeded_bugs/catalogue_blind2.py` · sha256 `de368d85b31a39be7c88241ff09297a3050e6789c177b678faa4c65126bc0c83` |
| Gates | unit-tests · test-ratchet · lint · hostile-run · atom-gate-selftest · milestone-selftest · graph-current · data-manifest (the list CI runs: `verification/gates.py`) |

## By area

| Area | Planted | Caught |
|---|---|---|
| adversarial run | 1 | 0 |
| arbitration | 1 | 0 |
| dialect | 1 | 0 |
| dice | 1 | 1 |
| gate | 3 | 2 |
| invariants | 2 | 2 |
| knowledge | 1 | 0 |
| ledger | 2 | 0 |
| loader | 2 | 2 |
| milestones | 1 | 1 |
| quests | 1 | 1 |
| registry | 2 | 2 |
| result facts | 1 | 0 |
| schemas | 1 | 1 |

## Every bug

| Bug | Area | Planted defect | Caught by | Evidence |
|---|---|---|---|---|
| B01 | gate | An unresolved invariant name is skipped instead of refusing the commit | unit-tests, hostile-run, atom-gate-selftest | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_an_unknown_invariant_is_fail_closed (test_arbiter.Chokepoint); unregistered invariant                   committed   committed  <-- ILLEGAL; AssertionError: unknown predicate must block: CommitResult(committed=True, reason='committed', mut=[(182, 1)], proc=None, post_ok=True) |
| B02 | gate | A missing party-size scalar now reads as 'the player came alone' | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_a_missing_party_size_fails_closed (test_arbiter.Chokepoint); test_a_missing_party_size_fails_closed (test_arbiter.Chokepoint); pass the gate with no party size         committed   committed  <-- ILLEGAL |
| B03 | gate | A guard clause the evaluator cannot parse is stepped over, not refused | **missed** | — |
| B04 | loader | The skills-only exemption becomes a denylist again and forgets stamp_time | unit-tests | test_the_teacher_exemption_is_exact (test_arbiter.Registry); test_the_teacher_exemption_is_exact (test_arbiter.Registry); test_the_teacher_exemption_is_exact (test_arbiter.Registry) |
| B05 | loader | The design-source check accepts a blank or non-list citation | atom-gate-selftest | AssertionError: blank-only source must reject |
| B06 | invariants | reward_iff_started lets the success flag through on a started quest | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_the_reward_flag_is_refused_at_every_stage_the_escort_fires_from (test_arbiter.Chokepoint); grant the reward on a started quest      committed   committed  <-- ILLEGAL |
| B07 | invariants | The teaching range is widened to the engine's 300-point skill cap | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); teach two hundred points                 committed   committed  <-- ILLEGAL |
| B08 | ledger | The mutex pass is dropped from set_fact as dead code | **missed** | — |
| B09 | ledger | Empty source and region make every character perceive every object fact | **missed** | — |
| B10 | dice | The chance is clamped before the difficulty penalty instead of after | unit-tests | test_the_chance_stays_inside_the_clamp (test_arbiter.Dice); test_the_chance_stays_inside_the_clamp (test_arbiter.Dice); test_the_chance_stays_inside_the_clamp (test_arbiter.Dice); test_the_chance_stays_inside_the_clamp (test_arbiter.Dice); test_the_chance_stays_inside_the_clamp (test_arbiter.Dice); test_the_chance_stays_inside_the_clamp (test_arbiter.Dice) |
| B11 | schemas | The free-action `kind` field loses its closed set of intents | unit-tests | test_the_intent_set_is_closed (test_schemas.Schemas) |
| B12 | result facts | A registered quest is reported to the narrator as a closed quest | **missed** | — |
| B13 | arbitration | The make-leave short-circuit is deleted from the atom intent classifier | **missed** | — |
| B14 | milestones | The pre-catastrophe baseline no longer overrides the contaminated facts | milestone-selftest | AssertionError: baseline must be clean: {'health': 'тяжело ранен/при смерти после нападения; обожжён', 'want': 'чтобы Избранный нашёл ГЭКК и спас деревню от засухи; чтобы его огород пропололи от чернодушника', 'fear': 'что чёрные духи уничтожат народ', 'knows_not': 'где именно находится ГЭКК; современный мир, города и технологии за пределами племени; что творится в далёких землях чужаков', 'life_events': '0:родился в племени; стал шаманом племени; много лет служил духовным наставником; настоящее время: деревню мучает засуха и голод, он шлёт Избранного на поиски ГЭККа', 'knows': 'Наварро — место, куда улетели похитители; ГЭКК спасёт деревню', 'backstory': 'Хакунин — старый шаман небольшого племени, из которого происходит Избранный. Много десятилетий он был духовным вождём, толкователем снов и хранителем племенных традиций. Когда земля перестала родить и запасы еды иссякли, именно Хакунин убедил старейшин отправить Избранного на поиски священного ГЭККа — единственной надежды деревни перед засухой.'} |
| B15 | dialect | The runtime card belt sanitises the canon dialect speakers too | **missed** | — |
| B16 | knowledge | Runtime name resolution falls back to any node sharing a prefix | **missed** | — |
| B17 | quests | The dog's strict alias list is completed with the second name's forms | data-manifest | !! the designer data differs from verification/data_manifest.json: changed: quests/arroyo_nagor_dog.json. A deliberate data change records the new state with `uv run python -m verification.data_manifest --update` in the same commit, where a reviewer sees it. |
| B18 | registry | The Rescue Torr guard is 'normalised' to read Torr as not missing | data-manifest | !! the designer data differs from verification/data_manifest.json: changed: arbiter/atom_registry.json. A deliberate data change records the new state with `uv run python -m verification.data_manifest --update` in the same commit, where a reviewer sees it. |
| B19 | registry | critter_state.status is widened from an enumeration to free text | data-manifest | !! the designer data differs from verification/data_manifest.json: changed: arbiter/registry/fo2.state.json. A deliberate data change records the new state with `uv run python -m verification.data_manifest --update` in the same commit, where a reviewer sees it. |
| B20 | adversarial run | A missing atom becomes an empty stand-in instead of aborting the run | **missed** | — |

## Missed

- **B03** A guard clause the evaluator cannot parse is stepped over, not refused. Preparing the guard grammar for terms the engine evaluates itself (the registry's post lists already carry clauses such as cur_map==14), an agent makes the evaluator tolerant: a clause it does not recognise is skipped instead of failing the guard. A designer's typo, or a clause written with OR, is then silently dropped from the guard it was meant to impose, and a guard built only of such clauses holds against every state the atom is ever offered.
- **B08** The mutex pass is dropped from set_fact as dead code. The base state registry declares no mutex groups and the helper ignores two of the arguments it is given, so an agent pruning dead code removes the call from set_fact. A content mod that declares predicates mutually exclusive loses the rule that a new fact clears its siblings, and a subject can hold two contradictory facts at once — repaired and broken, allied and hostile — both of which are injected into the prompt.
- **B09** Empty source and region make every character perceive every object fact. An agent flattening the perception test drops the 'key and' / 'reg and' guards as redundant belt-and-braces in front of the comparisons that follow. Both sides default to the empty string — a fact written without a source or a region, an NPC queried without either — so the empty strings compare equal and characters start volunteering durable state about objects in places they have never been.
- **B12** A registered quest is reported to the narrator as a closed quest. Two adjacent arms of the fact renderer build almost the same sentence about the quest journal, so an agent deduplicating the branch merges them into one. The narrating model is then told a quest was closed on the very turn it was merely accepted, which is the completion claim every quest record forbids the brain from making before the engine flips the done variable.
- **B13** The make-leave short-circuit is deleted from the atom intent classifier. The module says the primary make-leave route is the role-annotated option index, so an agent retiring the regex floor deletes the short-circuit that made a send-them-away line neither an accept nor a go. A player telling Torr to clear off in a sentence that happens to carry a go-word («сваливай, пошли уже») classifies as go_now again and fires the pasture teleport — the spurious re-teleport the comment right above it records.
- **B15** The runtime card belt sanitises the canon dialect speakers too. Reasoning that a dossier card is the distiller's prose about a character and never the character's own lines, an agent removes the canon exemption from the runtime belt so stale cards on players' machines are cleaned for everyone. The cards of the characters whose broken speech is canon lose every sentence that describes it, and the model voices Torr and his like as ordinary, articulate people.
- **B16** Runtime name resolution falls back to any node sharing a prefix. Mirroring the build's prefix matching, an agent makes the runtime resolver accept an inflected or shortened entity name by falling back to the first graph key that starts with it. A name that is a prefix of a longer one — and an empty name, which is a prefix of everything — then borrows a stranger's neighbourhood, so the lines injected into a character's prompt as related facts belong to an entity the retrieval never matched.
- **B20** A missing atom becomes an empty stand-in instead of aborting the run. An agent makes the hostile run survive registry edits: a scenario whose atom is no longer in the live whitelist gets an empty stand-in, which the gate refuses as inert, rather than the whole run dying on a KeyError. An atom the loader has quietly started rejecting then leaves its attacks 'refused' for the wrong reason, and the table and the exit code report a clean run over checks that were never exercised at all.

## Reproduce

```bash
uv sync
uv run python -m verification.seeded_bugs.run --catalogue verification/seeded_bugs/catalogue_blind2.py --no-write
```
