"""LEDGER — structured, validated, save-safe world state. A fact is a single-valued slot
`domain:subject:predicate -> value` carrying provenance plus a supersede history. The GM writes DELTAS
(state_set) that are validated against a REGISTERED domain (registry/*.state.json):
  - faking-proof: you cannot assert outside a registered slot/type (an illegal delta is refused, like bad fx);
  - save-safe: it lives in mem['ledger'] inside world_memory (the game's .SAV is never touched, invariant #1);
  - canon stays intact: the ledger writes ONLY mem['ledger'], NEVER a canon gvar (canon is its own authority);
  - moddable: domains are an open registry (a mod drops in its own *.state.json), like the checks registry.
It consolidates the earlier scattered half-layers (objects/... and friends) into one queryable, consistent
layer.
"""
from __future__ import annotations

import glob
import json
import os
import time

_REGISTRY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry")
_domains_cache = None


def enabled() -> bool:
    """Flag for the WIRING (GM emits state_set + the apply/seed stage). Default ON; `BRAIN_LEDGER=0`
    disables cleanly (the standing project rule: new behaviour behind a flag, instant revert). The CORE
    store (set_fact/facts_for) is always available — only the live emit/apply path is gated."""
    return os.getenv("BRAIN_LEDGER", "1").strip().lower() not in ("0", "off", "false", "no")


