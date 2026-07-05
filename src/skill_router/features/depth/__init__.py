"""depth: select skill load level (summary/body/section) for a prompt.

NEW capability — the value-add over the legacy monoliths. When the router
recommends a multi-level skill, the depth selector ranks sections by embedding
relevance to the prompt and suggests loading just one section file instead of
the whole SKILL.md body. Progressive disclosure L2.
"""

from __future__ import annotations
