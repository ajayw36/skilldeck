"""Parse and validate SKILL.md files (YAML frontmatter + markdown body)."""

from __future__ import annotations

import dataclasses
import pathlib
import re

import yaml

STATUSES = ("draft", "shared", "verified")
REQUIRED = ("name", "description", "version", "owner", "status")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
MAX_DESCRIPTION = 300
VERIFIED_MIN_CASES = 3


class ManifestError(ValueError):
    pass


@dataclasses.dataclass
class Manifest:
    name: str
    description: str
    version: str
    owner: str
    status: str
    tags: list[str]
    extra: dict
    body: str
    path: pathlib.Path

    @property
    def skill_dir(self) -> pathlib.Path:
        return self.path.parent

    @property
    def evals_dir(self) -> pathlib.Path:
        return self.skill_dir / "evals"

    def execution_cases(self) -> list[pathlib.Path]:
        cases = self.evals_dir / "cases"
        if not cases.is_dir():
            return []
        return sorted(p for p in cases.glob("*.yaml") if p.is_file())

    def triggers_file(self) -> pathlib.Path | None:
        p = self.evals_dir / "triggers.yaml"
        return p if p.is_file() else None


def parse_skill_md(path: pathlib.Path) -> Manifest:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ManifestError(f"{path}: missing YAML frontmatter (file must start with ---)")
    try:
        front_raw, body = text[4:].split("\n---\n", 1)
    except ValueError:
        raise ManifestError(f"{path}: unterminated frontmatter (no closing ---)") from None
    try:
        front = yaml.safe_load(front_raw)
    except yaml.YAMLError as e:
        raise ManifestError(f"{path}: invalid YAML frontmatter: {e}") from None
    if not isinstance(front, dict):
        raise ManifestError(f"{path}: frontmatter must be a YAML mapping")

    missing = [k for k in REQUIRED if not front.get(k)]
    if missing:
        raise ManifestError(f"{path}: missing required fields: {', '.join(missing)}")

    name = str(front["name"])
    if not NAME_RE.match(name):
        raise ManifestError(f"{path}: name {name!r} must be lowercase kebab-case")
    version = str(front["version"])
    if not VERSION_RE.match(version):
        raise ManifestError(f"{path}: version {version!r} must be semver (x.y.z)")
    status = str(front["status"])
    if status not in STATUSES:
        raise ManifestError(f"{path}: status {status!r} must be one of {STATUSES}")
    description = str(front["description"]).strip()
    if len(description) > MAX_DESCRIPTION:
        raise ManifestError(
            f"{path}: description is {len(description)} chars (max {MAX_DESCRIPTION}); "
            "trigger descriptions must stay short enough to sit in the agent's catalog"
        )
    tags = front.get("tags") or []
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise ManifestError(f"{path}: tags must be a list of strings")

    extra = {k: v for k, v in front.items() if k not in (*REQUIRED, "tags")}
    return Manifest(
        name=name,
        description=description,
        version=version,
        owner=str(front["owner"]),
        status=status,
        tags=tags,
        extra=extra,
        body=body.strip(),
        path=path,
    )


def load_all(repo_root: pathlib.Path) -> list[Manifest]:
    """Load every skill manifest under skills/, raising on the first invalid one."""
    skills_dir = repo_root / "skills"
    manifests = []
    if not skills_dir.is_dir():
        return manifests
    for entry in sorted(skills_dir.iterdir()):
        if entry.name.startswith("."):
            continue
        if not entry.is_dir():
            raise ManifestError(f"{entry}: skills/ must contain only skill directories")
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            raise ManifestError(f"{entry}: missing SKILL.md")
        m = parse_skill_md(skill_md)
        if m.name != entry.name:
            raise ManifestError(
                f"{skill_md}: manifest name {m.name!r} must match directory name {entry.name!r}"
            )
        manifests.append(m)
    return manifests


def validate_repo(repo_root: pathlib.Path) -> list[str]:
    """Full lint. Returns a list of problems (empty = clean)."""
    problems: list[str] = []
    try:
        manifests = load_all(repo_root)
    except ManifestError as e:
        return [str(e)]

    for m in manifests:
        if m.status == "verified":
            n = len(m.execution_cases())
            if n < VERIFIED_MIN_CASES:
                problems.append(
                    f"{m.name}: status is 'verified' but has {n} execution eval case(s) "
                    f"(minimum {VERIFIED_MIN_CASES})"
                )
            tf = m.triggers_file()
            if tf is None:
                problems.append(f"{m.name}: status is 'verified' but has no evals/triggers.yaml")
            else:
                t = yaml.safe_load(tf.read_text(encoding="utf-8")) or {}
                if not t.get("should_trigger") or not t.get("should_not_trigger"):
                    problems.append(
                        f"{m.name}: triggers.yaml needs non-empty should_trigger AND "
                        "should_not_trigger (near-miss negatives are the eval that matters)"
                    )

    # Trigger-collision lint: warn when two descriptions look near-identical.
    for i, a in enumerate(manifests):
        for b in manifests[i + 1 :]:
            if _jaccard(a.description, b.description) > 0.6:
                problems.append(
                    f"{a.name} / {b.name}: descriptions overlap heavily — the agent may "
                    "not be able to pick between them; sharpen the trigger boundaries"
                )
    return problems


def _jaccard(a: str, b: str) -> float:
    ta, tb = set(re.findall(r"[a-z0-9]+", a.lower())), set(re.findall(r"[a-z0-9]+", b.lower()))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
