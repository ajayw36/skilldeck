"""Programmatic checks — run against the sandbox filesystem and the transcript.

Checks run first, always: they're the only signal that doesn't drift with judge
models. The LLM judge only sees cases the checks can't decide.
"""

from __future__ import annotations

import pathlib
import re

from .runner import Transcript


class CheckResult:
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def run_checks(checks: list, transcript: Transcript, sandbox: pathlib.Path) -> list[CheckResult]:
    results = []
    for spec in checks:
        if isinstance(spec, str):
            kind, arg = spec, None
        elif isinstance(spec, dict) and len(spec) == 1:
            kind, arg = next(iter(spec.items()))
        else:
            results.append(CheckResult(str(spec), False, "unrecognized check spec"))
            continue
        fn = _CHECKS.get(kind)
        if fn is None:
            results.append(CheckResult(kind, False, f"unknown check kind {kind!r}"))
        else:
            results.append(fn(arg, transcript, sandbox))
    return results


def _transcript_mentions(arg, t: Transcript, _sb) -> CheckResult:
    ok = str(arg).lower() in t.all_text().lower()
    return CheckResult(f"transcript_mentions:{arg}", ok,
                       "" if ok else f"{arg!r} never appeared in the transcript")


def _no_command_matching(arg, t: Transcript, _sb) -> CheckResult:
    pat = re.compile(str(arg))
    hits = [c for c in t.bash_commands() if pat.search(c)]
    return CheckResult(f"no_command_matching:{arg}", not hits,
                       "" if not hits else f"matched: {hits[:3]}")


def _command_matching(arg, t: Transcript, _sb) -> CheckResult:
    pat = re.compile(str(arg))
    ok = any(pat.search(c) for c in t.bash_commands())
    return CheckResult(f"command_matching:{arg}", ok,
                       "" if ok else "no Bash command matched")


def _file_exists(arg, _t, sb: pathlib.Path) -> CheckResult:
    ok = (sb / str(arg)).exists()
    return CheckResult(f"file_exists:{arg}", ok, "" if ok else "file not found in sandbox")


def _file_absent(arg, _t, sb: pathlib.Path) -> CheckResult:
    ok = not (sb / str(arg)).exists()
    return CheckResult(f"file_absent:{arg}", ok, "" if ok else "file exists in sandbox")


_CHECKS = {
    "transcript_mentions": _transcript_mentions,
    "no_command_matching": _no_command_matching,
    "command_matching": _command_matching,
    "file_exists": _file_exists,
    "file_absent": _file_absent,
}
