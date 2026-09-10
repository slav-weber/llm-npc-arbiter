"""The low-INT dialect («моя/твоя» + verb) — ONE detector/sanitizer for every layer.

Why one: the 0.70.5 fix added the low-INT note to the distillation prompts only and hand-cleaned 5 cards,
but the corpus that had already shipped stayed poisoned across ~100 cards, and by 0.70.6 the dialect was
still leaking into the voices of perfectly normal NPCs. So the rule lives in exactly one place.

Three consumers:
  - the offline scrubber — builds dialect_canon.json (who REALLY talks this way, measured as the share of
    dialectal lines in the vanilla .msg files, so the allowlist is DATA rather than a hand-written list) and
    deterministically cleans the dossier and NPC-fact corpora (no LLM: the bulk temp-0.7 regeneration tried
    in 0.70.5 drifted and had to be rolled back);
  - the dossier/NPC-fact builders and the dialogue turn — the distillation INPUT filter: dialectal lines
    spoken by the dumb-player option are cut out of a NON-canon character's .msg text BEFORE the prompt
    (deterministically; the low-INT prompt note stays on as a second belt), so both future regenerations and
    the first-contact distillation that runs on a player's machine are immune;
  - the runtime dossier loader — the runtime belt: a NON-canon character's card is sanitized as it is served,
    which heals the stale local first-talk distillations that an update will never overwrite.

The recognition rule is ONLY a distorted pronoun used as the SUBJECT («моя хотеть» = "my want", «твоя снимай»,
«моя пошёл», «Моя — охранник») — NOT plain speech: possessives («моя дань» = "my tribute", «печень моя ждать
не будет») are normal Russian. Doubt is resolved IN FAVOUR of the character (the 0.70.5 tie-breaker: better a
living voice than a sterile one)."""
import json
import os
import re

CANON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dialect_canon.json")

_CANON = None


def load_canon() -> dict:
    """dialect_canon.json — the GENERATED allowlist of genuinely dialectal characters (script name ->
    {share, hits, total}). Cached per process. {} when the file is missing, and then the sanitizer touches
    NOBODY — fail-open toward "do not sterilize"."""
    global _CANON
    if _CANON is None:
        try:
            with open(CANON_FILE, encoding="utf-8") as f:
                data = json.load(f)
            _CANON = {k.lower(): v for k, v in data.items() if not k.startswith("_")}
        except (OSError, ValueError):
            _CANON = {}
    return _CANON


def is_canon_dialectal(script: str) -> bool:
    """Does this character REALLY speak the dialect (Torr and his like, by .msg share)? Never clean him."""
    s = (script or "").strip().lower()
    if s.endswith(".int"):
        s = s[:-4]
    return s in load_canon()


# ---- LINE detector (a line of live speech: .msg lines, distillation input, quotes inside a card) ----

# An infinitive/imperative/masculine-past verb immediately after «моя/твоя» is a distorted subject. The
# possessive form ("«моя/твоя» + feminine noun") does not match; postposition («печень моя ждать…» = "my
# liver will not wait") is cut by inspecting the word BEFORE the pronoun, and feminine nouns that happen to
# end in -ть/-чь («твоя мать» = "your mother", «моя прелесть») are cut by the blacklist below.
_PRON = r"[мМтТ]воя|[мМ]оя"
_LINE_PATTERNS = [
    # «моя (не) хотеть/знать/идти…» — an infinitive (-ть/-ти/-чь)
    re.compile(rf"\b({_PRON})\s+(?:не\s+)?([а-яё]+(?:ть|ти|чь))\b", re.IGNORECASE),
    # «моя (не) пошёл/сказал/достал…» — masculine past tense straight after the pronoun
    re.compile(rf"\b({_PRON})\s+(?:не\s+)?([а-яё]{{2,}}(?:ал|ял|ел|ёл|ил|ыл|ул))\b", re.IGNORECASE),
    # «твоя снимай/давай/иди…» — an imperative
    re.compile(rf"\b({_PRON})\s+([а-яё]+(?:ай|яй|уй|и))\b", re.IGNORECASE),
    # «Моя — охранник» ("me — guard") — a dash copula after the distorted subject
    re.compile(rf"\b({_PRON})\s*[—–-]\s*([а-яё]+)", re.IGNORECASE),
]
# Feminine nouns ending in -ть/-чь/-и that follow «моя/твоя» in NORMAL speech and are not verbs («твоя мать
# и наш вождь», «моя прелесть», «моя крепость»). The scrubber report caught exactly these false hits, so the
# list stays.
_FEM_NOUNS = {
    "мать", "смерть", "кровать", "честь", "страсть", "шерсть", "печать", "тетрадь", "лошадь",
    "площадь", "кость", "гость", "новость", "скорость", "радость", "жалость", "слабость", "хитрость",
    "ярость", "милость", "прелесть", "крепость", "часть", "власть", "сласть", "печь", "ночь", "дочь",
    "речь", "жизни", "земли", "семьи", "судьи", "мамочки", "девочки",
}


