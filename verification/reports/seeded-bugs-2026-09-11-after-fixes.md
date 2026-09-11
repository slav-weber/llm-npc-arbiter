# Seeded-bug benchmark · 2026-09-11 · after-fixes

**The deterministic gates caught 20 of 20 planted bugs (100 %).** The canary (A00) was caught by unit-tests, test-ratchet, hostile-run, atom-gate-selftest, milestone-selftest.

| | |
|---|---|
| Measured | 2026-09-11T20:17:36Z · git `fa599c2` · Windows · Python 3.12.13 |
| Tree | sha256 `490f84db7f30959818f81f8715aed2abae1d1f01ca91063dc31767ad26468b3b` over 77 files |
| Catalogue | `verification/seeded_bugs/catalogue.py` · sha256 `1b86d72879493bb9ba5ea84bf69a72a02cb070cd2eb33ba9f52cc9323da73994` |
| Gates | unit-tests · test-ratchet · lint · hostile-run · atom-gate-selftest · milestone-selftest · graph-current · data-manifest (the list CI runs: `verification/gates.py`) |

## By area

| Area | Planted | Caught |
|---|---|---|
| adversarial run | 1 | 1 |
| arbitration | 2 | 2 |
| dialect | 1 | 1 |
| dice | 1 | 1 |
| gate | 3 | 3 |
| invariants | 2 | 2 |
| knowledge | 1 | 1 |
| ledger | 1 | 1 |
| loader | 2 | 2 |
| milestones | 1 | 1 |
| quests | 1 | 1 |
| registry | 2 | 2 |
| result facts | 1 | 1 |
| schemas | 1 | 1 |

## Every bug

