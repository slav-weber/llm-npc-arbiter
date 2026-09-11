# Seeded-bug benchmark · 2026-09-11

**The deterministic gates caught 5 of 20 planted bugs (25 %).** The canary (A00) was caught by unit-tests, test-ratchet, hostile-run, atom-gate-selftest, milestone-selftest.

| | |
|---|---|
| Measured | 2026-09-11T14:37:16Z · git `1a7a4c7` · Windows · Python 3.12.13 |
| Tree | sha256 `36552bfc5a39e36c1e16a66f1c4e63d3c98968c144e05613bbc425eb233ea79f` over 70 files |
| Catalogue | `verification/seeded_bugs/catalogue.py` · sha256 `1b86d72879493bb9ba5ea84bf69a72a02cb070cd2eb33ba9f52cc9323da73994` |
| Gates | unit-tests · test-ratchet · lint · hostile-run · atom-gate-selftest · milestone-selftest · graph-current (the list CI runs: `verification/gates.py`) |

## By area

| Area | Planted | Caught |
|---|---|---|
| adversarial run | 1 | 0 |
| arbitration | 2 | 0 |
| dialect | 1 | 0 |
| dice | 1 | 0 |
| gate | 3 | 1 |
| invariants | 2 | 1 |
| knowledge | 1 | 0 |
| ledger | 1 | 1 |
| loader | 2 | 1 |
| milestones | 1 | 1 |
| quests | 1 | 0 |
| registry | 2 | 0 |
| result facts | 1 | 0 |
| schemas | 1 | 0 |

## Every bug

| Bug | Area | Planted defect | Caught by | Evidence |
|---|---|---|---|---|
| A01 | gate | An unregistered invariant name is skipped instead of refusing the commit | unit-tests, hostile-run, atom-gate-selftest | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_an_unknown_invariant_is_fail_closed (test_arbiter.Chokepoint); unregistered invariant                   committed   committed  <-- ILLEGAL; AssertionError: unknown predicate must block: CommitResult(committed=True, reason='committed', mut=[(182, 1)], proc=None, post_ok=True) |
| A02 | gate | A failed post-assert on a procedure atom no longer halts further commits | **missed** | — |
| A03 | gate | A missing party size is read as 'alone', so party_size(0)==0 guards pass | **missed** | — |
| A04 | loader | The guard-free teacher exemption accepts any once_per_npc atom with skills | **missed** | — |
| A05 | loader | A design source made of blank strings satisfies the fail-closed loader | atom-gate-selftest | AssertionError: blank-only source must reject |
| A06 | invariants | reward_iff_started lets an atom write the success flag once the quest started | **missed** | — |
| A07 | invariants | skills_only accepts lessons of up to 300 points instead of 1..20 | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); teach two hundred points                 committed   committed  <-- ILLEGAL |
| A08 | ledger | An undeclared predicate validates as a free-text slot | unit-tests, hostile-run | test_no_hostile_turn_writes_anything (test_arbiter.AdversarialRun); test_a_value_outside_the_enumeration_is_dropped (test_arbiter.Ledger); test_validate_reports_the_reason (test_arbiter.Ledger); undeclared predicate                     stored      faction_stance:ncr:owns_everything=true  <-- ILLEGAL; value outside the enumeration            stored      faction_stance:ncr:stance=worships_the_player  <-- ILLEGAL |
| A09 | dice | Difficulties below 1 now subtract a negative penalty, a bonus the model picks | **missed** | — |
| A10 | schemas | The narrating call gains a state_set field, a durable-write channel | **missed** | — |
| A11 | result facts | A mercy fact renders as 'the enemy agreed' unless it says refused | **missed** | — |
| A12 | arbitration | A negated go-word classifies as go_now and can fire a teleport | **missed** | — |
| A13 | arbitration | Acceptance is tested before the generic job-seeking veto | **missed** | — |
| A14 | milestones | The pre-milestone baseline no longer overrides the contaminated fields | milestone-selftest | AssertionError: baseline must be clean: {'health': 'тяжело ранен/при смерти после нападения; обожжён', 'want': 'чтобы Избранный нашёл ГЭКК и спас деревню от засухи; чтобы его огород пропололи от чернодушника', 'fear': 'что чёрные духи уничтожат народ', 'knows_not': 'где именно находится ГЭКК; современный мир, города и технологии за пределами племени; что творится в далёких землях чужаков', 'life_events': '0:родился в племени; стал шаманом племени; много лет служил духовным наставником; настоящее время: деревню мучает засуха и голод, он шлёт Избранного на поиски ГЭККа', 'knows': 'Наварро — место, куда улетели похитители; ГЭКК спасёт деревню', 'backstory': 'Хакунин — старый шаман небольшого племени, из которого происходит Избранный. Много десятилетий он был духовным вождём, толкователем снов и хранителем племенных традиций. Когда земля перестала родить и запасы еды иссякли, именно Хакунин убедил старейшин отправить Избранного на поиски священного ГЭККа — единственной надежды деревни перед засухой.'} |
| A15 | dialect | Nancy's allowlist entry is parked, so her canon pidgin gets scrubbed | **missed** | — |
| A16 | knowledge | A corrupt graph file now raises from every retrieval instead of degrading | **missed** | — |
| A17 | quests | The betrayal value 198=4 of the still quest is relabelled as done | **missed** | — |
| A18 | registry | The Rescue Torr atom now fires only when Torr is not missing | **missed** | — |
| A19 | registry | critter_state.status becomes a free string, so any status is stored | **missed** | — |
| A20 | adversarial run | The hostile run flags only unauthorised commits as illegal | **missed** | — |

