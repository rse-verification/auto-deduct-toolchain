#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
from unittest import TestCase, main


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSISTANT = REPO_ROOT / "Dockerfiles" / "bin" / "autodeduct-contract-assistant"
GUI = REPO_ROOT / "Dockerfiles" / "bin" / "autodeduct-contract-assistant-gui"
SAMPLE = REPO_ROOT / "tests" / "contract-assistant" / "missing_helper.c"


def load_script(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


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

    def test_gui_analysis_response_contains_pipeline_and_prompt(self):
        gui = load_script("autodeduct_contract_assistant_gui", GUI)

        response = gui.analyze_code("missing_helper.c", SAMPLE.read_text(), False)

        self.assertEqual(response["status"], "Analysis complete.")
        self.assertEqual(response["report"]["file"], "missing_helper.c")
        self.assertIn("maybe_add", response["summary"])
        self.assertIn("Missing helper function: maybe_add", response["llm_prompt"])
        helper_step = response["pipeline"][2]
        self.assertEqual(helper_step["name"], "Check helper contracts")
        self.assertEqual(helper_step["status"], "warn")


if __name__ == "__main__":
    main()