def _load_domains() -> dict:
    """Domains from registry/*.state.json (the fo2 base plus mod files; a mod overrides by name). Cached."""
    global _domains_cache
    if _domains_cache is not None:
        return _domains_cache
    domains: dict = {}
    for path in sorted(glob.glob(os.path.join(_REGISTRY_DIR, "*.state.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for name, spec in (data.get("domains") or {}).items():
                if name and isinstance(spec, dict):
                    domains[name] = spec
        except (OSError, ValueError, TypeError):
            continue  # a broken mod registry must never take the base registry down with it
    _domains_cache = domains
    return domains


def reload_domains() -> dict:
    """Drop the domain cache (for tests, and for hot-loading a mod)."""
    global _domains_cache
    _domains_cache = None
    return _load_domains()


def _slot(domain: str, subject, predicate: str) -> str:
    return f"{domain}:{str(subject).strip().lower()}:{predicate}"


def validate(domain: str, predicate: str, value) -> tuple[bool, str]:
    """Is the delta legal: domain and predicate registered AND the value fits the type/enum. (ok, reason).

    The reason strings below are returned values on this runtime's Russian-language surface, not commentary,
    so they stay in Russian."""
    spec = _load_domains().get(domain)
    if not spec:
        return False, f"домен {domain!r} не зарегистрирован"
    p = (spec.get("predicates") or {}).get(predicate)
    if not p:
        return False, f"предикат {predicate!r} не в домене {domain!r}"
    t = p.get("type", "string")
    if t == "enum" and str(value) not in (p.get("values") or []):
        return False, f"значение {value!r} вне enum {p.get('values')}"
    if t == "number":
        try:
            float(value)
        except (TypeError, ValueError):
            return False, f"значение {value!r} не число"
    return True, ""


def _apply_mutex(mem: dict, domain: str, subject, predicate: str, now: int, source: str) -> None:
    """When the domain declares mutex groups, a delta on one predicate CLEARS the sibling predicates of the
    same subject (a subject cannot hold two mutually exclusive facts). What is cleared leaves as a mutex
    transition."""
    spec = _load_domains().get(domain) or {}
    ledger = mem.setdefault("ledger", {})
    for group in (spec.get("mutex") or []):
        if predicate in group:
            for sib in group:
                if sib != predicate:
                    k = _slot(domain, subject, sib)
                    if k in ledger:
                        del ledger[k]


def set_fact(mem: dict, domain: str, subject, predicate: str, value,
             source: str = "", reason: str = "", now=None, region: str = "") -> tuple[bool, str]:
    """Apply a GM delta. Validates against the registry; on success SUPERSEDES the slot (the old value goes
    to the history) with provenance. (ok, reason). Faking-proof: an illegal delta is refused, like a bad fx.
    Writes ONLY mem['ledger'] — never a canon gvar. `region` is where the event happened, which drives
    perception: the whole neighbourhood knows about its own well."""
    ok, why = validate(domain, predicate, value)
    if not ok:
        return False, why
    now = int(now if now is not None else time.time())
    _apply_mutex(mem, domain, subject, predicate, now, source)
    ledger = mem.setdefault("ledger", {})
    key = _slot(domain, subject, predicate)
    prev = ledger.get(key)
    history = list((prev or {}).get("history", []))
    if prev and prev.get("value") != value:
        history = (history + [{"value": prev.get("value"), "until": now, "source": prev.get("source", "")}])[-5:]
    ledger[key] = {"domain": domain, "subject": str(subject), "predicate": predicate, "value": value,
                   "since": now, "source": str(source)[:60], "reason": str(reason)[:120],
                   "region": str(region or "").strip().upper(), "history": history}
    return True, ""


def get_fact(mem: dict, domain: str, subject, predicate: str):
    """The slot's current value, or None."""
    return (mem.get("ledger", {}) or {}).get(_slot(domain, subject, predicate), {}).get("value")


def facts_for(mem: dict, subject=None, in_prompt_only: bool = True) -> list:
    """The relevant facts (for injection into the prompt): by subject, optionally only in_prompt predicates.
    Returns [{domain, subject, predicate, value, reason}]."""
    doms = _load_domains()
    out = []
    for e in (mem.get("ledger", {}) or {}).values():
        if subject is not None and str(e.get("subject", "")).strip().lower() != str(subject).strip().lower():
            continue
        if in_prompt_only:
            p = ((doms.get(e.get("domain")) or {}).get("predicates") or {}).get(e.get("predicate")) or {}
            if not p.get("in_prompt"):
                continue
        out.append({k: e.get(k) for k in ("domain", "subject", "predicate", "value", "reason")})
    return out


def prompt_lines(facts: list) -> list:
    """Facts -> the short context lines the prompt carries."""
    return [f"{f['subject']}: {f['predicate']} = {f['value']}"
            + (f" ({f['reason']})" if f.get("reason") else "") for f in facts]


def facts_for_npc(mem: dict, npc_name: str, npc_key: str = "", npc_region: str = "", limit: int = 6) -> list:
    """Prompt-ready DURABLE-state lines this NPC would PERCEIVE (the dialogue ctx injection):
      1) every faction_stance toward the player (any NPC senses the factional weather);
      2) any in_prompt fact whose subject is THIS NPC by name;
      3) added 2026-06-20: durable object_state this NPC PERCEIVES — locked in HIS context (source==his key)
         OR in HIS region (the whole neighbourhood knows their own well was repaired). This closes the hole
         where state was siloed away from the very NPC it concerns: the well's subject is 'Arroyo_well', yet
         Fergus, who had been fretting over it, could not see it.
    Short lines (prompt_lines), capped. [] when nothing relevant is locked."""
    nm = str(npc_name or "").strip().lower()
    key = str(npc_key or "").strip()
    reg = str(npc_region or "").strip().upper()
    doms = _load_domains()
    rel = []
    for e in (mem.get("ledger", {}) or {}).values():
        dom = e.get("domain")
        p = ((doms.get(dom) or {}).get("predicates") or {}).get(e.get("predicate")) or {}
        if not p.get("in_prompt"):
            continue
        subj = str(e.get("subject", "")).strip().lower()
        perceives = (
            dom == "faction_stance"
            or subj == nm
            or (dom == "object_state" and (
                (key and str(e.get("source", "")).strip() == key)
                or (reg and str(e.get("region", "")).strip().upper() == reg)))
        )
        if perceives:
            rel.append({k: e.get(k) for k in ("domain", "subject", "predicate", "value", "reason")})
    return prompt_lines(rel)[:limit]


def apply_state_set(mem: dict, s: str, source: str = "", reason: str = "", now=None, region: str = "") -> list:
    """Parse the compact state_set `domain:subject:predicate=value` (';'-separated), apply EVERY valid delta
    through set_fact, and return the list of APPLIED deltas [{domain,subject,predicate,value}] (used to seed
    rumours). Invalid ones are refused silently (faking-proof). The format is forgiving: junk and incomplete
    tokens are skipped. `region` is where the change happened, which drives perception: the whole
    neighbourhood perceives its own object_state."""
    applied = []
    for tok in str(s or "").split(";"):
        tok = tok.strip()
        if not tok or "=" not in tok:
            continue
        left, value = tok.split("=", 1)
        parts = left.split(":")
        if len(parts) != 3:
            continue
        domain, subject, predicate = (p.strip() for p in parts)
        ok, _why = set_fact(mem, domain, subject, predicate, value.strip(),
                            source=source, reason=reason, now=now, region=region)
        if ok:
            applied.append({"domain": domain, "subject": subject, "predicate": predicate, "value": value.strip()})
    return applied


def delta_rumor(delta: dict) -> str:
    """A short rumour phrase built from an applied delta (for the rumour seeder) — this is how the world
    spreads a state change. The phrases are Russian because they are game-facing text, not commentary."""
    d, s, p, v = delta.get("domain"), delta.get("subject"), delta.get("predicate"), delta.get("value")
    if d == "faction_stance" and p == "stance_to_player":
        return f"{s} теперь настроена {v} к чужаку"
    if d == "critter_state" and p == "status":
        return f"{s} теперь {v}"
    if d == "object_state":
        return f"про {s}: {p} = {v}"
    return f"{s}: {p} = {v}"
