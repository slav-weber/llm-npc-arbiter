"""Second blind seeded-bug catalogue: twenty realistic defects plus one canary, written by an agent
that saw only a copy of the source code, data and documentation, without the tests, and that ran
nothing but a checker of its own edits. Exact find->replace edits, each find occurring exactly
once, one import-time canary. Chosen by domain realism and consequence, never tuned to a measured
result.
"""

from __future__ import annotations

from verification.seeded_bugs.records import Bug, Edit

BUGS: tuple[Bug, ...] = (
    Bug("B00", "canary", "Import-time crash in arbiter/atom_gate.py",
        "Not a realistic bug: it proves that the runner applies edits and that the gates see them.",
        (Edit("arbiter/atom_gate.py",
              "_HERE = os.path.dirname(os.path.abspath(__file__))\n",
              "raise RuntimeError(\"seeded canary\")\n"
              "_HERE = os.path.dirname(os.path.abspath(__file__))\n"),),
        canary=True),

    Bug("B01", "gate", "An unresolved invariant name is skipped instead of refusing the commit",
        "Chasing a report that a freshly onboarded atom never fired because its predicate module had "
        "not been imported before the turn, an agent turns the unresolved-name refusal into an audit "
        "line and a skip, so registration order stops breaking live quests. An invariant nobody "
        "registered now evaluates to nothing rather than blocking the write: a typo in a designer's "
        "invariant list, or a name a model appended to it, leaves the atom committing on its guard alone.",
        (Edit("arbiter/atom_gate.py",
              "        fn = _PREDICATES.get(nm)\n"
              "        if fn is None:\n"
              "            return CommitResult(False, f\"unresolved invariant predicate '{nm}' "
              "(no predicate is registered \"\n"
              "                                       f\"under that name)\")\n"
              "        fns.append((nm, fn))",
              "        fn = _PREDICATES.get(nm)\n"
              "        if fn is None:\n"
              "            _audit(f\"ATOM-GATE | invariant '{nm}' resolves to no predicate -> skipped\")\n"
              "            continue\n"
              "        fns.append((nm, fn))"),)),

    Bug("B02", "gate", "A missing party-size scalar now reads as 'the player came alone'",
        "An agent fixing a report that the Navarro sentry refused a player who really had sent his "
        "companions away, because that engine build never emitted the escort scalar, makes the missing "
        "value default to zero so the gate stops punishing absent data. The vanilla rule that recruits "
        "report for duty alone then holds only when the engine happens to report the party, and every "
        "turn without that field passes the gate with a retinue in tow.",
        (Edit("arbiter/atom_gate.py",
              "\"party_size\": {0: (int(party_size) if party_size is not None else 99)}}",
              "\"party_size\": {0: (int(party_size) if party_size is not None else 0)}}"),)),

    Bug("B03", "gate", "A guard clause the evaluator cannot parse is stepped over, not refused",
        "Preparing the guard grammar for terms the engine evaluates itself (the registry's post lists "
        "already carry clauses such as cur_map==14), an agent makes the evaluator tolerant: a clause it "
        "does not recognise is skipped instead of failing the guard. A designer's typo, or a clause "
        "written with OR, is then silently dropped from the guard it was meant to impose, and a guard "
        "built only of such clauses holds against every state the atom is ever offered.",
        (Edit("arbiter/atom_gate.py",
              "        m = _CLAUSE.fullmatch(c)\n"
              "        if not m:\n"
              "            return False                       # don't understand it -> refuse "
              "(false-null > false-fire)",
              "        m = _CLAUSE.fullmatch(c)\n"
              "        if not m:\n"
              "            continue                           # a clause kind this evaluator "
              "cannot parse yet"),)),

    Bug("B04", "loader", "The skills-only exemption becomes a denylist again and forgets stamp_time",
        "Simplifying the loader, an agent replaces the effect-key allowlist with a shorter, more "
        "readable 'no data_delta, no proc, no map or local var' test that looks equivalent. It is not: "
        "a once_per_npc atom whose effect also carries stamp_time, a durable gvar write, or any effect "
        "kind added later, is now exempt from the mandatory durable guard and loads as an active atom "
        "with nothing but memory and intent between a model turn and engine state.",
        (Edit("arbiter/atom_gate.py",
              "    _eff_keys = {k for k in eff if not str(k).startswith(\"_\")}\n"
              "    skills_only_oneshot = bool(a.get(\"once_per_npc\")) and has_skills "
              "and _eff_keys == {\"skills\"}",
              "    skills_only_oneshot = (bool(a.get(\"once_per_npc\")) and has_skills\n"
              "                           and not (has_data or has_proc or has_mapv or has_localv))"),)),

    Bug("B05", "loader", "The design-source check accepts a blank or non-list citation",
        "Tidying the fail-closed schema checks, an agent collapses the design_source test to a plain "
        "truthiness check, reading the list-and-non-blank version as a verbose way of saying the same "
        "thing. A citation of [\"\"], or a bare placeholder string, now counts as design truth, so the "
        "one field that forces a human to name where a guard's intent comes from can be satisfied with "
        "whitespace and the atom loads as cited and active.",
        (Edit("arbiter/atom_gate.py",
              "    src = iv.get(\"design_source\")\n"
              "    if not isinstance(src, list) or not any(str(s).strip() for s in src):",
              "    src = iv.get(\"design_source\")\n"
              "    if not src:"),)),

    Bug("B06", "invariants", "reward_iff_started lets the success flag through on a started quest",
        "An agent reconciling a predicate with its own name rewrites 'the atom must never touch the "
        "success flag' into 'the success flag only once the quest has started'. The escort's go-now "
        "atom legitimately fires at stage 1, so a turn that appends set gvar 85 = 1 to its effect now "
        "passes every check, and the quest's reward is written by a model turn instead of being earned "
        "at the end of the escort.",
        (Edit("arbiter/invariants.py",
              "    # The atom must never touch the success flag — that is the reward, and it is not "
              "the atom's.\n"
              "    r(\"reward_iff_started\", lambda c: _S not in _mut(c))",
              "    # The success flag may be written once the quest is under way, as the name says.\n"
              "    r(\"reward_iff_started\", lambda c: _S not in _mut(c) "
              "or c[\"before\"].get(_Q, 0) >= 1)"),)),

    Bug("B07", "invariants", "The teaching range is widened to the engine's 300-point skill cap",
        "Aligning the numbers that describe train_skill, an agent takes the cap quoted in the "
        "surrounding docstrings — the engine halves a tagged skill and stops at 300 — as the teaching "
        "range and raises the per-lesson bound from 20 to 300. skills_only then accepts a lesson of any "
        "size, so a teacher atom whose amount was inflated to Unarmed:200 is still, by the invariant's "
        "own measure, exactly a skill raise.",
        (Edit("arbiter/invariants.py",
              "        return all(1 <= p <= 20 for _s, p in atom_gate.parse_skill_trains(c[\"atom\"]))",
              "        return all(1 <= p <= 300 for _s, p in atom_gate.parse_skill_trains(c[\"atom\"]))"),)),

    Bug("B08", "ledger", "The mutex pass is dropped from set_fact as dead code",
        "The base state registry declares no mutex groups and the helper ignores two of the arguments "
        "it is given, so an agent pruning dead code removes the call from set_fact. A content mod that "
        "declares predicates mutually exclusive loses the rule that a new fact clears its siblings, and "
        "a subject can hold two contradictory facts at once — repaired and broken, allied and hostile — "
        "both of which are injected into the prompt.",
        (Edit("arbiter/ledger.py",
              "    now = int(now if now is not None else time.time())\n"
              "    _apply_mutex(mem, domain, subject, predicate, now, source)\n"
              "    ledger = mem.setdefault(\"ledger\", {})",
              "    now = int(now if now is not None else time.time())\n"
              "    ledger = mem.setdefault(\"ledger\", {})"),)),

    Bug("B09", "ledger", "Empty source and region make every character perceive every object fact",
        "An agent flattening the perception test drops the 'key and' / 'reg and' guards as redundant "
        "belt-and-braces in front of the comparisons that follow. Both sides default to the empty "
        "string — a fact written without a source or a region, an NPC queried without either — so the "
        "empty strings compare equal and characters start volunteering durable state about objects in "
        "places they have never been.",
        (Edit("arbiter/ledger.py",
              "            or (dom == \"object_state\" and (\n"
              "                (key and str(e.get(\"source\", \"\")).strip() == key)\n"
              "                or (reg and str(e.get(\"region\", \"\")).strip().upper() == reg)))",
              "            or (dom == \"object_state\" and (\n"
              "                str(e.get(\"source\", \"\")).strip() == key\n"
              "                or str(e.get(\"region\", \"\")).strip().upper() == reg))"),)),

    Bug("B10", "dice", "The chance is clamped before the difficulty penalty instead of after",
        "Skills in this game run well past 100, so an agent normalising the character's ability first "
        "moves the clamp onto the base chance and subtracts the difficulty penalty afterwards. The "
        "5..95 window that guarantees room for a miracle and a fumble is gone at the bottom: an "
        "ordinary skill against a hard check lands on a negative chance, where every roll is not merely "
        "a failure but a critical one.",
        (Edit("arbiter/dice.py",
              "    chance = max(5, min(95, base - difficulty_penalty(difficulty)))",
              "    chance = max(5, min(95, base)) - difficulty_penalty(difficulty)"),)),

    Bug("B11", "schemas", "The free-action `kind` field loses its closed set of intents",
        "After turns were thrown away wholesale because the model answered with an intent outside the "
        "five and strict validation rejected the call, an agent relaxes kind to a plain string and "
        "leaves normalisation to the caller. The intent channel stops being a closed vocabulary: the "
        "model can now name a kind nobody designed, and the routing that switches on it meets a value "
        "with no defined meaning.",
        (Edit("arbiter/schemas.py",
              "_PROPS = {\n"
              "    \"kind\": {\"type\": \"string\", \"enum\": [\"valid\", \"trivial\", \"impossible\", "
              "\"unclear\", \"mercy\"]},\n"
              "    \"narration\": {\"type\": \"string\"},",
              "_PROPS = {\n"
              "    \"kind\": {\"type\": \"string\"},\n"
              "    \"narration\": {\"type\": \"string\"},"),)),

    Bug("B12", "result facts", "A registered quest is reported to the narrator as a closed quest",
        "Two adjacent arms of the fact renderer build almost the same sentence about the quest journal, "
        "so an agent deduplicating the branch merges them into one. The narrating model is then told a "
        "quest was closed on the very turn it was merely accepted, which is the completion claim every "
        "quest record forbids the brain from making before the engine flips the done variable.",
        (Edit("arbiter/result_facts.py",
              "        elif key == \"quest_closed\":\n"
              "            lines.append(f\"Квест закрыт ({val}).\")\n"
              "        elif key == \"quest_registered\":\n"
              "            # The quest is NOW tracked in the Pip-Boy as of this turn, so the narrator "
              "may confirm it\n"
              "            # was accepted.\n"
              "            lines.append(\"Задание ЗАРЕГИСТРИРОВАНО — теперь оно в Пип-бое "
              "(отслеживается).\")",
              "        elif key in (\"quest_closed\", \"quest_registered\"):\n"
              "            # One line for both journal events — the quest reached the Pip-Boy either "
              "way.\n"
              "            lines.append(f\"Квест закрыт ({val}).\")"),)),

    Bug("B13", "arbitration", "The make-leave short-circuit is deleted from the atom intent classifier",
        "The module says the primary make-leave route is the role-annotated option index, so an agent "
        "retiring the regex floor deletes the short-circuit that made a send-them-away line neither an "
        "accept nor a go. A player telling Torr to clear off in a sentence that happens to carry a "
        "go-word («сваливай, пошли уже») classifies as go_now again and fires the pasture teleport — "
        "the spurious re-teleport the comment right above it records.",
        (Edit("arbiter/atom_arbitration.py",
              "    if _is_make_leave(p):\n"
              "        return None\n"
              "    if _GO_INTENT_RE.search(p) and not re.search(",
              "    if _GO_INTENT_RE.search(p) and not re.search("),)),

    Bug("B14", "milestones", "The pre-catastrophe baseline no longer overrides the contaminated facts",
        "An agent fixing what reads like a precedence mistake — a generic side-car overwriting a "
        "character's own curated fields — puts the NPC's facts last in the merge. Every field the "
        "baseline exists to replace wins again, so on first contact, long before the raid happens, the "
        "shaman speaks of Navarro, the burned village and his own dying: exactly the bug the milestone "
        "gate was built to stop.",
        (Edit("arbiter/milestone_gate.py",
              "    return {**facts, **base} if base else facts",
              "    return {**base, **facts} if base else facts"),)),

    Bug("B15", "dialect", "The runtime card belt sanitises the canon dialect speakers too",
        "Reasoning that a dossier card is the distiller's prose about a character and never the "
        "character's own lines, an agent removes the canon exemption from the runtime belt so stale "
        "cards on players' machines are cleaned for everyone. The cards of the characters whose broken "
        "speech is canon lose every sentence that describes it, and the model voices Torr and his like "
        "as ordinary, articulate people.",
        (Edit("arbiter/dialect_guard.py",
              "    if not dossier_text or is_canon_dialectal(script):\n"
              "        return dossier_text",
              "    if not dossier_text:\n"
              "        return dossier_text"),)),

    Bug("B16", "knowledge", "Runtime name resolution falls back to any node sharing a prefix",
        "Mirroring the build's prefix matching, an agent makes the runtime resolver accept an inflected "
        "or shortened entity name by falling back to the first graph key that starts with it. A name "
        "that is a prefix of a longer one — and an empty name, which is a prefix of everything — then "
        "borrows a stranger's neighbourhood, so the lines injected into a character's prompt as related "
        "facts belong to an entity the retrieval never matched.",
        (Edit("knowledge/graph.py",
              "    return {k.lower(): k for k in adj}.get(str(name or \"\").lower())",
              "    lowered = {k.lower(): k for k in adj}\n"
              "    key = str(name or \"\").lower()\n"
              "    return lowered.get(key) or next((v for k, v in lowered.items() "
              "if k.startswith(key)), None)"),)),

    Bug("B17", "quests", "The dog's strict alias list is completed with the second name's forms",
        "The deliverable record says Smoke answers to both «Смок» and «Дым», so an agent completing the "
        "strict list adds the second name's inflections for symmetry. That list is the match set for a "
        "memory deletion that runs outside the quest's owning character, and «Дым» is also the ordinary "
        "Russian word for smoke, so unrelated true memories — a campfire that smells of smoke — are "
        "erased for good from every character that holds them.",
        (Edit("quests/arroyo_nagor_dog.json",
              "    \"strict_aliases\": [\"Смок\", \"Смока\", \"Смоку\", \"Смоком\", \"Смоке\"],",
              "    \"strict_aliases\": [\"Смок\", \"Смока\", \"Смоку\", \"Смоком\", \"Смоке\",\n"
              "                       \"Дым\", \"Дыма\", \"Дыму\", \"Дымом\", \"Дыме\"],"),)),

    Bug("B18", "registry", "The Rescue Torr guard is 'normalised' to read Torr as not missing",
        "Sweeping the registry for inconsistencies, an agent finds one guard reading the Torr-missing "
        "flag as gvar(71)==1 where every neighbouring atom reads gvar(71)==0, and makes it match its "
        "siblings. The atom now registers the rescue quest in the journal only while Torr is safely at "
        "home, and refuses it in the one state the designer wrote the quest for, so the mother's errand "
        "can never be accepted when her son is actually gone.",
        (Edit("arbiter/atom_registry.json",
              "      \"durable\": \"gvar(391)==0 AND gvar(71)==1 AND gvar(68)==0\",",
              "      \"durable\": \"gvar(391)==0 AND gvar(71)==0 AND gvar(68)==0\","),)),

    Bug("B19", "registry", "critter_state.status is widened from an enumeration to free text",
        "After watching legitimate-looking deltas dropped because the model wrote statuses the registry "
        "does not declare, an agent changes the predicate's type from enum to string so content stops "
        "being lost. The validated slot stops validating: any status a model invents for any creature "
        "is stored with provenance, injected into the prompts of everyone who would perceive it, and "
        "spread by the rumour seeder as durable truth about the world.",
        (Edit("arbiter/registry/fo2.state.json",
              "        \"status\": { \"type\": \"enum\", \"values\": [\"alive\", \"dead\", \"fled\"], "
              "\"in_prompt\": true }",
              "        \"status\": { \"type\": \"string\", \"in_prompt\": true }"),)),

    Bug("B20", "adversarial run", "A missing atom becomes an empty stand-in instead of aborting the run",
        "An agent makes the hostile run survive registry edits: a scenario whose atom is no longer in "
        "the live whitelist gets an empty stand-in, which the gate refuses as inert, rather than the "
        "whole run dying on a KeyError. An atom the loader has quietly started rejecting then leaves "
        "its attacks 'refused' for the wrong reason, and the table and the exit code report a clean run "
        "over checks that were never exercised at all.",
        (Edit("adversarial/hostile_runs.py",
              "    atom = atoms.get(atom_id)\n"
              "    if atom is None:\n"
              "        raise KeyError(f\"the registry has no atom {atom_id!r}; adjust the scenario, "
              "not the gate\")\n"
              "    return atom",
              "    # A scenario whose atom is no longer in the live whitelist runs against an empty\n"
              "    # stand-in, which the gate refuses as inert, instead of aborting the whole run.\n"
              "    return atoms.get(atom_id) or {}"),)),
)
