"""The strict function-calling tool schemas, one per seam — PURE DATA (2026-06-12).

The caller holds the strict:true required-subset + additionalProperties:false contract; editing a schema
here is a CONTRACT change, so it always flags a re-verify. Lifted verbatim out of the brain module that
used to carry them inline."""

import os

_PROPS = {
    "kind": {"type": "string", "enum": ["valid", "trivial", "impossible", "unclear", "mercy"]},
    "narration": {"type": "string"},
    "check": {"type": "string"},
    "skill_name": {"type": "string"},
    "difficulty": {"type": "integer"},
    "on_crit_success": {"type": "string"},
    "on_success": {"type": "string"},
    "on_failure": {"type": "string"},
    "on_crit_failure": {"type": "string"},
    # Mechanical effects per outcome — compact "key=value;key=value" string; engine applies.
    "fx_crit_success": {"type": "string"},
    "fx_success": {"type": "string"},
    "fx_failure": {"type": "string"},
    "fx_crit_failure": {"type": "string"},
    # Short text listing the situational factors that EASE or WORSEN the check (shown to the player,
    # and folded into `difficulty`). E.g. "темно (-), факел в руке (+), цель ранена (+)". "" if none.
    "modifiers": {"type": "string"},
    # Free-quest completion: id of an active free-quest this action fulfils OR relates to, else 0.
    # Completion counts only if the roll succeeds.
    "completes_quest_id": {"type": "integer"},
    # Smart quests: an INSPECT discovers an object's problem + the logically-matching requirement to
    # fix it; a FIX flags the object as repaired (confirmed on a successful roll).
    "object_problem": {"type": "string"},   # what's wrong with the object (on inspect), or ""
    "object_req": {"type": "string"},        # the item/means needed to fix it (logically matching), or ""
    "object_fixed": {"type": "integer"},     # 1 = this action repairs the object (if the roll succeeds)
    "next_step": {"type": "string"},         # journal line for the related quest (what to do next)
    # One short phrase summarising what the player did, for the persistent Chronicle.
    "essence": {"type": "string"},
    # If the action ADDRESSED an NPC (shout/ask/greet/talk to), the NPC's spoken reply IN CHARACTER — its
    # actual words only (no "он говорит:" / "he says:" wrapper), so the game can VOICE it. Empty otherwise.
    "npc_reply": {"type": "string"},
    # Reachability: "touch" = a hands-on/contact action that needs the player NEXT TO the target (pull a
    # lever, search a box, pick a lock, shove someone); "ranged" = works at a distance (throw, shout,
    # shoot, observe from afar). The ENGINE refuses a "touch" action on an out-of-reach target.
    "reach": {"type": "string", "enum": ["touch", "ranged"]},
    # The chained-action channel: 1 = this is ONE step of the player's larger plan; on a SUCCESS the engine
    # re-asks with a fresh snapshot for the NEXT step (failure breaks the chain). 0/absent = self-contained.
    "continue_action": {"type": "integer"},
    # Ledger: a DURABLE world-state change this action locks in ON A SUCCESSFUL ROLL, as compact validated
    # deltas `domain:subject:predicate=value` (";"-sep). Applied by the bridge ONLY when the engine reports a
    # success tier (faking-proof: illegal slots dropped; save-safe; never numbers/gvars).
    "state_set": {"type": "string"},
    # The atom_id choice channel on the FREE-ACTION seam, mirroring the dialogue precedent in
    # _DIALOGUE_PROPS["atom_id"] below: the stable STRING id of a CURATED deed-atom the model chose to take by
    # THIS free action (from the AVAILABLE-ATOMS list rendered in the prompt). ACCEPT-ONLY on this seam — a
    # go_now/teleport atom is NEVER surfaced here (the action prompt filters to non-terminal), so the model
    # literally cannot pick a teleport by free action. "" = took NO curated atom (decide the action normally).
    # Consumed BRAIN-SIDE only: the free-action router fires it THROUGH THE SAME GATE as dialogue, ending in
    # atom_gate.commit_effect (durable guard + offer-gate). Faking-proof unchanged; the regex floor in
    # atom_arbitration stays as the fallback so this can only ADD fires, never regress.
    "atom_id": {"type": "string"},
}

# atom_id is REQUIRED (strict function-calling -> the model DECLARES its atom choice, or its absence "", on
# EVERY free action) — the same lesson as _DIALOGUE_REQUIRED, which beat the retired optional drive_off field
# that the model simply failed to emit ~92% of the time.
_REQUIRED = ["kind", "narration", "check", "difficulty", "essence",
            "on_crit_success", "on_success", "on_failure", "on_crit_failure", "atom_id"]

