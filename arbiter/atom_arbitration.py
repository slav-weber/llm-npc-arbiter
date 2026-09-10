"""The ATOM-ARBITRATION vetoes, extracted verbatim from the dialogue-guard module so they can OUTLIVE the
regex FLOOR. The doctrine is determinism-for-ARBITRATION, LLM-for-INTERPRETATION. These deterministic
predicates are NOT floor classifiers on their way out — they are PERMANENT vetoes on the atom_id BYPASS path,
where the LLM names an atom by id and skips the regex floor, so a consequential fire always needs a
corroborating deterministic key:
  - go-SAFETY: a go_now/teleport atom_id needs a real go-word (_GO_INTENT_RE via _dialogue_atom_intent), or it
    demotes to the accept atom. This kills the warm «да, помогу» ("yes, I'll help") -> teleport mis-pick.
  - WORKSEEK-veto: a bare generic job-seek (_GENERIC_WORKSEEK_RE ∧ NOT _acceptance_intent ∧ NOT a go-word)
    never auto-accepts a specific deed — the live «ищу работу» ("I'm looking for work") bug.
  - shout-to-accept: the free-action ACCEPT hook reuses _dialogue_atom_intent — the SAME arbitration.
So the "safe-to-delete" set for these is EMPTY; only the floor's own FIRE path is a later, recall-gated trim.
The dialogue-guard module re-exports these names, so its existing importers are unaffected. PURE extraction —
byte-identical behaviour.
"""
import re

# accept stems (substring, negation-aware via _acceptance_intent). The rule: NEVER match blind to polarity.
_ACCEPT_INTENT = ("принима", "соглас", "берусь", "сделаю", "готов", "по рукам", "договор", "да, найд",
                  "да найд", "идёт", "я в деле", "помогу", "хочу задани", "дай задани", "дай квест")
# Audit 2026-06-14: the accept test was a bare substring match BLIND TO POLARITY — «не согласен» ("I don't
# agree"), «я не готов», «нет, не берусь», «не помогу», «не идёт» each contain an accept stem and were read as
# ACCEPTANCE, so the backstop forced a canon quest the player had REFUSED (and the explore and dodge routers
# misfired the same way). Gate every "the player accepted" guard on _acceptance_intent: an accept stem PRESENT
# **and not negated**. Conservative by design — any whiff of refusal means "don't force" (the model owns the
# clear cases; the backstop only fires on model -1, so a false-negative just declines to force, never forces a
# refusal). «да, не вопрос, берусь» still passes (no «не <accept>» / standalone «нет» / refusal verb there).
_REFUSAL_RE = re.compile(
    r"\b(не\s+(?:хочу|буду|стану|готов\w*|соглас\w*|берусь|возьмусь|могу|помог\w*|стоит|в\s+деле)"
    r"|нет|ни\s+за\s+что|не\s+в\s+этот\s+раз|отказ\w*|откажусь|отвали|проваливай)\b",
    re.IGNORECASE)

_GO_INTENT_RE = re.compile(r"\b(пошли|пойдём|пойдем|пойду|идём|идем|веди|поехали|в\s+путь)\b", re.I)
# gate_pass intent (Cameron at the Temple of Trials, and the gatekeeper class in general): a request to be LET
# PAST, or to pass WITHOUT a fight. Deliberately NOT _REFUSAL_RE-guarded — the canonical phrasings are
# themselves negative («не хочу драться» = "I don't want to fight", «давай без боя» = "let's skip the fight"),
# and that is a request to pass, not a refusal of the offer. General; the registry decides which NPC carries a
# gate_pass atom.
_GATE_PASS_RE = re.compile(
    r"пропуст[ии](?:шь|те)?\b|дай(?:те)?\s+(?:мне\s+|нам\s+)?пройти|дать\s+пройти|можно\s+(?:мне\s+)?пройти|"
    r"позволь\s+пройти|разреши\s+пройти|без\s+боя|без\s+драки|не\s+хочу\s+(?:с\s+тобой\s+)?драться|"
    r"не\s+будем\s+драться|не\s+станем\s+драться|обойд[её]мся\s+без|разойд[её]мся\s+миром|реши[мт]\s+миром|"
    r"мирно\s+разойти|давай\s+без\s+боя|зачем\s+(?:нам\s+)?драться|"
    # At Navarro: Chris the refueller («я новобранец из пополнения» = "I'm one of the new recruits") and the
    # gate sentry (the password itself). The registry still decides WHO carries a gate_pass atom — a match
    # on an atom-less NPC is a logged no-op, so the stems stay broad enough for how players really phrase it
    # («овечья голова говорю же», «да я новобранец сука»).
    r"\bя\s+новобранец|новобранец\s+из\b|из\s+пополнени\w*|меня\s+прислали|"
    r"прибыл\w*\s+(?:на\s+служб\w*|в\s+пополнени\w*)|хочу\s+(?:вступить|записаться|служить)|"
    r"овечья\s+голова|sheepshead|\bпароль\b",
    re.I)