| Bug | Area | Planted defect | Caught by | Evidence |
|---|---|---|---|---|
| A01 | gate | An unregistered invariant name is skipped instead of refusing the commit | unit-tests, hostile-run, atom-gate-selftest | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_an_unknown_invariant_is_fail_closed (test_arbiter.Chokepoint); unregistered invariant                   committed   committed  <-- ILLEGAL; AssertionError: unknown predicate must block: CommitResult(committed=True, reason='committed', mut=[(182, 1)], proc=None, post_ok=True) |
| A02 | gate | A failed post-assert on a procedure atom no longer halts further commits | unit-tests, atom-gate-selftest | test_a_failed_post_assert_halts_the_next_valid_commit (test_arbiter.PostAssert); AssertionError: post-assert fail must HALT further commits: CommitResult(committed=True, reason='committed', mut=[(182, 1)], proc={'script': 'kctorr', 'proc': 'Node020'}, post_ok=True) |
| A03 | gate | A missing party size is read as 'alone', so party_size(0)==0 guards pass | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_a_missing_party_size_fails_closed (test_arbiter.Chokepoint); test_a_missing_party_size_fails_closed (test_arbiter.Chokepoint); pass the gate with no party size         committed   committed  <-- ILLEGAL |
| A04 | loader | The guard-free teacher exemption accepts any once_per_npc atom with skills | unit-tests | test_the_teacher_exemption_is_exact (test_arbiter.Registry); test_the_teacher_exemption_is_exact (test_arbiter.Registry); test_the_teacher_exemption_is_exact (test_arbiter.Registry); test_the_teacher_exemption_is_exact (test_arbiter.Registry); test_the_teacher_exemption_is_exact (test_arbiter.Registry); test_the_teacher_exemption_is_exact (test_arbiter.Registry) |
| A05 | loader | A design source made of blank strings satisfies the fail-closed loader | atom-gate-selftest | AssertionError: blank-only source must reject |
| A06 | invariants | reward_iff_started lets an atom write the success flag once the quest started | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_the_reward_flag_is_refused_at_every_stage_the_escort_fires_from (test_arbiter.Chokepoint); grant the reward on a started quest      committed   committed  <-- ILLEGAL |
| A07 | invariants | skills_only accepts lessons of up to 300 points instead of 1..20 | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); teach two hundred points                 committed   committed  <-- ILLEGAL |
| A08 | ledger | An undeclared predicate validates as a free-text slot | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_a_value_outside_the_enumeration_is_dropped (test_arbiter.Ledger); test_validate_reports_the_reason (test_arbiter.Ledger); undeclared predicate                     stored      faction_stance:ncr:owns_everything=true  <-- ILLEGAL; value outside the enumeration            stored      faction_stance:ncr:stance=worships_the_player  <-- ILLEGAL |
| A09 | dice | Difficulties below 1 now subtract a negative penalty, a bonus the model picks | unit-tests | test_a_difficulty_below_one_gives_no_bonus (test_arbiter.Dice); test_a_difficulty_below_one_gives_no_bonus (test_arbiter.Dice); test_a_difficulty_below_one_gives_no_bonus (test_arbiter.Dice); test_a_difficulty_below_one_gives_no_bonus (test_arbiter.Dice); test_a_difficulty_below_one_gives_no_bonus (test_arbiter.Dice); test_a_difficulty_below_one_gives_no_bonus (test_arbiter.Dice) |
| A10 | schemas | The narrating call gains a state_set field, a durable-write channel | unit-tests | test_the_narrating_calls_offer_no_write_channel (test_schemas.Schemas) |
| A11 | result facts | A mercy fact renders as 'the enemy agreed' unless it says refused | unit-tests | test_mercy_is_rendered_as_granted_only_when_the_engine_reports_a_yield (test_result_facts.ResultFacts); test_mercy_is_rendered_as_granted_only_when_the_engine_reports_a_yield (test_result_facts.ResultFacts); test_mercy_is_rendered_as_granted_only_when_the_engine_reports_a_yield (test_result_facts.ResultFacts); test_mercy_is_rendered_as_granted_only_when_the_engine_reports_a_yield (test_result_facts.ResultFacts); test_mercy_is_rendered_as_granted_only_when_the_engine_reports_a_yield (test_result_facts.ResultFacts) |
| A12 | arbitration | A negated go-word classifies as go_now and can fire a teleport | unit-tests | test_a_negated_go_word_is_not_go_now (test_atom_arbitration.Arbitration); test_a_negated_go_word_is_not_go_now (test_atom_arbitration.Arbitration); test_a_negated_go_word_is_not_go_now (test_atom_arbitration.Arbitration); test_a_negated_go_word_is_not_go_now (test_atom_arbitration.Arbitration) |
| A13 | arbitration | Acceptance is tested before the generic job-seeking veto | unit-tests | test_job_seeking_with_an_accept_stem_is_vetoed (test_atom_arbitration.Arbitration); test_job_seeking_with_an_accept_stem_is_vetoed (test_atom_arbitration.Arbitration); test_job_seeking_with_an_accept_stem_is_vetoed (test_atom_arbitration.Arbitration); test_job_seeking_with_an_accept_stem_is_vetoed (test_atom_arbitration.Arbitration) |
| A14 | milestones | The pre-milestone baseline no longer overrides the contaminated fields | milestone-selftest | AssertionError: baseline must be clean: {'health': 'тяжело ранен/при смерти после нападения; обожжён', 'want': 'чтобы Избранный нашёл ГЭКК и спас деревню от засухи; чтобы его огород пропололи от чернодушника', 'fear': 'что чёрные духи уничтожат народ', 'knows_not': 'где именно находится ГЭКК; современный мир, города и технологии за пределами племени; что творится в далёких землях чужаков', 'life_events': '0:родился в племени; стал шаманом племени; много лет служил духовным наставником; настоящее время: деревню мучает засуха и голод, он шлёт Избранного на поиски ГЭККа', 'knows': 'Наварро — место, куда улетели похитители; ГЭКК спасёт деревню', 'backstory': 'Хакунин — старый шаман небольшого племени, из которого происходит Избранный. Много десятилетий он был духовным вождём, толкователем снов и хранителем племенных традиций. Когда земля перестала родить и запасы еды иссякли, именно Хакунин убедил старейшин отправить Избранного на поиски священного ГЭККа — единственной надежды деревни перед засухой.'} |
| A15 | dialect | Nancy's allowlist entry is parked, so her canon pidgin gets scrubbed | data-manifest | !! the designer data differs from verification/data_manifest.json: changed: arbiter/dialect_canon.json. A deliberate data change records the new state with `uv run python -m verification.data_manifest --update` in the same commit, where a reviewer sees it. |
| A16 | knowledge | A corrupt graph file now raises from every retrieval instead of degrading | unit-tests | test_a_corrupt_or_half_written_graph_file_degrades_to_a_no_op (test_knowledge_graph.GraphDegradation); test_a_corrupt_or_half_written_graph_file_degrades_to_a_no_op (test_knowledge_graph.GraphDegradation); test_a_corrupt_or_half_written_graph_file_degrades_to_a_no_op (test_knowledge_graph.GraphDegradation) |
| A17 | quests | The betrayal value 198=4 of the still quest is relabelled as done | data-manifest | !! the designer data differs from verification/data_manifest.json: changed: quests/q198_klamath_still.json. A deliberate data change records the new state with `uv run python -m verification.data_manifest --update` in the same commit, where a reviewer sees it. |
| A18 | registry | The Rescue Torr atom now fires only when Torr is not missing | data-manifest | !! the designer data differs from verification/data_manifest.json: changed: arbiter/atom_registry.json. A deliberate data change records the new state with `uv run python -m verification.data_manifest --update` in the same commit, where a reviewer sees it. |
| A19 | registry | critter_state.status becomes a free string, so any status is stored | data-manifest | !! the designer data differs from verification/data_manifest.json: changed: arbiter/registry/fo2.state.json. A deliberate data change records the new state with `uv run python -m verification.data_manifest --update` in the same commit, where a reviewer sees it. |
| A20 | adversarial run | The hostile run flags only unauthorised commits as illegal | unit-tests | test_a_control_that_no_longer_commits_is_illegal (test_arbiter.AdversarialRun); test_a_refused_turn_that_reached_the_write_site_is_illegal (test_arbiter.AdversarialRun); test_a_refused_turn_that_reached_the_write_site_is_illegal (test_arbiter.AdversarialRun); test_a_refused_turn_that_reached_the_write_site_is_illegal (test_arbiter.AdversarialRun); test_a_refused_turn_that_reached_the_write_site_is_illegal (test_arbiter.AdversarialRun); test_a_refused_turn_that_reached_the_write_site_is_illegal (test_arbiter.AdversarialRun) |

## Reproduce

```bash
uv sync
uv run python -m verification.seeded_bugs.run --no-write
```