_DECIDE_PROPS = {
    "continue_action": {"type": "integer"},  # the chained-action channel (see _PROPS) — the two-call path
    "kind": {"type": "string", "enum": ["valid", "trivial", "impossible", "unclear", "mercy"]},
    "reach": {"type": "string", "enum": ["touch", "ranged"]},
    "check": {"type": "string"},
    "skill_name": {"type": "string"},
    "difficulty": {"type": "integer"},
    "fx_crit_success": {"type": "string"},
    "fx_success": {"type": "string"},
    "fx_failure": {"type": "string"},
    "fx_crit_failure": {"type": "string"},
    "modifiers": {"type": "string"},
    "completes_quest_id": {"type": "integer"},
    "object_problem": {"type": "string"},
    "object_req": {"type": "string"},
    "object_fixed": {"type": "integer"},
    "next_step": {"type": "string"},
    "essence": {"type": "string"},
    # When the action ADDRESSES a person nearby who is NOT the cursor target, the DECIDE leg DECLARES who —
    # the bridge resolves the name against the engine's perceive list ONCE and the narrate leg adopts that
    # identity, so the two legs can no longer pick different people.
    "addressee": {"type": "string"},
    # Ledger: durable world-state delta locked ON SUCCESS (see _PROPS["state_set"]).
    "state_set": {"type": "string"},
    # The atom_id choice channel on the two-call DECIDE leg — same contract as _PROPS["atom_id"] (ACCEPT-ONLY,
    # fired through the gate by the free-action router). Kept in lockstep so the two legs never diverge.
    "atom_id": {"type": "string"},
}

_DECIDE_REQUIRED = ["kind", "reach", "check", "difficulty", "essence", "atom_id"]

_NARRATE_PROPS = {
    "narration": {"type": "string"},   # what the world does/looks like — STRICTLY per the RESULT facts
    "npc_reply": {"type": "string"},   # the addressed NPC's spoken words (for TTS), or ""
    # Whose words these are: the EXACT name from the "who is nearby" list, so the bridge can voice the line
    # in that character's real voice. Empty, or a name not on the list -> the line is not voiced (2026-06-12).
    "speaker": {"type": "string"},
    # Set 1 ONLY when the target object's REAL state (shown in the prompt) confirms a pending
    # quest-deed about it is ALREADY done (object repaired/restored/cleared). The bridge then marks that quest's
    # deed_done. Faking-proof: gated on the engine's real examine state, NEVER on the player's word.
    "object_deed_done": {"type": "integer"},
}

_NARRATE_REQUIRED = ["narration"]