# The training intent: the player asks a TEACHER to be taught a skill («научи меня» = "teach me", «обучи меня
# драться», «хочу научиться», «преподай»). A teacher atom (intent=train) then raises the real skill via
# train_skill. Scoped to the player asking to BE taught, NOT to «я научу тебя» ("I'll teach you").
_TRAIN_RE = re.compile(
    r"(?:научи|обучи|подучи|поучи)(?:шь|те)?\s+(?:меня|нас)|"
    r"(?:на)?учи(?:шь|те)?\s+меня\s+(?:драться|бить|владеть|навык)|"
    r"хочу\s+(?:на)?учиться|можешь\s+(?:ли\s+)?(?:меня\s+)?(?:на|об)учить|"
    r"научи\s+(?:меня\s+)?драться|преподай|дай\s+(?:мне\s+)?урок",
    re.I)
# Generic willingness-to-be-HIRED — «ищу работу» ("looking for work"), «берусь за любую работу», «готов на
# всё», «чем помочь», «я свободен», «дай любое дело», «что нужно (сделать)» — is NOT acceptance of a SPECIFIC
# deed. It must NOT fire a teleport atom before the NPC has even OFFERED anything. It classifies as NEITHER
# intent (unless an explicit go-word is ALSO present), so the turn falls through to a free reply and the NPC
# offers first. A SPECIFIC accept of a NAMED deed («помогу с браминами», «берусь за охрану», «согласен увести
# стадо») carries NO generic-willingness marker -> it still classifies as accept. Fail-SAFE, not perfect: the
# LLM intent call is the eventual judge, and here the heuristic errs toward "let the NPC offer first".
_GENERIC_WORKSEEK_RE = re.compile(
    r"ищу\s+(?:работу|дело|подработ|зарабо)|нужна\s+работа|любую\s+работу|"
    r"берусь\s+за\s+любую|есть\s+(?:какая|что[- ]?нибудь)?\s*работа|"
    r"что(?:-нибудь)?\s+для\s+меня|подзаработать|ищу\s+работёнк|"
    r"готов\w*\s+на\s+(?:вс[её]|любо\w+)|на\s+вс[её]\s+готов|"                                      # готов на всё/любое
    r"(?:дай|дайте|давай|поручи|ищу|есть|на)\s+любо\w*\s+(?:дело|работ|задани|поручени)|любо\w*\s+(?:дело|работёнк)|"  # дай любое дело
    r"чем\s+(?:я\s+)?(?:могу\s+)?помо\w*|чем\s+(?:могу\s+)?быть\s+полез|"                           # чем (могу) помочь
    r"я\s+свободен|к\s+(?:твоим|вашим)\s+услугам|"                                                  # я свободен
    r"что\s+(?:для\s+теб\w*|для\s+вас|теб\w*|вам)\s+(?:могу\s+)?с?делать|"                           # что для тебя сделать
    r"что\s+(?:мне\s+)?(?:нужно|надо|требуется|сделать|делать)",                                    # что нужно (сделать)
    re.I)
