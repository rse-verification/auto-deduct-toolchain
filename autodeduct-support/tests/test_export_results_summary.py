import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "export_results_summary.py"
SPEC = importlib.util.spec_from_file_location("export_results_summary", MODULE_PATH)
export_results_summary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(export_results_summary)


class ExportResultsSummaryTests(unittest.TestCase):
    def write_manifest(self, repo_root, cases):
        manifest = repo_root / "autodeduct-support" / "cases.json"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        return manifest

    def test_export_removes_paths_and_keeps_review_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            absolute_fixture = repo_root / "absolute-fixture"
            source = repo_root / "case.c"
            source.write_text("int entry(void) { return 0; }\n", encoding="utf-8")
            self.write_manifest(repo_root, [])
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "case",
                            "path": "case.c",
                            "module": "micro",
                            "kind": "micro_helper_inference_rewrite",
                            "probe_role": "helper_inference",
                            "evidence_tier": "tier_1_helper_inference",
                            "rewrite_of": "helper_boundary",
                            "expected_support": "supported",
                            "observed": "supported_end_to_end",
                            "conclusion": "supported_end_to_end",
                            "inference_evidence": "inferred_helpers",
                            "inferred_helper_contract_count": 1,
                            "missing_inferred_contract_count": 0,
                            "lib_entry": True,
                            "phases": {
                                "wp": {
                                    "status": "pass",
                                    "wp_goals": "4/4",
                                    "command": [str(absolute_fixture / "bin" / "frama-c"), "-wp"],
                                    "stdout": str(absolute_fixture / "stdout.txt"),
                                    "stderr": str(absolute_fixture / "stderr.txt"),
                                    "generated_files": [str(absolute_fixture / "out.c")],
                                    "seconds": 1.25,
                                }
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root)

            expected_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(exported[0]["source_sha256"], expected_hash)
            self.assertEqual(exported[0]["phase_statuses"]["wp"], "pass")
            self.assertEqual(exported[0]["wp_goals"], "4/4")
            self.assertIs(exported[0]["lib_entry"], True)
            output_text = out.read_text(encoding="utf-8")
            self.assertNotIn(str(absolute_fixture), output_text)
            self.assertNotIn("command", output_text)
            self.assertNotIn("stdout", output_text)
            self.assertNotIn("stderr", output_text)
            self.assertNotIn("generated_files", output_text)
            self.assertNotIn("seconds", output_text)

    def test_export_merges_rewrite_metadata_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            source = repo_root / "rewrite.c"
            source.write_text("int entry(void) { return 0; }\n", encoding="utf-8")
            self.write_manifest(
                repo_root,
                [
                    {
                        "id": "helper_valid_pointer_store_simpler",
                        "path": "rewrite.c",
                        "module": "micro",
                        "kind": "micro_helper_inference_rewrite",
                        "probe_role": "helper_inference",
                        "evidence_tier": "tier_1_helper_inference",
                        "evidence_role": "helper_inference_probe",
                        "rewrite_of": "helper_valid_pointer_store",
                        "expected_support": "supported",
                        "baseline_group": "academic_functional_v1",
                        "baseline_groups": ["academic_functional_v2"],
                        "helper_inference_claim": "positive",
                        "saida_tricera_opts": "-cpp -acsl",
                        "evaluation_profile": "configured_tricera_profile",
                        "direct_or_rewrite_relation": "rewrite_of:helper_valid_pointer_store",
                    }
                ],
            )
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "helper_valid_pointer_store_simpler",
                            "path": "rewrite.c",
                            "observed": "supported_end_to_end",
                            "conclusion": "supported_end_to_end",
                            "inference_evidence": "inferred_helpers",
                            "phase_statuses": {
                                "frama_parse": "pass",
                                "autodeduct_full": "unknown",
                                "func": "pass",
                                "aux": "pass",
                                "wp": "pass",
                            },
                            "wp_goals": "13/13",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root)

            self.assertEqual(exported[0]["module"], "micro")
            self.assertEqual(exported[0]["kind"], "micro_helper_inference_rewrite")
            self.assertEqual(exported[0]["probe_role"], "helper_inference")
            self.assertEqual(exported[0]["evidence_tier"], "tier_1_helper_inference")
            self.assertEqual(exported[0]["evidence_role"], "helper_inference_probe")
            self.assertEqual(exported[0]["rewrite_of"], "helper_valid_pointer_store")
            self.assertEqual(exported[0]["expected_support"], "supported")
            self.assertEqual(exported[0]["baseline_group"], "academic_functional_v1")
            self.assertEqual(exported[0]["baseline_groups"], ["academic_functional_v2"])
            self.assertEqual(exported[0]["helper_inference_claim"], "positive")
            self.assertEqual(exported[0]["saida_tricera_opts"], "-cpp -acsl")
            self.assertEqual(exported[0]["evaluation_profile"], "configured_tricera_profile")
            self.assertEqual(exported[0]["direct_or_rewrite_relation"], "rewrite_of:helper_valid_pointer_store")

    def test_export_preserves_module_smoke_metadata_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            for source_name in ("mini.c", "sample_module.c"):
                (repo_root / source_name).write_text("int entry(void) { return 0; }\n", encoding="utf-8")
            self.write_manifest(
                repo_root,
                [
                    {
                        "id": "sample_module_a",
                        "path": "mini.c",
                        "module": "sample-module-a",
                        "kind": "self_contained_verified_variant",
                        "evidence_tier": "tier_4_real_module_smoke_evidence",
                        "evidence_role": "module_smoke_evidence",
                        "baseline_group": "internal_module_smoke_v1",
                        "helper_inference_claim": "none",
                        "paper_model_input_classification": "module_smoke_only",
                    },
                    {
                        "id": "sample_module_b",
                        "path": "sample_module.c",
                        "module": "SAMPLE_MODULE",
                        "kind": "sample_module_anonymized",
                        "evidence_tier": "tier_4_real_module_smoke_evidence",
                        "evidence_role": "module_smoke_evidence",
                        "baseline_group": "internal_module_smoke_v1",
                        "helper_inference_claim": "none",
                        "paper_model_input_classification": "module_smoke_only",
                        "source_visibility": "internal",
                        "public_export": False,
                    },
                ],
            )
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "sample_module_a",
                            "path": "mini.c",
                            "helper_inference_claim": None,
                            "paper_model_input_classification": None,
                            "phase_statuses": {"frama_parse": "pass"},
                        },
                        {
                            "id": "sample_module_b",
                            "path": "sample_module.c",
                            "helper_inference_claim": "stale",
                            "paper_model_input_classification": "stale",
                            "source_visibility": "public",
                            "public_export": True,
                            "phase_statuses": {"frama_parse": "pass"},
                        },
                    ]
                ),
                encoding="utf-8",
            )

            exported = {
                item["id"]: item
                for item in export_results_summary.export_results(raw, out, repo_root)
            }

            self.assertEqual(exported["sample_module_a"]["helper_inference_claim"], "none")
            self.assertEqual(exported["sample_module_a"]["paper_model_input_classification"], "module_smoke_only")
            self.assertEqual(exported["sample_module_a"]["evidence_role"], "module_smoke_evidence")
            self.assertEqual(exported["sample_module_b"]["helper_inference_claim"], "none")
            self.assertEqual(
                exported["sample_module_b"]["paper_model_input_classification"],
                "module_smoke_only",
            )
            self.assertEqual(exported["sample_module_b"]["source_visibility"], "internal")
            self.assertIs(exported["sample_module_b"]["public_export"], False)

    def test_export_preserves_academic_functional_metadata_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            (repo_root / "helper.c").write_text("int entry(void) { return 0; }\n", encoding="utf-8")
            self.write_manifest(
                repo_root,
                [
                    {
                        "id": "helper_struct_basic",
                        "path": "helper.c",
                        "module": "micro",
                        "kind": "micro_helper_inference",
                        "probe_role": "helper_inference",
                        "evidence_tier": "tier_1_helper_inference",
                        "evidence_role": "helper_inference_probe",
                        "baseline_group": "academic_functional_v1",
                        "helper_inference_claim": "positive",
                        "expected_support": "supported",
                    }
                ],
            )
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "helper_struct_basic",
                            "path": "helper.c",
                            "phase_statuses": {"frama_parse": "pass"},
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root)

            self.assertEqual(exported[0]["probe_role"], "helper_inference")
            self.assertEqual(exported[0]["evidence_tier"], "tier_1_helper_inference")
            self.assertEqual(exported[0]["evidence_role"], "helper_inference_probe")
            self.assertEqual(exported[0]["baseline_group"], "academic_functional_v1")
            self.assertEqual(exported[0]["helper_inference_claim"], "positive")
            self.assertEqual(exported[0]["expected_support"], "supported")

    def test_export_preserves_explicit_lib_entry_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_manifest(repo_root, [])
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "case",
                            "module": "micro",
                            "kind": "micro_helper_inference",
                            "probe_role": "helper_inference",
                            "evidence_tier": "tier_1_helper_inference",
                            "expected_support": "supported",
                            "lib_entry": False,
                            "phases": {
                                "frama_parse": {"status": "pass", "lib_entry": True},
                                "func": {"status": "pass", "lib_entry": True},
                                "aux": {"status": "pass", "lib_entry": True},
                                "wp": {"status": "pass", "lib_entry": True, "wp_goals": "4/4"},
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root)

            self.assertIs(exported[0]["lib_entry"], False)

    def test_export_uses_phase_lib_entry_when_top_level_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_manifest(repo_root, [])
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "case",
                            "module": "micro",
                            "kind": "micro_helper_inference",
                            "probe_role": "helper_inference",
                            "evidence_tier": "tier_1_helper_inference",
                            "expected_support": "supported",
                            "phases": {
                                "frama_parse": {"status": "pass", "lib_entry": True},
                                "func": {"status": "pass", "lib_entry": True},
                                "aux": {"status": "pass", "lib_entry": True},
                                "wp": {"status": "pass", "lib_entry": True, "wp_goals": "4/4"},
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root)

            self.assertIs(exported[0]["lib_entry"], True)

    def test_export_preserves_rte_profile_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_manifest(repo_root, [])
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "case",
                            "module": "micro",
                            "kind": "micro_helper_inference",
                            "probe_role": "helper_inference",
                            "evidence_tier": "tier_1_helper_inference",
                            "expected_support": "supported",
                            "wp_goals": "4/4",
                            "rte_wp_goals": "3/5",
                            "rte_result": "failed_at_rte_wp_goals",
                            "rte_goal_breakdown": {
                                "pointer_validity": {"reported": 1, "proved": 1, "unproved": 0},
                                "array_bounds": {"reported": 1, "proved": 0, "unproved": 1},
                            },
                            "phase_statuses": {
                                "frama_parse": "pass",
                                "autodeduct_full": "unknown",
                                "func": "pass",
                                "aux": "pass",
                                "wp": "pass",
                                "rte_wp": "pass",
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root)

            self.assertEqual(exported[0]["functional_wp_goals"], "4/4")
            self.assertEqual(exported[0]["rte_wp_goals"], "3/5")
            self.assertEqual(exported[0]["rte_result"], "failed_at_rte_wp_goals")
            self.assertEqual(exported[0]["phase_statuses"]["rte_wp"], "pass")
            self.assertEqual(exported[0]["rte_goal_breakdown"]["array_bounds"]["unproved"], 1)

    def test_export_preserves_inferred_contract_quality_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            absolute_fixture = repo_root / "absolute-fixture" / "case.c"
            self.write_manifest(repo_root, [])
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "case",
                            "module": "micro",
                            "kind": "micro_helper_inference",
                            "probe_role": "helper_inference",
                            "evidence_tier": "tier_1_helper_inference",
                            "expected_support": "boundary",
                            "inference_evidence": "inferred_helpers",
                            "inferred_helper_contract_count": 1,
                            "missing_inferred_contract_count": 0,
                            "saida_output_parse_status": "pass",
                            "inferred_contract_quality": "vacuous_candidate",
                            "suspicious_contract_markers": ["ensures \\false;"],
                            "inferred_contract_quality_reason": "manual review required",
                            "functional_backend_status": "translation_error",
                            "functional_backend_error_kind": "horn_translation_arity_mismatch",
                            "functional_backend_error_text": (
                                f"Horn Translation Error in {absolute_fixture}: "
                                "expects 21 argument(s), but got 20"
                            ),
                            "tricera_result_present": True,
                            "process_first_failed_stage": "-",
                            "evidence_first_failed_stage": "func_backend_translation",
                            "phase_statuses": {
                                "frama_parse": "pass",
                                "func": "pass",
                                "aux": "fail",
                                "wp": "unknown",
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root)

            self.assertEqual(exported[0]["saida_output_parse_status"], "pass")
            self.assertEqual(exported[0]["inferred_contract_quality"], "vacuous_candidate")
            self.assertEqual(exported[0]["suspicious_contract_markers"], ["ensures \\false;"])
            self.assertEqual(exported[0]["inferred_contract_quality_reason"], "manual review required")
            self.assertEqual(exported[0]["functional_backend_status"], "translation_error")
            self.assertEqual(exported[0]["functional_backend_error_kind"], "horn_translation_arity_mismatch")
            self.assertIn("Horn Translation Error", exported[0]["functional_backend_error_text"])
            self.assertNotIn(str(absolute_fixture), json.dumps(exported))
            self.assertIs(exported[0]["tricera_result_present"], True)
            self.assertEqual(exported[0]["evidence_first_failed_stage"], "func_backend_translation")

    def test_export_omits_unexecuted_rows_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_manifest(repo_root, [])
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "executed",
                            "phase_statuses": {"frama_parse": "pass", "func": "unknown", "aux": "unknown", "wp": "unknown"},
                        },
                        {
                            "id": "unexecuted",
                            "phase_statuses": {
                                "frama_parse": "unknown",
                                "autodeduct_full": "unknown",
                                "func": "unknown",
                                "aux": "unknown",
                                "wp": "unknown",
                            },
                        },
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root)

            self.assertEqual([item["id"] for item in exported], ["executed"])

    def test_export_can_include_unexecuted_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_manifest(repo_root, [])
            raw = repo_root / "results.json"
            out = repo_root / "results-summary.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "unexecuted",
                            "phase_statuses": {
                                "frama_parse": "unknown",
                                "autodeduct_full": "unknown",
                                "func": "unknown",
                                "aux": "unknown",
                                "wp": "unknown",
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            exported = export_results_summary.export_results(raw, out, repo_root, include_unexecuted=True)

            self.assertEqual([item["id"] for item in exported], ["unexecuted"])

    def test_cli_uses_positional_input_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            absolute_fixture = repo_root / "absolute-fixture"
            source = repo_root / "case.c"
            source.write_text("int entry(void) { return 0; }\n", encoding="utf-8")
            self.write_manifest(repo_root, [])
            raw = repo_root / "raw-results.json"
            out = repo_root / "review" / "output.json"
            raw.write_text(
                json.dumps(
                    [
                        {
                            "id": "case",
                            "path": "case.c",
                            "module": "micro",
                            "kind": "micro_helper_inference",
                            "probe_role": "helper_inference",
                            "evidence_tier": "tier_1_helper_inference",
                            "expected_support": "supported",
                            "observed": "supported_end_to_end",
                            "conclusion": "supported_end_to_end",
                            "inference_evidence": "inferred_helpers",
                            "inferred_helper_contract_count": 1,
                            "missing_inferred_contract_count": 0,
                            "lib_entry": True,
                            "phases": {
                                "func": {
                                    "status": "pass",
                                    "command": [str(absolute_fixture / "bin" / "frama-c"), "-saida"],
                                    "stdout": str(absolute_fixture / "stdout.txt"),
                                    "stderr": str(absolute_fixture / "stderr.txt"),
                                    "generated_files": [str(absolute_fixture / "tmp_inferred_source_merged.c")],
                                },
                                "wp": {
                                    "status": "pass",
                                    "wp_goals": "8/8",
                                    "seconds": 0.5,
                                },
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--repo-root",
                    str(repo_root),
                    str(raw),
                    str(out),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            exported = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(exported[0]["id"], "case")
            self.assertEqual(exported[0]["phase_statuses"]["func"], "pass")
            self.assertEqual(exported[0]["wp_goals"], "8/8")
            self.assertIs(exported[0]["lib_entry"], True)
            output_text = out.read_text(encoding="utf-8")
            self.assertNotIn(str(absolute_fixture), output_text)
            self.assertNotIn("command", output_text)
            self.assertNotIn("stdout", output_text)
            self.assertNotIn("stderr", output_text)


if __name__ == "__main__":
    unittest.main()
