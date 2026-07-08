"""Routing data structures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    """One routing rule plus orchestration metadata."""

    patterns: tuple[str, ...]
    hint: str
    skills: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    workers: tuple[str, ...] = ()
    doc_namespaces: tuple[str, ...] = ()
    priority: int = 50
