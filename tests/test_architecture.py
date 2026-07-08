"""Architecture guardrails for the vertical-slice package layout."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "skill_router"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add("." * node.level + node.module)
    return imports


def test_shared_does_not_depend_on_features() -> None:
    for path in (SRC / "shared").glob("*.py"):
        assert not any("skill_router.features" in name for name in _imports(path)), path


def test_feature_slices_do_not_import_each_other() -> None:
    feature_root = SRC / "features"
    for feature_dir in feature_root.iterdir():
        if not feature_dir.is_dir() or feature_dir.name.startswith("__"):
            continue
        for path in feature_dir.rglob("*.py"):
            imports = _imports(path)
            forbidden = [
                name
                for name in imports
                if name.startswith("skill_router.features.")
                and not name.startswith(f"skill_router.features.{feature_dir.name}.")
            ]
            assert forbidden == [], f"{path}: {forbidden}"
