"""Generate registry.json — the machine-readable catalog the CLI resolves against."""

from __future__ import annotations

import json
import pathlib

from .manifest import Manifest, load_all


def build(repo_root: pathlib.Path) -> dict:
    skills = []
    for m in load_all(repo_root):
        skills.append(
            {
                "name": m.name,
                "description": m.description,
                "version": m.version,
                "owner": m.owner,
                "status": m.status,
                "tags": m.tags,
                "evals": {
                    "execution_cases": len(m.execution_cases()),
                    "has_triggers": m.triggers_file() is not None,
                },
            }
        )
    return {
        "_generated": "by `skill registry` — do not edit by hand",
        "skills": skills,
    }


def registry_path(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root / "registry.json"


def write(repo_root: pathlib.Path) -> pathlib.Path:
    path = registry_path(repo_root)
    path.write_text(json.dumps(build(repo_root), indent=2) + "\n", encoding="utf-8")
    return path


def is_current(repo_root: pathlib.Path) -> bool:
    path = registry_path(repo_root)
    if not path.is_file():
        return False
    try:
        on_disk = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return on_disk == build(repo_root)


def load(repo_root: pathlib.Path) -> dict:
    return json.loads(registry_path(repo_root).read_text(encoding="utf-8"))


def catalog_lines(manifests: list[Manifest]) -> str:
    """The skill catalog exactly as an agent would see it: name + trigger description."""
    return "\n".join(f"- {m.name}: {m.description}" for m in manifests)
