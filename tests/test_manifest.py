import pathlib
import tempfile
import unittest

from skilldeck.manifest import ManifestError, parse_skill_md

GOOD = """---
name: my-skill
description: Use when doing the thing.
version: 1.2.3
owner: ajay
status: draft
tags: [a, b]
---

# body here
"""


class TestManifest(unittest.TestCase):
    def _write(self, text):
        d = pathlib.Path(tempfile.mkdtemp())
        p = d / "SKILL.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_parses_good_manifest(self):
        m = parse_skill_md(self._write(GOOD))
        self.assertEqual(m.name, "my-skill")
        self.assertEqual(m.version, "1.2.3")
        self.assertEqual(m.tags, ["a", "b"])
        self.assertEqual(m.body, "# body here")

    def test_rejects_missing_frontmatter(self):
        with self.assertRaises(ManifestError):
            parse_skill_md(self._write("# no frontmatter\n"))

    def test_rejects_bad_status(self):
        with self.assertRaises(ManifestError):
            parse_skill_md(self._write(GOOD.replace("status: draft", "status: cool")))

    def test_rejects_bad_version(self):
        with self.assertRaises(ManifestError):
            parse_skill_md(self._write(GOOD.replace("1.2.3", "1.2")))

    def test_rejects_bad_name(self):
        with self.assertRaises(ManifestError):
            parse_skill_md(self._write(GOOD.replace("my-skill", "My Skill")))


if __name__ == "__main__":
    unittest.main()