_DIALOGUE_PROPS = {
    "npc_reply": {"type": "string"},
    "option_index": {"type": "integer"},
    # Take this scripted option ON BEHALF of the player to ADVANCE toward their goal when no current option
    # matches it (vanilla hides offers behind branches). The engine runs the real option proc and
    # AUTO-CONTINUES the same player line on the new node (hop-limited). -1 = none.
    "explore_option": {"type": "integer"},
    # The atom_id choice channel: the stable STRING id of a CURATED deed-atom the model chose to take THIS
    # turn (from the AVAILABLE-ATOMS list rendered in the prompt). A SEPARATE channel from option_index — and
    # NOT an index, because option_index is an unbounded dereference inside the engine's dialogue code,
    # guarded only at the turn boundary. "" = took NO curated atom (use option_index / a free reply).
    # Consumed BRAIN-SIDE only:
    # the router fires it THROUGH THE GATE, ending in atom_gate.commit_effect (durable guard + offer-gate +
    # invariants); the atom's effect then reaches the engine as the usual fx (setgvar/exec_proc). Faking-proof
    # unchanged. Precedent: explore_option.
    "atom_id": {"type": "string"},
    # The LLM SELF-REPORTS which quest gvar(s) it ACTUALLY PITCHED in THIS reply (a deed it genuinely PROPOSED
    # to the player — not a greeting/business/chatter line). CSV of gvar ordinals ("102" or "102,390"), "" =
    # pitched nothing. The bridge writes a DURABLE per-NPC `pitched_voiced` flag from it; the quest-SPECIFIC
    # offer-gate for a CONSEQUENTIAL go_now/teleport atom then requires a recorded pitch of THAT quest, so a
    # merely-GREETED NPC can no longer teleport the player on a bare «пошли» ("let's go"). It only RELAXES the
    # gate (it never writes an effect), so it cannot fake a teleport; a MISSED pitch fails CLOSED (the NPC
    # re-asks). "Did I pitch THIS deed" is interpretation, so the LLM owns it — the same doctrine as atom_id.
    # Optional, default "".
    "offered_gvars": {"type": "string"},
    "end": {"type": "integer"},
    # Persuasion: an fx outcome gated by a CONTESTED check. Empty fx = no persuasion.
    "npc_reply_fail": {"type": "string"},
    "fx": {"type": "string"},
    "check": {"type": "string"},
    "vs": {"type": "string"},
    "difficulty": {"type": "integer"},    # situational difficulty 1..10 for the contested check (3 = neutral)
    "promise_kept": {"type": "integer"},  # 1 = the player fulfilled an owed promise THIS turn
    "about_done": {"type": "integer"},    # 1 = this talk RESOLVED a quest whose subject is THIS npc
    "quest_cancel": {"type": "integer"},  # 1 = the player wants to ABANDON a tracked quest from this NPC
    # How the player settles a cancellation when an advance was taken.
    "cancel_settle": {"type": "string"},      # "return" (give the advance back) | "barter" (offer goods) | "keep" (renege)
    "cancel_barter_item": {"type": "string"}, # if barter: the player's item offered instead (exact name)
    # The NPC pays the player an ADVANCE up front for taking a quest (only from what it has — verified by
    # the bridge). caps OR an item.
    "advance_caps": {"type": "number"},
    "advance_item": {"type": "string"},
    "advance_qty": {"type": "number"},
    # A LOAN — you LEND the player caps or an item now (from what you really have), to be RETURNED.
    # The engine hands it over this turn and tracks the debt; the player repays later (promise_kept=1).
    "loan_item": {"type": "string"},   # what you lend ("крышки" for caps), exact name; empty = no loan
    "loan_qty": {"type": "number"},    # how much / how many
    "loan_days": {"type": "number"},   # soft deadline in days (0 = open-ended, you just remember the debt)
    # Conversational trade: the player buys/sells by sentence — with a MERCHANT (mode=trade) OR with
    # ANY ordinary NPC who's WILLING (then it trades dearer; the system handles the markup). Name the item(s)
    # EXACTLY as listed; optional ":N" for quantity, ";" to separate. The SYSTEM executes the transfer at the
    # engine price — never set give/caps/take/pay yourself for a sale.
    "trade_buy": {"type": "string"},   # player buys FROM you (item from YOUR inventory), e.g. "Стимулятор:3"
    "trade_sell": {"type": "string"},  # player sells TO you (item from the player's inventory), e.g. "Нож:2"
    "trade_haggle": {"type": "integer"},  # 1 = the player is haggling THIS turn (system sets the skill-based break)
    # Recruitment mode: set together with recruit=1 (or fx="party_add=1"). "deal" = you AGREED to join
    # because a condition was met (paid, promised something you value, proved themselves) -> you join on the
    # deal, NO persuasion roll. Leave empty/"persuade" for a normal talked-into-it attempt (engine contests it).
    "hire": {"type": "string", "enum": ["persuade", "deal"]},
    # CLEAN decision fields (the system turns these into verified fx -- you set the DECISION, the
    # engine drives + verifies the effect; never hand-write party_add/caps for these).
    "recruit": {"type": "integer"},   # 1 = this NPC joins the player's party (contested unless hire="deal")
    "pay_caps": {"type": "integer"},  # the player pays the NPC this many caps (capped at the player's purse)
    # The player HANDS this NPC a named item THIS turn and the NPC ACCEPTS it — "Пиво:1" (beer, one of).
    # The system verifies against the player's REAL inventory and the engine moves it; never hand-write take=.
    "give_item": {"type": "string"},
    # The MIRROR (added after a 2026-06-18 bug where an NPC narrated a gift nobody received): YOU, the NPC,
    # hand the PLAYER an item from YOUR OWN inventory as a plain gift ("Целебный порошок:1"). System-verified
    # against your REAL holdings; the engine moves it (faking-proof give=). NOT trade/reward/loan/advance —
    # those have their own fields. Raw give= is stripped in dialogue, so this is the ONLY honest NPC-gift
    # channel: never narrate handing something over without it.
    "gift_item": {"type": "string"},
    # YOU give the PLAYER caps from YOUR purse (charity / sharing / gratitude), clamped to your real
    # npc_caps. NOT a quest reward (that pays itself). Raw pay= is stripped in dialogue — use this field.
    "gift_caps": {"type": "integer"},
    # Ledger: a DURABLE world-state change this talk locked in, as compact validated deltas
    # `domain:subject:predicate=value` (";"-separated). The bridge validates each against the registered
    # domains (faking-proof — an illegal slot/value is silently dropped), writes it to the save-safe ledger
    # (NEVER canon gvars / numbers — the engine owns those), and lets the world gossip it. "" = nothing locked.
    "state_set": {"type": "string"},
    # The old `drive_off` boolean was RETIRED: as a separate optional channel the LLM under-emitted it (~92%
    # miss). Make-leave now rides the proven `option_index` channel — each surfaced option is annotated with
    # its grounded ROLE («РОЛЬ: спровадить» = "ROLE: send them away"), so the model returns the make-leave
    # option's index exactly like any quest-accept, and the role-router remains the deterministic floor.
}

