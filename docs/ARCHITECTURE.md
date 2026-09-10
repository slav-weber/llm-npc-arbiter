# Architecture

The system this layer comes from puts a language model in charge of every character in a role-playing
game: what they say, what they want, and what they claim is happening. The game is a 1998 title whose
state lives in a save file full of numbered variables, and whose rules were written by designers a
quarter of a century before anyone thought of asking a model to improvise inside them.

That combination has one obvious failure mode. If the model's text is treated as truth, a player who
writes convincingly enough is handed the game: items appear, money appears, quests complete
themselves, and the world stops meaning anything. The whole architecture is an answer to that.

## The contract

Two processes, one rule between them.

```
player types free-form text
        │
        ▼
[decision layer, Python]   the model returns: intent · prose · effect tokens · a check to roll
        │                  the tokens come from a closed vocabulary; the schema forbids the rest
        ▼
[the gate]                 guard on the pre-state → invariants → ONE write site → post-assert
        │
        ▼
[game engine, C++]         rolls the check with its own mathematics, applies the effects it
        │                  recognises, ignores anything it does not, reports what happened
        ▼
[narration]                the model describes the outcome from a closed vocabulary of facts
```

The model decides *intent*. The engine decides *outcome*. Neither of those is a rhetorical
distinction: the model never sees a code path that writes to the save file, and the narrating call
never sees anything except a list of facts the engine has already made true.

This repository contains the middle box and the pieces around it. The engine, the bridge and the
prompt construction are not here.

## 1. The closed vocabulary

The model's response is a strict function call. Its fields are an intent from a fixed set
(`valid`, `trivial`, `impossible`, `unclear`, `mercy`), the prose, an optional check to roll, and up
to four effect slots — one per outcome grade, because the effect of a critical success is not the
effect of a failure. `arbiter/schemas.py` holds those schemas, with `additionalProperties: false`
throughout, so the response cannot carry a field nobody designed.

The effects themselves are tokens like `item`, `caps`, `hp`, `skill_on`, `party_add`, joined by
semicolons. The vocabulary is closed on both sides: the prompt lists it, and the engine has a table
of handlers with one row per token. A token the engine does not know is a silent no-op — the model
can write it, and nothing happens. One of the tests in the original suite parses the engine's own
table and asserts the prompt's vocabulary is a subset of it, so the two cannot drift apart unnoticed.

Optionally the check name can be constrained by grammar during decoding, so an out-of-vocabulary
skill name is not merely normalised later but impossible to emit.

## 2. The gate

`arbiter/atom_gate.py`. Some effects are too consequential to be a token: accepting a quest,
teleporting the player to a scene, passing a guarded gate, a teacher raising a skill. Those are
**write atoms** — designer-authored rows in `arbiter/atom_registry.json`, each with:

- a **scope**: which character's script it binds to, and which scene it belongs to;
- an **intent**: `accept`, `go_now`, `gate_pass` or `train` — the routing key;
- a **guard**: a boolean expression over engine state, such as
  `gvar(182)==0 AND gvar(70)==0 AND gvar(203)==0`, meaning the quest has not started, the escorted
  character is alive, and the town is not hostile;
- an **effect**: the variable writes, the engine procedure to call, the skills to raise;
- a list of **invariants** by name;
- an **intent verification** block with a mandatory citation of the design source.

The model does not author an atom. It names one. `commit_effect` is then the only path to a durable
change, and it runs in a fixed order:

1. Compute the effect. An empty effect is a refusal, not a no-op success.
2. Evaluate the guard against the state *before* the turn.
3. Resolve every declared invariant to a registered predicate. **An unknown name is a refusal**, so
   an atom cannot ship with a safety rule that silently evaluates to nothing.
4. Evaluate every predicate on the pre-state.
5. Apply — once, through an injected callable, which is the single write site. Tests pass a recorder;
   the runtime passes the engine bridge.
6. For effects that call an engine procedure, re-assert every invariant on the *post*-state. A
   violation escalates and halts further commits.

Steps 1 to 4 all mean the same thing when they fail: the write site is never called. There is no
partial write and no rollback, because there is nothing to roll back.