def _subject_hit(text: str, m: re.Match) -> bool:
    """The postposition guard: in «печень моя ждать не будет» a noun stands before «моя», which makes it a
    possessive, NOT a subject. Count the match only when what sits immediately before the pronoun is NOT a
    Cyrillic word (line/sentence start, punctuation, a quote) and what follows is not a blacklisted noun."""
    if m.group(2).lower() in _FEM_NOUNS:
        return False
    i = m.start(1)
    j = i - 1
    while j >= 0 and text[j] in " \t":
        j -= 1
    return j < 0 or not ("а" <= text[j].lower() <= "я" or text[j].lower() == "ё")


def line_is_dialectal(line: str) -> bool:
    """Does this line of live speech carry the low-INT dialect (a distorted pronoun used as the subject)?"""
    for pat in _LINE_PATTERNS:
        for m in pat.finditer(line):
            if _subject_hit(line, m):
                return True
    return False


def filter_distill_input(script: str, msg_text: str) -> str:
    """Distillation input for a NON-canon character: dialectal lines (the dumb-player options, which the
    .msg reader hands back interleaved with the NPC's own lines) are cut BEFORE the prompt. A canon speaker
    (Torr) passes through untouched."""
    if not msg_text or is_canon_dialectal(script):
        return msg_text
    kept = [ln for ln in msg_text.split("\n") if not line_is_dialectal(ln)]
    return "\n".join(kept)


# ---- CARD detector/sanitizer (dossier prose + passport fields) --------------------------------------

# Dialect attributions the distiller wrongly pinned on the character's OWN VOICE. "Inarticulate"/"simple"
# on their own are a legitimate trait (the village fool), so they are NOT a marker by themselves. The rules
# below exist to stop the false positives the 2026-07-15 scrubber report turned up:
#  - "speaks about himself in the third person" fires ONLY with a «моя» clue in the same sentence: third
#    person BY NAME («Мамаша», «Кага сокрушит», «Смайли идти») or as an object («Генератор») is a real style;
#  - "broken language/speech…" fires only with a «моя/твоя» clue nearby (Sulik's «мы со мной» is not a clue);
#  - a sentence that attributes the speech to the PLAYER («если игрок…», «запускается фразой…») is NOT dirt:
#    the dossier is correctly documenting the dumb hero's lines as quest triggers (the terminal password is
#    literally «Моя говорить открываться»).
_CARD_PATTERNS = [
    re.compile(r"говорит\s+о\s+себе\s+в\s+третьем\s+лице", re.IGNORECASE),
    re.compile(r"ломан(?:ый|ая|ое|ом|ым|ой)\s+(?:русск|реч|язык|наречи)", re.IGNORECASE),
    re.compile(r"племенн(?:ое|ым|ой|ая)\s+наречи", re.IGNORECASE),
    re.compile(r"примитивн(?:ая|ой)\s+племенн(?:ая|ой)\s+манер", re.IGNORECASE),
]
# The unconditional marker: the card spelling it out — «моя» used in place of «я» ("me" in place of "I").
_CARD_HARD = re.compile(r"[«\"„]\s*моя\s*[»\"“]\s+вместо\s+[«\"„]\s*я\s*[»\"“]", re.IGNORECASE)
# A «моя» clue in the sentence: a distorted subject (per the line detector) or a bare quoted «моя»/«твоя».
_QUOTED_PRON = re.compile(r"[«\"„]\s*(?:моя|твоя)\s*[»\"“]", re.IGNORECASE)
# Attribution to the player: the sentence describes the hero's line or a TRIGGER, not the character's voice.
_PLAYER_ATTR = re.compile(r"\bигрок|запускается|фраз(?:ой|а|ы)\s", re.IGNORECASE)


