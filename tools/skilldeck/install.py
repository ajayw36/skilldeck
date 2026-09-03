"""Install skills into an agent config directory (default: ~/.claude/skills).

Install is a copy, not a symlink: users are insulated from teammates publishing
changes mid-task, and upgrades are deliberate (`skill update`).
"""

from __future__ import annotations

import datetime
import json
import pathlib
import shutil
import subprocess

from .manifest import ManifestError, parse_skill_md

LOCKFILE = "skilldeck.lock.json"
DEFAULT_TARGET = pathlib.Path.home() / ".claude" / "skills"

# Only the skill's payload is installed — evals stay in the repo.
INSTALL_EXCLUDE = {"evals", "fixtures"}


def _repo_commit(repo_root: pathlib.Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _load_lock(target: pathlib.Path) -> dict:
    lock = target / LOCKFILE
    if lock.is_file():
        return json.loads(lock.read_text(encoding="utf-8"))
    return {"skills": {}}


def _save_lock(target: pathlib.Path, lock: dict) -> None:
    (target / LOCKFILE).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


def install(repo_root: pathlib.Path, name: str, target: pathlib.Path = DEFAULT_TARGET) -> str:
    src = repo_root / "skills" / name
    if not (src / "SKILL.md").is_file():
        raise ManifestError(f"no such skill: {name} (looked in {src})")
    m = parse_skill_md(src / "SKILL.md")

    target.mkdir(parents=True, exist_ok=True)
    dst = target / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if n in INSTALL_EXCLUDE])

    lock = _load_lock(target)
    lock["skills"][name] = {
        "version": m.version,
        "status": m.status,
        "source": str(repo_root),
        "commit": _repo_commit(repo_root),
        "installed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    _save_lock(target, lock)
    return f"installed {name} {m.version} ({m.status}) -> {dst}"


def update(repo_root: pathlib.Path, target: pathlib.Path = DEFAULT_TARGET,
           name: str | None = None) -> list[str]:
    """Reinstall locked skills whose repo version moved past the locked one."""
    lock = _load_lock(target)
    messages = []
    names = [name] if name else sorted(lock["skills"])
    for n in names:
        entry = lock["skills"].get(n)
        if entry is None:
            messages.append(f"{n}: not installed (use `skill install {n}`)")
            continue
        src_md = repo_root / "skills" / n / "SKILL.md"
        if not src_md.is_file():
            messages.append(f"{n}: gone from the repo — leaving installed copy; remove manually if retired")
            continue
        current = parse_skill_md(src_md)
        if current.version == entry["version"]:
            messages.append(f"{n}: up to date ({entry['version']})")
        else:
            messages.append(install(repo_root, n, target) + f" (was {entry['version']})")
    return messages