**Fail closed, loudly.** The loader rejects any atom missing its invariants, its intent verification
or a non-empty design source, and says so on stderr and in the debug log. That rule exists because
the opposite once nearly happened: a plausible-looking safety invariant, written from what the code
did rather than from what the designer intended, would have deleted content the designer meant to
ship. Code-truth without design-truth is how a guard becomes a bug.

**Why the guard is repeated as an invariant.** `guard_consistent` re-evaluates the atom's full
durable guard from inside the invariant list. It is deliberate duplication: it means every variable
the designer named is enforced twice, by two different mechanisms, and a future refactor of the
firing path cannot quietly bypass one of them.

**Why a teacher atom has `skills_only`.** A teaching atom's other invariants
(`monotonic`, `idempotent_from_zero`, `guard_consistent`) are trivially satisfied when the effect is
just a skill raise, so its invariant list would be decoration. `skills_only` asserts the effect is
*exactly* a skill raise — no quest variable, no procedure, no map or local variable, no timestamp —
and that each amount is within the teaching range. It is the difference between an atom that declares
invariants and an atom that has them.

## 3. The state ledger

`arbiter/ledger.py`. Not everything worth remembering is a variable the 1998 designers thought to
create. A faction's stance toward the player, the state of an object the player broke or fixed — the
model can legitimately influence these, so they need a place to live that is neither the model's
imagination nor the game's canonical variables.

The ledger is that place: facts of the form `domain:subject:predicate=value`, written into the mod's
own memory file, never into canonical game variables. Every write is validated against an open
registry (`arbiter/registry/*.state.json`) that declares each domain's predicates, their types and,
for enumerations, their permitted values. A domain, predicate or value that is not declared is
dropped. Predicates can be declared mutually exclusive, so setting one clears its siblings rather
than leaving the world holding two contradictory beliefs. Facts carry provenance and a timestamp and
supersede rather than overwrite, so the history of a fact survives.

A content mod adds a domain by dropping a file into the registry. It does not add code.

## 4. The graded check

`arbiter/dice.py`. When an action needs a check, the model proposes *which* check; the engine rolls
it. The base chance comes from the character's own statistics, a difficulty of 1 to 10 subtracts up
to 90 points, the result is clamped to 5..95 so nothing is ever certain in either direction, and one
hundred-sided roll produces four grades: critical success, success, failure, critical failure, with
the criticals decided by a fixed margin. The atom or the effect slots then decide what each grade
does.

The model narrates the grade it is given. It does not choose it, and it cannot see it before it is
rolled.

## 5. The closed fact vocabulary

`arbiter/result_facts.py`. After the engine has applied the effects, the narrating call is given a
list of facts — `tier`, `item_gained`, `caps_lost`, `target_hp`, `dead`, `mercy`, and a few more —
and nothing else. The prose is therefore constrained to describe what happened, and the second model
call cannot smuggle a new consequence into the story by describing it confidently.

## 6. Knowledge

`knowledge/`. Characters must know their world without the model's half-remembered training data
leaking into it. The corpus is built from the game's own files: item descriptions and hard statistics
from the binaries, location and quest text from the message files, curated lore from seed files. That
gives 882 entities that are true by construction.

Over that corpus, `knowledge/build_graph.py` links entities that name one another in their descriptions —
deterministic, offline, prefix-matched so inflected forms still resolve, alias-aware. At runtime
`knowledge/graph.py` expands a retrieval with a query entity's neighbours: the facts a knowledgeable character
would connect, which pure vector similarity misses. It is flag-gated and degrades to a no-op when the
graph file is absent, because an optional layer must never be able to break retrieval.

`knowledge/build_graph_map.py` renders the whole thing as a self-contained page for humans.

## 7. Two smaller guards

`arbiter/milestone_gate.py` keeps one-shot events one-shot, from a side-car table rather than from
code. `arbiter/dialect_guard.py` is an allowlist of characters whose broken, dialectal speech is
canon from their own original lines, so the text-cleaning pass does not politely correct a character
into someone else.

## The invariants, stated once

1. The model names things; it never authors an effect.
2. Nothing durable changes except through `commit_effect`, and only after the guard and every
   declared invariant pass on the pre-state.
3. An unresolved invariant, a malformed atom or a missing design source is a refusal, and it is loud.
4. What cannot be prevented is detected: post-assert, escalate, halt.
5. The engine decides outcomes; the model describes them from a closed vocabulary of facts.
6. Every rule records the failure that produced it.