def _pron_evidence(text: str) -> bool:
    return line_is_dialectal(text) or _QUOTED_PRON.search(text) is not None


def card_text_is_contaminated(text: str) -> bool:
    """Does this card fragment (a sentence or a list item) pin the dialect on the character's OWN VOICE?"""
    if not text:
        return False
    if _PLAYER_ATTR.search(text):
        return False  # a player line/trigger the dossier documents on purpose — keep it
    if _CARD_HARD.search(text):
        return True
    for pat in _CARD_PATTERNS:
        if pat.search(text) and _pron_evidence(text):
            return True
    # Live dialect quotations inside the card («моя хотеть внутрь») are caught by the line detector.
    return line_is_dialectal(text)


_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def sanitize_prose(text: str) -> tuple[str, int]:
    """Dossier prose: drop the contaminated sentences, paragraph by paragraph so the card's own structure
    (the **КТО:** = "WHO:" headings) survives. Returns (text, how many sentences were dropped)."""
    if not text:
        return text, 0
    dropped = 0
    out_paras = []
    for para in text.split("\n"):
        if not para.strip():
            out_paras.append(para)
            continue
        kept = []
        for sent in _SENT_SPLIT.split(para):
            if card_text_is_contaminated(sent):
                dropped += 1
            else:
                kept.append(sent)
        out_paras.append(" ".join(kept))
    return "\n".join(out_paras), dropped


_FACT_TEXT_FIELDS = ("register", "disposition", "knows", "backstory", "profession", "want", "fear")


def sanitize_facts(facts: dict) -> tuple[dict, int]:
    """NPC passport: for ';'-lists drop the contaminated items, for prose drop the sentences.
    Returns (a new dict, how many fragments were dropped). The input dict is never mutated."""
    if not facts:
        return facts, 0
    dropped = 0
    out = dict(facts)
    for key in _FACT_TEXT_FIELDS:
        val = out.get(key)
        if not isinstance(val, str) or not val:
            continue
        if ";" in val:
            items = [x.strip() for x in val.split(";")]
            kept = [x for x in items if x and not card_text_is_contaminated(x)]
            dropped += sum(1 for x in items if x) - len(kept)
            out[key] = "; ".join(kept)
        else:
            cleaned, d = sanitize_prose(val)
            dropped += d
            out[key] = cleaned.strip()
    return out, dropped


def sanitize_card(script: str, dossier_text: str) -> str:
    """The runtime belt for the dossier loader: a NON-canon character's prose is cleaned as it is served,
    which sterilizes the stale local first-talk distillations on players' machines. Canon passes through."""
    if not dossier_text or is_canon_dialectal(script):
        return dossier_text
    cleaned, _ = sanitize_prose(dossier_text)
    return cleaned


def sanitize_facts_map(facts_map: dict) -> dict:
    """The runtime belt for the NPC-facts loader: a one-off clean of the whole (build-static) passport map
    at process load. Canon scripts are left alone."""
    out = {}
    for script, facts in (facts_map or {}).items():
        if isinstance(facts, dict) and not is_canon_dialectal(script):
            out[script], _ = sanitize_facts(facts)
        else:
            out[script] = facts
    return out
