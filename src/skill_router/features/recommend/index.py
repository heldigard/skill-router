"""Disk-backed embedding index for skill catalog recommendations."""

from __future__ import annotations

import json
import os
from pathlib import Path

from ...shared.config import AUDIT_EMBED_TIMEOUT
from ...shared.paths import state_dir
from ...shared.skill_io import Skill

BUILD_EMBED_TIMEOUT = AUDIT_EMBED_TIMEOUT
_INDEX_DIR_NAME = "skill-router"


def _index_dir() -> Path:
    d = state_dir() / _INDEX_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _index_paths() -> tuple[Path, Path, Path]:
    base = _index_dir()
    return (
        base / "catalog.npz",  # matrix + names array
        base / "catalog.meta.json",  # {skill_name: mtime_ns}
        base / "catalog.dim",  # single int: embedding dim (sanity check)
    )


def _catalog_text(skill: Skill) -> str:
    """Compact surrogate embedded per skill: name + description only.

    The system-prompt catalog uses exactly these two fields, so ranking on
    them matches what the model would see (and lets us resuscitate dropped
    entries by the same name).
    """
    desc = (skill.description or "").strip()
    return f"{skill.name}: {desc}" if desc else skill.name


def _skill_mtime(skill: Skill) -> int:
    try:
        return skill.skill_md.stat().st_mtime_ns
    except (OSError, AttributeError):
        return 0


def _load_meta(path: Path) -> dict[str, int]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_meta(path: Path, meta: dict[str, int]) -> None:
    try:
        _atomic_write_text(path, json.dumps(meta, sort_keys=True))
    except OSError:
        pass


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text atomically (.tmp + os.replace). Crash-safe across processes."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_save_npz(npz_path: Path, matrix, names) -> None:
    """Save npz atomically so a concurrent reader never sees a partial file.

    numpy's savez appends '.npz' if the name lacks it, so the temp name MUST end
    in '.npz' or os.replace below would target a non-existent file.
    """
    import numpy as np  # type: ignore

    tmp = npz_path.with_name(npz_path.stem + ".tmp.npz")
    np.savez_compressed(tmp, matrix=matrix, names=np.asarray(names))
    os.replace(tmp, npz_path)


def _load_disk_vectors(npz_path: Path) -> tuple[dict[str, list[float]], list[str]]:
    """Read the on-disk npz into {name: vector}. Empty on missing/corrupt.

    Safe against a concurrent atomic write: os.replace presents either the old
    complete file or the new one, never a partial.
    """
    try:
        import numpy as np  # type: ignore
    except Exception:
        return {}, []
    if not npz_path.exists():
        return {}, []
    try:
        blob = np.load(npz_path, allow_pickle=False)
        names = [str(n) for n in blob["names"]]
        vecs = {name: list(row) for name, row in zip(names, blob["matrix"], strict=False)}
        return vecs, names
    except (OSError, ValueError, KeyError):
        return {}, []


def _acquire_build_lock():
    """Non-blocking cross-process lock. Returns an open file handle or None.

    The SessionStart warmup (nohup background) and a UserPromptSubmit hook can
    both decide to build at once. The lock lets one build while the other reads
    the existing on-disk index instead of duplicating ~115 embeds. fcntl is
    POSIX-only; this host is native Linux (Ubuntu).
    """
    try:
        import fcntl
    except ImportError:
        return None  # non-POSIX: no dedup, atomic write still prevents corruption
    lock_path = _index_dir() / "catalog.lock"
    try:
        lf = open(lock_path, "w")  # noqa: SIM115 — held open until released
    except OSError:
        return None
    try:
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lf
    except OSError:
        lf.close()
        return None


def _release_build_lock(lf) -> None:
    try:
        lf.close()
    except Exception:  # noqa: BLE001 — lock release must never raise
        pass


