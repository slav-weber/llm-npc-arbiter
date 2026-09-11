"""The response contract, pinned against arbiter/schemas.py.

The module is pure data: for each seam (one function call the model answers) a map of typed fields
and a list of required names. The caller, which is not in this repository, wraps each seam into a
strict function-calling schema with additionalProperties: false. What the module itself decides, and
what these tests pin, is which fields a seam offers and how each one is typed.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arbiter import schemas    # noqa: E402

_JSON_TYPES = {"string", "integer", "number", "boolean", "array", "object"}


def _seams() -> dict[str, tuple[dict, list]]:
    """Every seam the module defines, keyed by the name of its field map: (fields, required names)."""
    return {name: (getattr(schemas, name), getattr(schemas, name[: -len("PROPS")] + "REQUIRED"))
            for name in sorted(dir(schemas))
            if name.endswith("_PROPS") and isinstance(getattr(schemas, name), dict)}


class Schemas(unittest.TestCase):
    """What a model's answer can carry is decided here, not by the model."""

    def test_the_narrating_calls_offer_no_write_channel(self):
        """The narrating legs may only describe what the engine has already made true.

        Real behaviour [CODE]: the free-action narrate leg (`_NARRATE_PROPS`) offers narration,
        npc_reply, speaker and object_deed_done; the dialogue narrate leg (`_NARRATE_DIALOGUE_PROPS`)
        offers npc_reply alone. The one field that is not prose, object_deed_done, marks a pending deed
        done only when the engine's own examine state confirms it, per the module. None of the
        durable-write channels the other seams carry (state_set for the ledger, atom_id for a write
        atom, the fx effect slots) is there. The sets are pinned exactly: the module calls every schema
        edit a contract change that needs a re-verify, and a new field on a narrating leg is exactly
        that.
        """
        narrating = {"_NARRATE_PROPS": {"narration", "npc_reply", "speaker", "object_deed_done"},
                     "_NARRATE_DIALOGUE_PROPS": {"npc_reply"}}
        elsewhere = (schemas._PROPS, schemas._DECIDE_PROPS, schemas._DIALOGUE_PROPS, schemas._REFLECT_PROPS)
        channels = {field for fields in elsewhere for field in fields
                    if field in ("state_set", "atom_id", "fx") or field.startswith("fx_")}
        self.assertLessEqual({"state_set", "atom_id", "fx", "fx_success"}, channels)
        for name, expected in narrating.items():
            fields = set(getattr(schemas, name))
            with self.subTest(seam=name):
                self.assertFalse(fields & channels,
                                 f"{name} offers a write channel: {sorted(fields & channels)}")
                self.assertEqual(fields, expected)

    def test_the_intent_set_is_closed(self):
        """The model names one intent from a fixed set, and it must name one.

        Real behaviour [CODE]: `kind` is a string enumeration of exactly valid, trivial, impossible,
        unclear and mercy, in the one-call seam (`_PROPS`) and the two-call decide seam
        (`_DECIDE_PROPS`) alike, and it is required in both, so a strict call can neither omit it nor
        invent a sixth intent.
        """
        intents = ["valid", "trivial", "impossible", "unclear", "mercy"]
        seams = _seams()
        for name in ("_PROPS", "_DECIDE_PROPS"):
            fields, required = seams[name]
            with self.subTest(seam=name):
                self.assertEqual(fields["kind"], {"type": "string", "enum": intents})
                self.assertIn("kind", required)

    def test_every_field_is_declared_and_typed(self):
        """No seam leaves room for a field nobody declared or typed.

        Real behaviour [CODE]: the module defines no whole object schema, so the top-level
        additionalProperties: false belongs to the caller and cannot be checked here. What the module
        does decide is pinned: every field declares a JSON type; an enumeration is a non-empty list of
        distinct strings; no schema sets additionalProperties to anything but false or uses
        patternProperties; every array declares its items and every nested object enumerates its
        fields; every required name is a declared field, so the caller's strict wrapper is valid.
        Not pinned, because it does not hold: the one nested object, the item of the summary seam's
        `claims` array, does not declare additionalProperties: false itself.
        """
        seams = _seams()
        self.assertIn("_NARRATE_PROPS", seams)          # the discovery found the seams at all
        for name, (fields, required) in seams.items():
            with self.subTest(seam=name):
                self.assertTrue(fields)
                self.assertLessEqual(set(required), set(fields), f"{name}: a required name is undeclared")
                for field, schema in fields.items():
                    self._assert_typed(f"{name}.{field}", schema)

    def _assert_typed(self, where: str, schema) -> None:
        self.assertIsInstance(schema, dict, where)
        self.assertIn(schema.get("type"), _JSON_TYPES, where)
        self.assertNotIn("patternProperties", schema, where)
        self.assertIs(schema.get("additionalProperties", False), False, where)
        if "enum" in schema:
            values = schema["enum"]
            self.assertTrue(values and all(isinstance(v, str) for v in values)
                            and len(set(values)) == len(values), f"{where}: {values}")
        if schema["type"] == "array":
            self.assertIn("items", schema, f"{where}: an array without items")
            self._assert_typed(f"{where}[]", schema["items"])
        if schema["type"] == "object":
            self.assertTrue(schema.get("properties"), f"{where}: a free-form object")
            for field, sub in schema["properties"].items():
                self._assert_typed(f"{where}.{field}", sub)


if __name__ == "__main__":
    unittest.main()
