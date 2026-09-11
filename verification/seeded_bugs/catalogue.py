"""First seeded-bug catalogue: twenty realistic defects plus one canary, written by an agent that
saw only a copy of the source code, data and documentation, without the tests, and that ran no
test, gate or script. Exact find->replace edits, each find occurring exactly once, one import-time
canary. Chosen by domain realism and consequence, never tuned to a measured result.
"""

from __future__ import annotations

from verification.seeded_bugs.records import Bug, Edit

BUGS: tuple[Bug, ...] = (
    Bug("A00", "canary", "Import-time crash in arbiter/atom_gate.py",
        "Not a realistic bug: it proves that the runner applies edits and that the gates see them.",
        (Edit("arbiter/atom_gate.py",
              "_HERE = os.path.dirname(os.path.abspath(__file__))",
              'raise RuntimeError("seeded canary")\n_HERE = os.path.dirname(os.path.abspath(__file__))'),),
        canary=True),

    Bug("A01", "gate", "An unregistered invariant name is skipped instead of refusing the commit",
        "After a renamed predicate made a whole quest line unfireable, an agent downgrades an unresolved "
        "invariant from a refusal to a loud escalation and moves on to the next name. An atom that "
        "declares a misspelled or never-registered invariant (the model's 'always_allow') now commits "
        "with that safety rule silently evaluating to nothing.",
        (Edit("arbiter/atom_gate.py",
              "        if fn is None:\n"
              "            return CommitResult(False, f\"unresolved invariant predicate '{nm}' "
              "(no predicate is registered \"\n"
              "                                       f\"under that name)\")\n",
              "        if fn is None:\n"
              "            _escalate(atom.get(\"atom_id\", \"?\"), f\"unresolved invariant predicate "
              "'{nm}' skipped\")\n"
              "            continue\n"),)),

    Bug("A02", "gate", "A failed post-assert on a procedure atom no longer halts further commits",
        "After one flaky post-assert froze every quest atom for the rest of a play session, an agent "
        "turns the halt into an escalation so a single bad procedure cannot take the whole layer down. "
        "A procedure that leaves the world violating the atom's invariants is now only reported, and "
        "the next commit goes ahead on a state nobody has checked.",
        (Edit("arbiter/atom_gate.py",
              "                _HALTED = True\n"
              "                _escalate(atom.get(\"atom_id\", \"?\"), f\"POST-ASSERT '{nm}' failed "
              "\u2014 halting further commits\")",
              "                _escalate(atom.get(\"atom_id\", \"?\"), f\"POST-ASSERT '{nm}' failed "
              "\u2014 escalated\")"),)),

    Bug("A03", "gate", "A missing party size is read as 'alone', so party_size(0)==0 guards pass",
        "An agent simplifies the party-size normalisation to int(party_size or 0), the same default "
        "every other missing variable gets. When the engine does not report the escort size, the "
        "Navarro sentry's 'recruits arrive alone' clause now holds, and a player with a retinue walks "
        "through the gate: the guard fails open where the docstring demands it fail closed.",
        (Edit("arbiter/atom_gate.py",
              '"party_size": {0: (int(party_size) if party_size is not None else 99)}}',
              '"party_size": {0: int(party_size or 0)}}'),)),

    Bug("A04", "loader", "The guard-free teacher exemption accepts any once_per_npc atom with skills",
        "A designer added a 'post' list to a teacher row and the loader rejected it for a missing "
        "durable guard, so an agent relaxes the exact-set test to a membership test. Any once_per_npc "
        "atom that carries skills now loads without a durable guard even when it also writes a quest "
        "variable, a procedure or a timestamp: the allowlist from the adversarial review is gone.",
        (Edit("arbiter/atom_gate.py",
              'and has_skills and _eff_keys == {"skills"}',
              'and has_skills and "skills" in _eff_keys'),)),

    Bug("A05", "loader", "A design source made of blank strings satisfies the fail-closed loader",
        "Tidying the loader's repeated isinstance/any(strip) idiom, an agent reduces the design-source "
        "check to a truthiness test. A list of empty strings or a bare placeholder string now passes, "
        "so an atom whose design intent cites nothing is loaded silently instead of being escalated "
        "for a human to clear.",
        (Edit("arbiter/atom_gate.py",
              "    if not isinstance(src, list) or not any(str(s).strip() for s in src):",
              "    if not src:"),)),

    Bug("A06", "invariants", "reward_iff_started lets an atom write the success flag once the quest started",
        "An agent makes the predicate match its name, 'reward if and only if started', by allowing the "
        "success flag once the quest stage is at least 1. The designer's rule was that the atom never "
        "touches the reward: a go-now turn at stage 1 whose effect carries 'set gvar 85 = 1' now passes "
        "every invariant of the escort atom and grants the reward.",
        (Edit("arbiter/invariants.py",
              'r("reward_iff_started", lambda c: _S not in _mut(c))',
              'r("reward_iff_started", lambda c: _S not in _mut(c) or c["before"].get(_Q, 0) >= 1)'),)),

    Bug("A07", "invariants", "skills_only accepts lessons of up to 300 points instead of 1..20",
        "The engine already halves tagged skills and caps them at 300, so an agent aligns the teaching "
        "range with the engine cap instead of keeping a second, seemingly arbitrary limit. A model that "
        "inflates a lesson to 'Unarmed:200' now passes skills_only, and one teacher turn can raise a "
        "skill by hundreds of points.",
        (Edit("arbiter/invariants.py",
              "return all(1 <= p <= 20 for _s, p in",
              "return all(1 <= p <= 300 for _s, p in"),)),

    Bug("A08", "ledger", "An undeclared predicate validates as a free-text slot",
        "A mod declared a free-text predicate as an empty spec (the type defaults to string) and every "
        "write to it was refused, because an empty dict is falsy. The agent tests 'is None' and gives "
        "the lookup an empty-dict default for symmetry, which turns every undeclared predicate into a "
        "string slot: 'faction_stance:ncr:owns_everything=true' is stored and injected into prompts.",
        (Edit("arbiter/ledger.py",
              '    p = (spec.get("predicates") or {}).get(predicate)\n    if not p:\n',
              '    p = (spec.get("predicates") or {}).get(predicate, {})\n    if p is None:\n'),)),

    Bug("A09", "dice", "Difficulties below 1 now subtract a negative penalty, a bonus the model picks",
        "The model is told to fold easing modifiers into difficulty, and the floor swallowed every bonus "
        "below 1, so an agent removes the max(0, ...). The schema only says integer: a model that "
        "answers difficulty -9 lifts a character with no skill from 5% to 95%, so the chance is chosen "
        "by the model rather than computed from the character's statistics.",
        (Edit("arbiter/dice.py",
              "    return max(0, (d - 1) * 10)",
              "    return (d - 1) * 10"),)),

    Bug("A10", "schemas", "The narrating call gains a state_set field, a durable-write channel",
        "Ledger deltas declared by the decide leg sometimes contradicted the narration, so an agent gives "
        "the narrate leg its own state_set, to be written by the call that has already seen the result "
        "facts. The narrating model, which may only describe what the engine made true, can now lock "
        "durable world state from its own prose.",
        (Edit("arbiter/schemas.py",
              '    "object_deed_done": {"type": "integer"},\n}',
              '    "object_deed_done": {"type": "integer"},\n'
              '    # Ledger: the durable delta, locked by the leg that has already seen the RESULT facts.\n'
              '    "state_set": {"type": "string"},\n}'),)),

    Bug("A11", "result facts", "A mercy fact renders as 'the enemy agreed' unless it says refused",
        "An agent aligns mercy with the bare flags such as dead or ko, where the key's presence means "
        "the thing happened, and flips the test to check for an explicit refusal. A bare 'mercy' or any "
        "value outside the pair now tells the narrator that the enemy agreed to spare the player, a "
        "fact the engine never reported.",
        (Edit("arbiter/result_facts.py",
              'lines.append("Враг СОГЛАСИЛСЯ пощадить." if val == "yielded" else "Враг ОТКАЗАЛ в пощаде.")',
              'lines.append("Враг ОТКАЗАЛ в пощаде." if val == "refused" '
              'else "Враг СОГЛАСИЛСЯ пощадить.")'),)),

    Bug("A12", "arbitration", "A negated go-word classifies as go_now and can fire a teleport",
        "Consolidating negation handling, an agent drops the ad-hoc 'no/not' test on the go branch, "
        "reasoning that make-leave lines are filtered just above and refusals are the refusal regex's "
        "job. A refusal that happens to contain a go-word, 'I am not going anywhere', now classifies as "
        "go_now, and on the atom_id bypass path it fires the terminal teleport to the pasture.",
        (Edit("arbiter/atom_arbitration.py",
              'if _GO_INTENT_RE.search(p) and not re.search(r"\\bне\\b|\\bнет\\b", p.lower()):',
              "if _GO_INTENT_RE.search(p):"),)),

    Bug("A13", "arbitration", "Acceptance is tested before the generic job-seeking veto",
        "While reordering the classifier so that the positive intents read first, an agent moves the "
        "acceptance test above the work-seeking veto. Job-seeking lines that contain an accept stem, "
        "such as 'ready for anything' or 'I will take any job', are accepted again, so a quest atom "
        "fires before the NPC has offered anything: the live 'looking for work' bug returns.",
        (Edit("arbiter/atom_arbitration.py",
              "    if _GENERIC_WORKSEEK_RE.search(p) and not _GO_INTENT_RE.search(p):\n"
              "        return None       # generic job-seeking with no go-word -> neither intent "
              "(the NPC offers first)\n"
              "    if _acceptance_intent(p):\n"
              "        return \"accept\"   # «я помогу / согласен / берусь» "
              "\u2014 the flag-only accept atom, "
              "negation-aware\n",
              "    if _acceptance_intent(p):\n"
              "        return \"accept\"   # «я помогу / согласен / берусь» "
              "\u2014 the flag-only accept atom, "
              "negation-aware\n"
              "    if _GENERIC_WORKSEEK_RE.search(p) and not _GO_INTENT_RE.search(p):\n"
              "        return None       # generic job-seeking with no go-word -> neither intent "
              "(the NPC offers first)\n"),)),

    Bug("A14", "milestones", "The pre-milestone baseline no longer overrides the contaminated fields",
        "An agent treats the baseline as defaults that should only fill gaps, and swaps the merge so a "
        "field the character's own facts already carry is never overwritten. Every contaminated field "
        "is present in the original facts, so the baseline never wins: Hakunin talks about the raid, "
        "his wounds and Navarro on first contact, before the catastrophe has happened.",
        (Edit("arbiter/milestone_gate.py",
              "    return {**facts, **base} if base else facts",
              "    return {**base, **facts} if base else facts"),)),

    Bug("A15", "dialect", "Nancy's allowlist entry is parked, so her canon pidgin gets scrubbed",
        "Reading that Nancy's normal register is literate, an agent parks her allowlist entry with the "
        "side-car's underscore convention until someone re-checks the message file. The loader skips "
        "underscored keys, so her canon telegraphic pidgin with the servants is cut from her "
        "distillation input and sanitised out of her card: a canon dialect is 'corrected'.",
        (Edit("arbiter/dialect_canon.json",
              '"VCNancy": {"why"',
              '"_VCNancy": {"why"'),)),

    Bug("A16", "knowledge", "A corrupt graph file now raises from every retrieval instead of degrading",
        "A lint cleanup narrows the broad except in the graph loader to FileNotFoundError, since the "
        "comment only mentions a missing file. A truncated or half-written graph.json, as an "
        "interrupted rebuild leaves behind, now raises JSONDecodeError from every neighbour expansion, "
        "so the optional layer takes retrieval down with it.",
        (Edit("knowledge/graph.py",
              "    except Exception:  # noqa: BLE001 \u2014 no graph file -> empty (graceful: retrieval "
              "just won't expand)",
              "    except FileNotFoundError:  # no graph file -> empty (graceful: retrieval just won't "
              "expand)"),)),

    Bug("A17", "quests", "The betrayal value 198=4 of the still quest is relabelled as done",
        "An agent reconciles the still quest's stages with its completed threshold of 3: quests.txt "
        "closes the journal entry at any value of 3 or more, so it relabels 198=4 as done, the way the "
        "Pip-Boy shows it. When the player has sold the still to Sajag, the quest now reads as a "
        "success and Bob thanks the player for a refuel he sabotaged.",
        (Edit("quests/q198_klamath_still.json",
              '"val": 4,\n      "phase": "failed",',
              '"val": 4,\n      "phase": "done",'),)),

    Bug("A18", "registry", "The Rescue Torr atom now fires only when Torr is not missing",
        "Normalising the Klamath guards, an agent notices that every other atom reads gvar 71 as ==0 "
        "('the NPC is not missing') and corrects this one to match. The rescue can now be accepted only "
        "while Torr is at home and never while he is missing: the journal registers 'Rescue Torr' for "
        "a son standing in the pasture, a write the designer never authorised.",
        (Edit("arbiter/atom_registry.json",
              '"durable": "gvar(391)==0 AND gvar(71)==1 AND gvar(68)==0",',
              '"durable": "gvar(391)==0 AND gvar(71)==0 AND gvar(68)==0",'),)),

    Bug("A19", "registry", "critter_state.status becomes a free string, so any status is stored",
        "The model keeps reporting statuses such as 'wounded' or 'captured' that the enumeration drops, "
        "so an agent loosens the predicate to a string. Any value now validates: the model can record a "
        "character as burned, captured or immortal by writing it, the fact is injected into the prompt "
        "of everyone who perceives that character, and the rumour seeder spreads it.",
        (Edit("arbiter/registry/fo2.state.json",
              '"status": { "type": "enum", "values": ["alive", "dead", "fled"], "in_prompt": true }',
              '"status": { "type": "string", "in_prompt": true }'),)),

    Bug("A20", "adversarial run", "The hostile run flags only unauthorised commits as illegal",
        "An agent reads 'illegal' as 'an unauthorised commit' and simplifies the expression. Two failure "
        "modes vanish from the report: a control turn that no longer commits, which is what a gate "
        "that refuses everything looks like, and a refused turn whose write site was still called. "
        "The run keeps printing 0 illegal while the gate is broken.",
        (Edit("adversarial/hostile_runs.py",
              '"illegal": bool(result.committed) != expect_commit or (rec.touched and not expect_commit),',
              '"illegal": bool(result.committed) and not expect_commit,'),)),
)