def _needs_rebuild(
    skills: list[Skill], metas: dict[str, int], existing: dict[str, list[float]]
) -> bool:
    """True if any skill is missing, stale (mtime changed), or extra in the index."""
    live = {sk.name: _skill_mtime(sk) for sk in skills}
    if set(live) != set(metas) or set(live) != set(existing):
        return True
    return any(metas.get(name) != mtime for name, mtime in live.items())


def _build_index(
    skills: list[Skill], existing: dict[str, list[float]], metas: dict[str, int]
) -> tuple[list[list[float]], list[str], dict[str, int]] | None:
    """Embed any skill missing or stale in the cache. Returns None if Ollama down.

    Reuses cached vectors whose mtime is unchanged (incremental update); embeds
    the rest. Late-imports numpy/embed so a missing dep degrades to None rather
    than raising.
    """
    try:
        import numpy as np  # type: ignore

        from ...shared.embed import embed, is_alive
    except Exception:
        return None

    if not is_alive():
        return None

    vectors: list[list[float]] = []
    names: list[str] = []
    new_metas: dict[str, int] = {}
    changed = False
    for sk in skills:
        mtime = _skill_mtime(sk)
        cached = existing.get(sk.name)
        if cached is not None and metas.get(sk.name) == mtime:
            vectors.append(cached)
        else:
            vec = embed(_catalog_text(sk), timeout=BUILD_EMBED_TIMEOUT)
            if vec is None:
                # Ollama bailed mid-rebuild: skip this skill but keep the rest.
                continue
            vectors.append(vec)
            changed = True
        names.append(sk.name)
        new_metas[sk.name] = mtime

    if not vectors:
        return None

    # Persist only when something actually changed (amortizes disk writes).
    # Atomic (.tmp + os.replace) so a concurrent reader never sees a partial npz.
    if changed or len(new_metas) != len(metas):
        npz_path, meta_path, dim_path = _index_paths()
        try:
            matrix = np.asarray(vectors, dtype=np.float32)
            _atomic_save_npz(npz_path, matrix, names)
            _save_meta(meta_path, new_metas)
            _atomic_write_text(dim_path, str(matrix.shape[1]))
        except OSError:
            pass
    return vectors, names, new_metas


def _disk_matrix_or_none(
    names: list[str], existing: dict[str, list[float]]
) -> tuple[object, list[str]] | None:
    """Materialize a matrix from already-loaded vectors, or None if empty."""
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    if not existing or not names:
        return None
    matrix = np.asarray([existing[n] for n in names], dtype=np.float32)
    return matrix, list(names)


def ensure_index(
    skills: list[Skill], force_rebuild: bool = False
) -> tuple[object, list[str]] | None:
    """Load or build the on-disk semantic index. Returns (matrix, names) or None.

    ``matrix`` is a numpy (N, dim) float32 array; ``names`` aligns rows to skill
    names. Returns None when Ollama or numpy is unavailable (caller falls back
    to lexical ranking). On ``force_rebuild`` the mtime cache is ignored.

    Race-safe: the build runs under a cross-process lock so the SessionStart
    warmup and a concurrent UserPromptSubmit hook never duplicate the ~115 embeds.
    A reader that loses the lock reuses whatever index is on disk rather than
    racing a writer; atomic writes (.tmp + os.replace) guarantee it never sees a
    partial npz.
    """
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None

    npz_path, meta_path, _ = _index_paths()
    metas = {} if force_rebuild else _load_meta(meta_path)
    existing, names = _load_disk_vectors(npz_path)

    # Fast path: index on disk is fresh — return it without embedding anything.
    if not force_rebuild and existing and not _needs_rebuild(skills, metas, existing):
        return _disk_matrix_or_none(names, existing)

    # Build under lock; if another process holds it, reuse the on-disk index.
    lock = _acquire_build_lock()
    if lock is None:
        return _disk_matrix_or_none(names, existing)
    try:
        built = _build_index(skills, existing, metas)
    finally:
        _release_build_lock(lock)
    if built is None:
        return _disk_matrix_or_none(names, existing)
    vectors, built_names, _ = built
    return np.asarray(vectors, dtype=np.float32), built_names
