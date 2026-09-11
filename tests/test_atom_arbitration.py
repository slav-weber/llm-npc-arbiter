"""How a player's line is routed to an atom intent, pinned against arbiter/atom_arbitration.py.

The classifier is the deterministic veto on the atom_id bypass path: when the model names an atom by
id, a consequential fire still needs a corroborating key from these patterns. The lines are in the
game's language, because that is what the patterns match.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arbiter import atom_arbitration as arbitration    # noqa: E402


class Arbitration(unittest.TestCase):
    """A consequential intent needs a line that really asks for it."""

    def test_a_negated_go_word_is_not_go_now(self):
        """A refusal that contains a go-word never routes to the go-now teleport.

        Real behaviour [CODE]: `_dialogue_atom_intent` returns go_now for a line with a go-word
        (пошли, пойдём, пойду, идём, веди, поехали, в путь: "let's go", "I'll go", "lead the way" and
        the like) only when the line has no standalone «не» ("not") or «нет» ("no"). Each refusal below
        contains a go-word, checked here so that the test cannot pass on a line the go pattern does not
        see, and must not classify as go_now: on the bypass path go_now fires a terminal teleport. The
        same go-words without a negation still do.
        """
        refusals = ("Я никуда не пойду.",               # "I am not going anywhere."
                    "Нет, не пойдём мы на выгон.",      # "No, we are not going to the pasture."
                    "Не веди меня туда.",               # "Don't lead me there."
                    "Не, никуда я с тобой не пойду.")   # "Nah, I'm not going anywhere with you."
        for line in refusals:
            with self.subTest(line=line):
                self.assertTrue(arbitration._GO_INTENT_RE.search(line))
                self.assertNotEqual(arbitration._dialogue_atom_intent(line), "go_now")
        for line in ("Пошли!", "Хорошо, пойдём на выгон."):   # "Let's go!", "All right, to the pasture."
            with self.subTest(line=line):
                self.assertEqual(arbitration._dialogue_atom_intent(line), "go_now")

    def test_job_seeking_with_an_accept_stem_is_vetoed(self):
        """Offering to take any job is not accepting a specific deed: the NPC offers first.

        Real behaviour [CODE]: generic job-seeking (`_GENERIC_WORKSEEK_RE`) without a go-word
        classifies as no intent, and that veto runs before the acceptance test. Each line below also
        carries an accept stem that `_acceptance_intent` recognises, checked here so that the veto is
        what stops it, and must not classify as accept: a quest atom would fire before the NPC had
        offered anything. An acceptance of a named deed carries no job-seeking marker and still
        classifies as accept.
        """
        seeking = ("Готов на всё, дай любое дело.",     # "Ready for anything, give me any job."
                   "Берусь за любую работу.",           # "I'll take any work."
                   "Ищу работу — помогу чем смогу.",    # "Looking for work, I'll help however I can."
                   "Я готов, что нужно сделать?")       # "I'm ready, what needs doing?"
        for line in seeking:
            with self.subTest(line=line):
                self.assertTrue(arbitration._acceptance_intent(line))
                self.assertTrue(arbitration._GENERIC_WORKSEEK_RE.search(line))
                self.assertIsNone(arbitration._dialogue_atom_intent(line))
        for line in ("Помогу с браминами.",             # "I'll help with the brahmin."
                     "Берусь за охрану стада.",         # "I'll take on guarding the herd."
                     "Согласен увести стадо."):         # "I agree to drive the herd off."
            with self.subTest(line=line):
                self.assertEqual(arbitration._dialogue_atom_intent(line), "accept")


if __name__ == "__main__":
    unittest.main()
