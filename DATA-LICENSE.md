# Data, sources and attribution

The code in this repository is mine and is licensed under `LICENSE.md`. The data is a different
question, and this file answers it honestly, file by file.

## What is here

| Path | What it is | Where it comes from |
|---|---|---|
| `knowledge/world.json` | A structured corpus of 882 entities: items with their statistics, creatures, locations, quests, lore | Extracted from the game's own files by the mod's corpus builder, running against the author's own legally purchased copy of the game |
| `knowledge/lore_seed.json`, `knowledge/fo1_seed.json`, `knowledge/bible_seed.json` | Curated lore entries used to ground the characters | Hand-authored from established canon, drawing on the Fallout wiki (`fallout.fandom.com`, CC BY-SA) and the Fallout Bible, a developer-canon document. Each file records its own `_source` |
| `knowledge/bestiary.json` | Creature descriptions with behaviour and danger notes | Hand-authored for the mod |
| `arbiter/atom_registry.json`, `arbiter/registry/*.json`, `arbiter/milestone_gates.json`, `arbiter/dialect_canon.json` | The whitelist of write effects, the state-domain registry, gates and the dialect allowlist | Authored by me. They reference the game's variable indices and script names, because that is what they guard |
| `quests/*.json` | Quest specifications: variables, stages, thresholds, characters, and the provenance of every number | Authored by me |
| `knowledge/graph.json`, `docs/knowledge-graph.html`, `docs/knowledge-graph.png` | The co-reference graph and its rendering | Derived from the corpus by the scripts in `knowledge/` |

## What is deliberately absent

The game engine, the fork of the open-source engine reimplementation the mod runs on, the game's
data archives, its executables, its audio, its dialogue message files, the mod's prompt corpus, its
voice models, and every recording, transcript or trace of a real play session. None of that is in
this repository and none of it should be added to it.

## The game

*Fallout 2* and its setting are the property of their rights holders. This repository is not
affiliated with, endorsed by or connected to them. It contains no game code and no game assets: the
corpus here is a derived, structured extract of descriptive text and statistics, included because
the graph and the retrieval layer cannot be read or verified without a corpus to run them against.
Anyone building on this is expected to regenerate their own corpus from their own copy of the game
with the builder in `knowledge/`; that is how the mod itself works.

If a rights holder objects to the extract shipped here, remove `knowledge/world.json` and rebuild it
locally: nothing else in the repository depends on it being committed.

## Wiki-derived lore

Entries drawn from `fallout.fandom.com` are used under CC BY-SA. The `_source` field in each seed
file names the source; this notice is the attribution, and derivative distribution of those entries
carries the same licence.
