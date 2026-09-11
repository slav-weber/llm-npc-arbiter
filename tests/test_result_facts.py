"""The closed fact vocabulary the narrating model is given, pinned against arbiter/result_facts.py.

The engine resolves an action and emits the facts; the narrating call is given a rendering of them
and may describe only that. The rendering is in the game's language, and so are the words matched
here.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arbiter import result_facts    # noqa: E402

_GRANTED = "СОГЛАСИЛСЯ"     # «Враг СОГЛАСИЛСЯ пощадить.» = "The enemy AGREED to spare you."
_REFUSED = "ОТКАЗАЛ"        # «Враг ОТКАЗАЛ в пощаде.» = "The enemy REFUSED mercy."


class ResultFacts(unittest.TestCase):
    """The prose can describe only what the engine reported."""

    def test_mercy_is_rendered_as_granted_only_when_the_engine_reports_a_yield(self):
        """The narrator hears that the enemy agreed to spare the player only when the engine said so.

        Real behaviour [CODE]: `render_ru` renders the mercy fact as agreement only for the value
        `yielded`, the engine's report that the enemy yielded; a bare `mercy` flag and every other
        value, `refused` among them, render as a refusal. Unlike dead or ko, whose presence is the
        event, a mercy fact without the engine's yield is the fail-safe refusal, so the prose can never
        describe a mercy the engine did not grant.
        """
        self.assertIn(_GRANTED, result_facts.render_ru("tier:success;mercy:yielded"))
        bare = result_facts.build(("mercy", ""))
        self.assertEqual(bare, "mercy")
        for facts in (bare, "mercy:", "tier:success;mercy", "mercy:refused", "mercy:spared", "mercy:true"):
            with self.subTest(facts=facts):
                text = result_facts.render_ru(facts)
                self.assertNotIn(_GRANTED, text)
                self.assertIn(_REFUSED, text)


if __name__ == "__main__":
    unittest.main()
