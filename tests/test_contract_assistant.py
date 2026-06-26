#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSISTANT = REPO_ROOT / "Dockerfiles" / "bin" / "autodeduct-contract-assistant"
SAMPLE = REPO_ROOT / "tests" / "contract-assistant" / "missing_helper.c"


class ContractAssistantTests(TestCase):
    def run_assistant(self, *args):
        return subprocess.run(
            [sys.executable, str(ASSISTANT), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_reports_missing_helper_contract(self):
        result = self.run_assistant("--json", str(SAMPLE))

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        missing_helpers = report[0]["missing_helper_contracts"]
        self.assertEqual([helper["name"] for helper in missing_helpers], ["maybe_add"])
        self.assertEqual(report[0]["called_by"]["maybe_add"], ["main"])

    def test_fail_on_missing_uses_nonzero_exit(self):
        result = self.run_assistant("--fail-on-missing", str(SAMPLE))

        self.assertEqual(result.returncode, 1)
        self.assertIn("maybe_add", result.stdout)

    def test_writes_llm_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_path = Path(tmpdir) / "prompt.md"
            result = self.run_assistant("--llm-prompt", str(prompt_path), str(SAMPLE))

            self.assertEqual(result.returncode, 0, result.stderr)
            prompt = prompt_path.read_text(encoding="utf-8")
            self.assertIn("Missing helper function: maybe_add", prompt)
            self.assertIn("Frama-C/WP/Eva", prompt)
            self.assertIn("void maybe_add", prompt)


if __name__ == "__main__":
    main()
