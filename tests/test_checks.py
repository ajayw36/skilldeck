import json
import pathlib
import tempfile
import unittest

from skilldeck.evals.checks import run_checks
from skilldeck.evals.runner import Transcript

STREAM = "\n".join([
    json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "STRIPE_KEY is missing, refusing to deploy"},
        {"type": "tool_use", "name": "Bash", "input": {"command": "cat .env.example"}},
    ]}}),
    json.dumps({"type": "result", "result": "Blocked: STRIPE_KEY unset."}),
])


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.t = Transcript.from_stream(STREAM)
        self.sb = pathlib.Path(tempfile.mkdtemp())
        (self.sb / "present.txt").write_text("x")

    def test_transcript_parsing(self):
        self.assertEqual(self.t.bash_commands(), ["cat .env.example"])
        self.assertIn("refusing to deploy", self.t.all_text())

    def test_checks(self):
        results = run_checks(
            [
                {"transcript_mentions": "STRIPE_KEY"},
                {"no_command_matching": r"deploy\.sh"},
                {"command_matching": r"cat"},
                {"file_exists": "present.txt"},
                {"file_absent": "deployed.marker"},
                {"file_exists": "missing.txt"},
                {"bogus_check": "x"},
            ],
            self.t, self.sb,
        )
        passed = [r.passed for r in results]
        self.assertEqual(passed, [True, True, True, True, True, False, False])


if __name__ == "__main__":
    unittest.main()
