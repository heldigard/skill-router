"""skill-router: unified skill routing for cross-CLI coding agents.

Consolidates three formerly-fragmented pieces:
  - skill-router.py  (UserPromptSubmit hook: regex hint injection)
  - intent_route.py   (prompt classifier: category + model tier)
  - skills-audit.py   (catalog health gate: structural/drift/discrim/bench)

Adds a new capability:
  - depth selector    (multi-level skills: summary/body/section/references)

Entry points:
  - command.main()  — UserPromptSubmit hook (settings.json wire)
  - cli.main()      — unified CLI (intent / audit / route / depth / catalog)
"""

from __future__ import annotations

__version__ = "0.1.0"