# atom_id is REQUIRED (strict function-calling -> the model DECLARES its atom choice, or its absence "", on
# EVERY turn) — the same mandatory-declaration lesson that beat the retired optional drive_off's ~92% miss.
_DIALOGUE_REQUIRED = ["npc_reply", "option_index", "atom_id"]

_DECIDE_DIALOGUE_PROPS = {k: v for k, v in _DIALOGUE_PROPS.items() if k not in ("npc_reply", "npc_reply_fail")}

# The DECIDE leg (two-call, currently dormant) is the OTHER pick leg; require atom_id here too so it stays in
# lockstep if it is ever reactivated — the perception frame must feed EVERY LLM leg, without exception.
_DECIDE_DIALOGUE_REQUIRED = ["option_index", "atom_id"]

_NARRATE_DIALOGUE_PROPS = {"npc_reply": {"type": "string"}}

_NARRATE_DIALOGUE_REQUIRED = ["npc_reply"]

_SUMMARY_PROPS = {
    "name": {"type": "string"},
    "summary": {"type": "string"},
    "facts": {"type": "string"},
    "reaction_delta": {"type": "integer"},
    "travel_dest": {"type": "string"},
    "travel_task": {"type": "string"},    # if the player ORDERED this NPC to go to travel_dest on an
                                          # errand (and the NPC agreed) — short text of the task; else empty
    "promise_what": {"type": "string"},   # the player agreed to do this FOR the NPC (else empty)
    "promise_days": {"type": "number"},   # in-game days until the deadline
    "promise_item": {"type": "string"},   # if it's a DELIVERY promise: item name ("крышки" for caps)
    "promise_qty": {"type": "number"},    # how many to deliver
    # Free-quest layer: when the obligation deserves a quest-log entry.
    "quest_is_canon": {"type": "integer"},  # 1 = this IS one of the NPC's canon scripted quests
    "canon_quest_gvar": {"type": "integer"},  # if canon AND it matches a quest from the canon table -> that quest's gvar (drives the NATIVE Pip-Boy entry); else 0
    "quest_title": {"type": "string"},      # short "who + what" for the quest log
    "quest_desc": {"type": "string"},       # 1 short sentence describing the quest
    "quest_linked": {"type": "string"},     # name of ANOTHER NPC this quest is about (or empty)
    # Kill quest: the NPC asked the player to KILL something. Completed by real combat kills (the engine
    # tracks them by TYPE + REGION), then turned in to the giver like any deed.
    "quest_kill_target": {"type": "string"},  # creature TYPE to kill ("крысы", "когти смерти", "бандиты")
    "quest_kill_count": {"type": "number"},   # how many (1 for a single named foe; a few for "вычистить")
    "quest_kill_region": {"type": "string"},  # WHERE — empty = HERE; a far region only from a merchant/leader
    # The reward the NPC committed for finishing. The bridge VERIFIES it against the NPC's
    # real holdings at turn-in and pays it (no conjured caps). Prefer non-material when the NPC is poor.
    "reward_kind": {"type": "string"},      # material | favour | info | relationship
    "reward_caps": {"type": "number"},      # caps reward (0 if none / non-material)
    "reward_item": {"type": "string"},      # item reward name (exact), or ""
    "reward_qty": {"type": "number"},       # how many of reward_item
    # Quest governance: how prone this NPC is to handing the player tasks (role/character-derived).
    "quest_propensity": {"type": "string"},  # none | low | normal | high
    # NPC autonomy ("mind"): the NPC's personal long-term DRIVE — what it wants, beyond the player.
    # Assigned once from its character; evolves slowly. Makes the NPC feel self-directed + the world live.
    "drive": {"type": "string"},
    # NPC-initiated dialogue: a short in-character hail this NPC would shout to flag the player
    # down next time, reflecting their history/relationship. Cached + exported so the beckon scan uses a
    # PERSONAL line instead of a generic category one (no per-tick LLM). Empty for beasts / nothing notable.
    "beckon_hook": {"type": "string"},
    # EVENT SEED (2026-06-12): a consequence of THIS conversation that ripens LATER — the NPC complains to
    # the elder, tells the neighbours, prepares a gift. On the due day the seed fires through the existing
    # channels (a director beat + a region rumour). RARE by design.
    "seed_what": {"type": "string"},   # what will happen, one short world-voice phrase ("" = no seed)
    "seed_days": {"type": "number"},   # in-game days until it ripens (1-7; 0/empty -> 1)
    # TYPED PRESENCE CLAIMS (root-caused 2026-07-19). The writer declares, ALONGSIDE the prose, any claim it
    # is making about a quest subject being present or absent RIGHT NOW. The gate then compares STRUCTURED
    # claims to STRUCTURED engine verdicts with ZERO Russian NLP — the braces to the prose belt. Prompt text
    # alone provably cannot hold this line: the failing trace had «Спасти Смока … (выполнен)» ("Rescue Smoke …
    # (done)") in its own prompt and still wrote «возможно, Смок снова убежал» ("maybe Smoke ran off again").
    # Optional and additive: an empty/absent array leaves the fold exactly as it is today.
    "claims": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "subject_key": {"type": "string"},   # who/what the claim is about (name as written in the prose)
                "polarity": {"type": "string"},      # present | absent — is it HERE right now, or not
                "kind": {"type": "string"},          # critter | item | npc
            },
        },
    },
}