## Missed

- **A02** A failed post-assert on a procedure atom no longer halts further commits. After one flaky post-assert froze every quest atom for the rest of a play session, an agent turns the halt into an escalation so a single bad procedure cannot take the whole layer down. A procedure that leaves the world violating the atom's invariants is now only reported, and the next commit goes ahead on a state nobody has checked.
- **A03** A missing party size is read as 'alone', so party_size(0)==0 guards pass. An agent simplifies the party-size normalisation to int(party_size or 0), the same default every other missing variable gets. When the engine does not report the escort size, the Navarro sentry's 'recruits arrive alone' clause now holds, and a player with a retinue walks through the gate: the guard fails open where the docstring demands it fail closed.
- **A04** The guard-free teacher exemption accepts any once_per_npc atom with skills. A designer added a 'post' list to a teacher row and the loader rejected it for a missing durable guard, so an agent relaxes the exact-set test to a membership test. Any once_per_npc atom that carries skills now loads without a durable guard even when it also writes a quest variable, a procedure or a timestamp: the allowlist from the adversarial review is gone.
- **A06** reward_iff_started lets an atom write the success flag once the quest started. An agent makes the predicate match its name, 'reward if and only if started', by allowing the success flag once the quest stage is at least 1. The designer's rule was that the atom never touches the reward: a go-now turn at stage 1 whose effect carries 'set gvar 85 = 1' now passes every invariant of the escort atom and grants the reward.
- **A09** Difficulties below 1 now subtract a negative penalty, a bonus the model picks. The model is told to fold easing modifiers into difficulty, and the floor swallowed every bonus below 1, so an agent removes the max(0, ...). The schema only says integer: a model that answers difficulty -9 lifts a character with no skill from 5% to 95%, so the chance is chosen by the model rather than computed from the character's statistics.
- **A10** The narrating call gains a state_set field, a durable-write channel. Ledger deltas declared by the decide leg sometimes contradicted the narration, so an agent gives the narrate leg its own state_set, to be written by the call that has already seen the result facts. The narrating model, which may only describe what the engine made true, can now lock durable world state from its own prose.
- **A11** A mercy fact renders as 'the enemy agreed' unless it says refused. An agent aligns mercy with the bare flags such as dead or ko, where the key's presence means the thing happened, and flips the test to check for an explicit refusal. A bare 'mercy' or any value outside the pair now tells the narrator that the enemy agreed to spare the player, a fact the engine never reported.
- **A12** A negated go-word classifies as go_now and can fire a teleport. Consolidating negation handling, an agent drops the ad-hoc 'no/not' test on the go branch, reasoning that make-leave lines are filtered just above and refusals are the refusal regex's job. A refusal that happens to contain a go-word, 'I am not going anywhere', now classifies as go_now, and on the atom_id bypass path it fires the terminal teleport to the pasture.
- **A13** Acceptance is tested before the generic job-seeking veto. While reordering the classifier so that the positive intents read first, an agent moves the acceptance test above the work-seeking veto. Job-seeking lines that contain an accept stem, such as 'ready for anything' or 'I will take any job', are accepted again, so a quest atom fires before the NPC has offered anything: the live 'looking for work' bug returns.
- **A15** Nancy's allowlist entry is parked, so her canon pidgin gets scrubbed. Reading that Nancy's normal register is literate, an agent parks her allowlist entry with the side-car's underscore convention until someone re-checks the message file. The loader skips underscored keys, so her canon telegraphic pidgin with the servants is cut from her distillation input and sanitised out of her card: a canon dialect is 'corrected'.
- **A16** A corrupt graph file now raises from every retrieval instead of degrading. A lint cleanup narrows the broad except in the graph loader to FileNotFoundError, since the comment only mentions a missing file. A truncated or half-written graph.json, as an interrupted rebuild leaves behind, now raises JSONDecodeError from every neighbour expansion, so the optional layer takes retrieval down with it.
- **A17** The betrayal value 198=4 of the still quest is relabelled as done. An agent reconciles the still quest's stages with its completed threshold of 3: quests.txt closes the journal entry at any value of 3 or more, so it relabels 198=4 as done, the way the Pip-Boy shows it. When the player has sold the still to Sajag, the quest now reads as a success and Bob thanks the player for a refuel he sabotaged.
- **A18** The Rescue Torr atom now fires only when Torr is not missing. Normalising the Klamath guards, an agent notices that every other atom reads gvar 71 as ==0 ('the NPC is not missing') and corrects this one to match. The rescue can now be accepted only while Torr is at home and never while he is missing: the journal registers 'Rescue Torr' for a son standing in the pasture, a write the designer never authorised.
- **A19** critter_state.status becomes a free string, so any status is stored. The model keeps reporting statuses such as 'wounded' or 'captured' that the enumeration drops, so an agent loosens the predicate to a string. Any value now validates: the model can record a character as burned, captured or immortal by writing it, the fact is injected into the prompt of everyone who perceives that character, and the rumour seeder spreads it.
- **A20** The hostile run flags only unauthorised commits as illegal. An agent reads 'illegal' as 'an unauthorised commit' and simplifies the expression. Two failure modes vanish from the report: a control turn that no longer commits, which is what a gate that refuses everything looks like, and a refused turn whose write site was still called. The run keeps printing 0 illegal while the gate is broken.

## Reproduce

```bash
uv sync
uv run python -m verification.seeded_bugs.run --no-write
```
