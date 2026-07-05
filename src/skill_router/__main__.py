"""Allow `python3 -m skill_router ...` to dispatch to the CLI."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