_SUMMARY_REQUIRED = ["summary"]

_WORLD_BEAT_PROPS = {
    "idx": {"type": "integer"},
    "drive": {"type": "string"},
    "development": {"type": "string"},
    # Nicknames: the world names the player after their deeds — offered ONLY when the prompt supplied
    # player_deeds (and there is no nickname yet) and those deeds add up to a recognizable figure.
    # "" = not yet.
    "player_nickname": {"type": "string"},
    "nickname_reason": {"type": "string"},
}

_WORLD_BEAT_REQUIRED = ["idx", "development"]

# Regional nickname coining (2026-06-20): a separate, light "christen the stranger" call on a DAILY cadence
# rather than on the rare 1-7 day beat. Same fields, both optional: "" = not yet (a nickname is rare).
_COIN_PROPS = {
    "player_nickname": {"type": "string"},
    "nickname_reason": {"type": "string"},
}

_COIN_REQUIRED: list = []

_NPC_STEP_PROPS = {
    "action": {"type": "string", "enum": ["say", "walk", "wait"]},
    "line": {"type": "string"},
    "walk": {"type": "string", "enum": ["wander", "player"]},
}

_NPC_STEP_REQUIRED = ["action"]

# Reflection + planning: an NPC synthesizes its memory-stream into ONE conclusion AND a short intent
# (offline, capped — ONE LLM call per NPC per day folds both).
_REFLECT_PROPS = {
    "belief": {"type": "string"},     # ONE short synthesized conclusion the NPC now holds
    "drive": {"type": "string"},      # its drive, nudged by the belief — keep/evolve, never replaced
    "note": {"type": "string"},       # one-line note for its memory (what it concluded)
    # optional DURABLE world-state the reflection makes certain (validated vs registered domains; faking-proof)
    "state_set": {"type": "string"},
    # PLANNING: a short personal intent the NPC will pursue (goal + 1-3 next steps; ";"-separated steps).
    "plan_goal": {"type": "string"},
    "plan_steps": {"type": "string"},
}

_REFLECT_REQUIRED = ["belief"]

