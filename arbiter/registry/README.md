# registry — the open extension registry

This is where a content mod drops its data to extend the AI layer **without editing the core**. The core
loads EVERY matching file (the FO2 base plus any mod files) and merges them.

## Check names — `*.checks.json`
The check-name normalizer loads every `registry/*.checks.json` (the `fo2.checks.json` base plus mods). That
is how a Russian or synonym check name is mapped onto the canonical engine token — without the mapping the
name silently falls through to a 50% baseline roll, which was a real bug. Format:

```json
{
  "skills": { "ваше имя проверки": "Speech", "ещё одно": "Sneak" },
  "stats":  { "ваш стат": "STR" }
}
```
The keys are the Russian names the player and the model actually use (`"ваше имя проверки"` = "your check
name"); the values are the canonical engine tokens.

- `skills` → the engine's skill tokens (`Small Guns`, `Sneak`, `Speech`, `Lockpick`, …).
- `stats`  → the SPECIAL abbreviations (`STR PER END CHA INT AGI LCK`).
- Keys are matched lowercased. On a key collision the mod file overrides the base.
- A broken or missing file does NOT break the base (graceful degrade; the core also carries a hardcoded
  fallback).

To ship your own mod: put `mymod.checks.json` next to `fo2.checks.json`.

## Structured world state — `*.state.json`
The GM writes VALIDATED state deltas into `mem['ledger']` (inside world_memory, so it is save-safe; canon
gvars are NEVER touched). `ledger.py` loads every `registry/*.state.json` (the `fo2.state.json` base plus
mods), which is how a content mod adds ITS OWN state domain (a faction's stance, an object's condition, …)
without editing the core. Format:

```json
{ "domains": {
  "<domain>": {
    "subject_kind": "faction|object|critter|…",
    "predicates": {
      "<predicate>": { "type": "enum|string|number", "values": ["..."], "in_prompt": true }
    },
    "mutex": [ ["predicateA", "predicateB"] ]
  }
}}
```
- `type=enum` → the value MUST be in `values`, otherwise the delta is REFUSED (faking-proof).
- `in_prompt:true` → the fact is injected into the model's context (perceptually — what the NPC could know).
- `mutex` → a subject holds only ONE predicate from the group (a new one clears its siblings).
- A slot is single-valued: a new delta SUPERSEDES the old one and records it in the history (provenance).
  A conflict means an invalid delta.

## Reserved (separate steps, NOT a registry yet):
- **fx verbs** — they currently live in the engine's fx table plus the prompt text; moving them into the
  registry spans C++ and the prompt at once, so it is its own task.
- **canon quest gvars** — already data-driven from the game's own quest table.
- **a schema enum for checks on the wire** — structurally forbid out-of-vocabulary names in the model's
  output; needs the prompt and the live check coordinated (a separate step).
