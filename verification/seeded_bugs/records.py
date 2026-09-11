"""The two record types of a seeded-bug catalogue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Edit:
    file: str       # path relative to the repository root, forward slashes
    find: str       # exact text; must occur exactly once in the file when the edit is applied
    replace: str


@dataclass(frozen=True)
class Bug:
    id: str
    area: str
    title: str
    story: str                      # how an agent plausibly arrives at this change
    edits: tuple[Edit, ...]
    canary: bool = False