# make-leave INTENT (threat / ultimatum / order to leave / send-for-help) — GENERAL + NPC-agnostic, negation-guarded.
_MAKE_LEAVE_RE = re.compile(
    r"вал[иь]\b|свал[иь]|убир[ае]йся|уебыв|уёбыв|отвали|пош[её]л\s+вон|проваливай|прова[лж]ива|спрова[дж]|выпрова|"
    r"выгна|припугн|спугн|пугн|уход\w*\s+отсюда|уйд[иёе]\w*\s+отсюда|уноси\s+ноги|беги\s+за\s+(?:помощ|подмог)|"
    # ultimatum «либо/или уходишь, либо/или убью/прирежу» — the leave-or-die threat IS a make-leave intent
    r"(?:либо|или)\s+уход|уход\w*.{0,18}(?:либо|или).{0,8}(?:убь|прир[еж]|пристрел|порешу)|"
    r"(?:уход|уйд|вал|свал|убир|уебыв).{0,18}(?:или|иначе|а\s+то).{0,10}(?:убь|прир|пристрел|порешу)|"
    r"чтоб.{0,14}(?:уш[её]л|свалил|сбежал|убрался)",
    re.I)


def _acceptance_intent(player: str) -> bool:
    """True when the line is a genuine acceptance/commitment: an accept stem is present AND the line is not a
    refusal or a negated acceptance. Shared by every guard that acts on 'the player accepted'."""
    p = (player or "").lower()
    return any(w in p for w in _ACCEPT_INTENT) and not _REFUSAL_RE.search(p)


def _is_make_leave(player: str) -> bool:
    """Make-NPC-leave intent by TEXT, GENERAL and NPC-agnostic, negation-guarded. This is the deterministic
    FLOOR signal ONLY: the PRIMARY router is the role-annotated option_index, where the LLM picks the option
    marked «РОЛЬ: спровадить» ("ROLE: send them away"). Generalised from the retired Torr-specific regex and
    the retired drive_off boolean the LLM under-emitted (~92% miss). Used by the role-router floor and by the
    short-circuit in _dialogue_atom_intent; the LLM's option_index covers the phrasings this regex misses."""
    p = str(player or "")
    return bool(_MAKE_LEAVE_RE.search(p) and not _REFUSAL_RE.search(p))


def _dialogue_atom_intent(player: str) -> str | None:
    """Classify a free line into a dialogue ATOM intent-kind: a make-leave intent is NEITHER (categorically
    not a quest accept or go); an explicit go-now then OUTRANKS a plain accept; a negated line, and generic
    job-seeking, are neither. General (not NPC-specific) — the atom registry decides which NPC has an atom for
    a given kind. The make-leave check is the GENERAL _is_make_leave, which replaced both the LLM's drive_off
    boolean and the old Torr-specific regex."""
    p = str(player or "")
    # SYSTEMIC, and it holds for every atom NPC: a make-leave intent is categorically NOT accept/go, so a
    # go-word INSIDE a make-leave line («сваливай, пошли уже» = "get lost, off you go") cannot fire a quest
    # atom — that was the live spurious re-teleport. General and negation-aware (_is_make_leave). The PRIMARY
    # make-leave route is the role-annotated option_index; this guards the residual path where it returns -1.
    if _is_make_leave(p):
        return None
    if _GO_INTENT_RE.search(p) and not re.search(r"\bне\b|\bнет\b", p.lower()):
        return "go_now"   # explicit go-word OUTRANKS everything (incl. alongside job-seeking words) — «идём на выгон»
    if _GATE_PASS_RE.search(p):
        return "gate_pass"  # «пропусти / дай пройти / без боя» — the registry decides who has a gate_pass atom
    if _TRAIN_RE.search(p):
        return "train"      # «научи меня / обучи драться» — a teacher atom (intent=train) raises the real skill
    if _GENERIC_WORKSEEK_RE.search(p) and not _GO_INTENT_RE.search(p):
        return None       # generic job-seeking with no go-word -> neither intent (the NPC offers first)
    if _acceptance_intent(p):
        return "accept"   # «я помогу / согласен / берусь» — the flag-only accept atom, negation-aware
    return None