# The NPC passport (2026-06-23): a structural character sheet extracted OFFLINE from an NPC's .msg file into
# the NPC-facts corpus. FLAT schema in the project's house style — string/integer/enum, with lists as a
# ";"-separated STRING rather than a JSON array (strict function-calling was verified on the flat shape, same
# as state_set/fx_*). The CANON fields are filled for ALL NPCs; backstory is synthetic, so the builder keeps
# it ONLY for named characters. The birthday is computed in Python (deterministically), NOT by the model, so
# it is absent from the schema. Age is inferred from the dialogue: the game data does not carry it, because
# an NPC's STAT_AGE is unused by the engine.
_FACTS_PROPS = {
    "age_band": {"type": "string", "enum": ["child", "teen", "young", "adult", "middle", "old", "ancient"]},
    "age_est": {"type": "integer"},        # rough age in years; 0 = impossible to tell (a ghoul is 150-250)
    "race": {"type": "string", "enum": ["human", "ghoul", "supermutant", "robot", "deathclaw", "animal", "other"]},
    "profession": {"type": "string"},      # role/occupation, briefly
    "kin": {"type": "string"},             # family and close ties, "name:relation", ";"-separated
    "knows": {"type": "string"},           # canon facts/lore/places/names this NPC knows, ";"-separated
    "knows_not": {"type": "string"},       # the LIMIT of their knowledge — the cure for an all-knowing NPC
    "register": {"type": "string"},        # manner of speech / what their speech reveals about them
    "disposition": {"type": "string"},     # temperament + starting attitude toward a stranger
    "health": {"type": "string"},          # illnesses/addictions that matter for SAFETY (weak heart), ";"-sep
    "secrets": {"type": "string"},         # what they withhold without trust or a passed check, ";"-separated
    "want": {"type": "string"},            # the core desire (feeds the agents; injected under BRAIN_AGENTS)
    "fear": {"type": "string"},            # what they fear or avoid
    "life_events": {"type": "string"},     # CANON milestones, "age:event", ";"-separated
    "backstory": {"type": "string"},       # synthetic: 3-5 sentences; kept ONLY for named NPCs
}

_FACTS_REQUIRED = ["age_band", "race", "profession"]

# The codex/bestiary: an OFFLINE enrichment of a creature on top of the mechanical critter build. Flat schema;
# the corpus builder sews this into the critter's `desc`, so it reaches the RAG result as `name: desc` with no
# change to retrieval or indexing.
_BESTIARY_PROPS = {
    "danger": {"type": "string"},      # level + what makes it dangerous ("high — claws you up close")
    "behavior": {"type": "string"},    # habits: loner or pack, aggression, how it attacks
    "habitat": {"type": "string"},     # where it lives (terrain / regions of the wasteland)
    "drops": {"type": "string"},       # what you can take — hide/meat/parts, ";"-separated; "" if nothing
    "edible": {"type": "string"},      # is the meat edible: "да"/"нет"/"опасно"/"" (yes/no/dangerous)
    "fight_tip": {"type": "string"},   # how to fight it / what to watch out for
}

_BESTIARY_REQUIRED = ["danger", "behavior"]


# ---- structurally constrain `check` to KNOWN names (flag FO2_CHECK_ENUM, default OFF) --------------------
# Grammar-constrained decoding so the model literally CANNOT emit an out-of-vocabulary check name — the
# residual failure where an unknown name silently rolls a 50% baseline. The enum is built from the SAME
# registry the runtime uses to normalize ru→en, so it NEVER fights normalization: every known ru/en/synonym
# name is allowed, "" / "none" stay valid (no check), and only truly-unknown names are blocked. Default OFF ->
# the plain schema, byte-identical to the baseline.
def _check_enum() -> list:
    """The allowed `check` values: "" / "none" (no check) + every name the check-name registry knows (ru keys,
    en tokens, synonyms). Built lazily from the host (no module-level import -> no cycle). [] if missing."""
    try:
        from core import _SKILL_RU2EN, _STAT_RU2EN
    except Exception:  # noqa: BLE001 — registry not ready -> no enum (degrade to plain schema)
        return []
    vals = {"", "none"}
    for m in (_SKILL_RU2EN, _STAT_RU2EN):
        for k, v in m.items():
            if k:
                vals.add(k)
            if v:
                vals.add(v)
    return sorted(vals)


def apply_check_enum() -> bool:
    """If FO2_CHECK_ENUM is on, constrain every seam's `check` field to _check_enum(). Idempotent (re-sets the
    current enum). Returns True if applied. Off / empty enum -> no-op (plain schema). Called at import + tests."""
    if os.environ.get("FO2_CHECK_ENUM", "").strip().lower() not in ("1", "on", "true", "yes"):
        return False
    ce = _check_enum()
    if not ce:
        return False
    for p in (_PROPS, _DECIDE_PROPS, _DIALOGUE_PROPS, _DECIDE_DIALOGUE_PROPS):
        if "check" in p:
            p["check"] = {"type": "string", "enum": ce}
    return True


apply_check_enum()  # apply at import per the env flag (set FO2_CHECK_ENUM=1 before launch; default = plain)

