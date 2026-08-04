import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_support_tests.py"
SPEC = importlib.util.spec_from_file_location("run_support_tests", MODULE_PATH)
run_support_tests = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_support_tests)


class RunSupportTestsParserTests(unittest.TestCase):
    def test_wp_goal_parsing(self):
        self.assertEqual(
            run_support_tests.extract_wp_goals_from_text("[wp] Proved goals: 13 / 13"),
            "13/13",
        )

    def test_rte_goal_breakdown_parsing(self):
        text = """
[wp] [Qed] typed_entry_assert_rte_mem_access
[wp] [Timeout] typed_entry_assert_rte_index_bound (Alt-Ergo)
[wp] [Failure] typed_entry_assert_rte_signed_overflow (Alt-Ergo)
[wp] [Qed] typed_entry_assert_rte_float_to_int
[wp] [Qed] typed_entry_assert_rte_division_by_zero
"""
        breakdown = run_support_tests.extract_rte_goal_breakdown_from_text(text)
        self.assertEqual(breakdown["pointer_validity"], {"reported": 1, "proved": 1, "unproved": 0})
        self.assertEqual(breakdown["array_bounds"], {"reported": 1, "proved": 0, "unproved": 1})
        self.assertEqual(breakdown["integer_overflow"], {"reported": 2, "proved": 1, "unproved": 1})
        self.assertEqual(breakdown["floating_point"], {"reported": 1, "proved": 1, "unproved": 0})
        self.assertEqual(
            run_support_tests.extract_wp_goals_from_text("[wp] Proved goals: 6 / 8"),
            "6/8",
        )
        self.assertEqual(
            run_support_tests.extract_wp_goals_from_text("[wp] no summary was printed"),
            "-",
        )
        self.assertEqual(
            run_support_tests.extract_wp_goals_from_text(
                "[wp] [Timeout] typed_entry_requires\n[wp] Proved goals: 7 / 9"
            ),
            "7/9",
        )

    def test_tricera_syntax_error_detection(self):
        self.assertTrue(run_support_tests.detect_tricera_error("TriCera parser error: syntax error near token"))
        self.assertTrue(run_support_tests.detect_tricera_error("line 3:7 mismatched input '}' expecting ID"))
        self.assertTrue(
            run_support_tests.detect_tricera_error(
                'Parse Error: At line 295, near "predicate" :     Unrecoverable Syntax Error'
            )
        )
        self.assertTrue(
            run_support_tests.detect_tricera_error(
                'Syntax Error, trying to recover and continue parse... for input symbol ""\n'
                "Warning: The input program could not be parsed. If 'main' is not the entry point"
            )
        )
        self.assertTrue(
            run_support_tests.detect_tricera_error(
                "Horn Translation Error: read expects 21 argument(s), but got 20"
            )
        )
        self.assertFalse(run_support_tests.detect_tricera_error("Frama-C warning: user annotation was not proved"))

    def test_functional_backend_detects_horn_translation_error(self):
        evidence = run_support_tests.functional_backend_evidence(
            source_text="""int helper(int value) { return value; }
/*@ ensures \\result == value; */
int entry(int value) { return helper(value); }
""",
            entry_point="entry",
            tricera_result_present=True,
            tricera_result_text=(
                "Horn Translation Error: At (101:20)): read101_20(a, b, _res10) "
                "expects 3 argument(s), but got 2: a, b"
            ),
            func_stdout_text="",
            func_stderr_text="",
            expect_tricera_result=True,
        )

        self.assertEqual(evidence["functional_backend_status"], "translation_error")
        self.assertEqual(evidence["functional_backend_error_kind"], "horn_translation_arity_mismatch")
        self.assertIn("expects 3 argument", evidence["functional_backend_error_text"])
        self.assertIs(evidence["tricera_result_present"], True)

    def test_functional_backend_detects_parser_error(self):
        evidence = run_support_tests.functional_backend_evidence(
            source_text="int helper(int value) { return value; }\nint entry(int value) { return helper(value); }\n",
            entry_point="entry",
            tricera_result_present=True,
            tricera_result_text="line 1:3 mismatched input '}' expecting ID",
            func_stdout_text="",
            func_stderr_text="",
            expect_tricera_result=True,
        )

        self.assertEqual(evidence["functional_backend_status"], "parser_error")
        self.assertEqual(evidence["functional_backend_error_kind"], "tricera_parser_error")

    def test_functional_backend_detects_retained_result_parse_error(self):
        evidence = run_support_tests.functional_backend_evidence(
            source_text="int helper(int value) { return value; }\nint entry(int value) { return helper(value); }\n",
            entry_point="entry",
            tricera_result_present=True,
            tricera_result_text='Parse Error: At line 295, near "predicate" :     Unrecoverable Syntax Error',
            func_stdout_text="",
            func_stderr_text="",
            expect_tricera_result=True,
        )

        self.assertEqual(evidence["functional_backend_status"], "parser_error")
        self.assertEqual(evidence["functional_backend_error_kind"], "tricera_parser_error")
        self.assertIn("Parse Error", evidence["functional_backend_error_text"])

    def test_functional_backend_detects_saida_recovery_parse_error(self):
        evidence = run_support_tests.functional_backend_evidence(
            source_text="int helper(int value) { return value; }\nint entry(int value) { return helper(value); }\n",
            entry_point="entry",
            tricera_result_present=True,
            tricera_result_text="SAFE\n",
            func_stdout_text="",
            func_stderr_text=(
                'Syntax Error, trying to recover and continue parse... for input symbol ""\n'
                "Warning: The input program could not be parsed. If 'main' is not the entry point"
            ),
            expect_tricera_result=True,
        )

        self.assertEqual(evidence["functional_backend_status"], "parser_error")
        self.assertEqual(evidence["functional_backend_error_kind"], "tricera_parser_error")
        self.assertIn("Syntax Error", evidence["functional_backend_error_text"])

    def test_functional_backend_does_not_treat_plain_framac_warning_as_parser_error(self):
        evidence = run_support_tests.functional_backend_evidence(
            source_text="int helper(int value) { return value; }\nint entry(int value) { return helper(value); }\n",
            entry_point="entry",
            tricera_result_present=True,
            tricera_result_text="SAFE\n",
            func_stdout_text=(
                "[kernel:parser:decimal-float] case.c:3: Warning: "
                "Floating-point constant is not represented exactly."
            ),
            func_stderr_text="",
            expect_tricera_result=True,
        )

        self.assertEqual(evidence["functional_backend_status"], "missing_output")
        self.assertEqual(evidence["functional_backend_error_kind"], "no_expected_helper_contract_blocks")

    def test_functional_backend_detects_missing_result_file(self):
        evidence = run_support_tests.functional_backend_evidence(
            source_text="int helper(int value) { return value; }\nint entry(int value) { return helper(value); }\n",
            entry_point="entry",
            tricera_result_present=False,
            tricera_result_text="",
            func_stdout_text="",
            func_stderr_text="",
            expect_tricera_result=True,
        )

        self.assertEqual(evidence["functional_backend_status"], "missing_output")
        self.assertEqual(evidence["functional_backend_error_kind"], "missing_tricera_result")

    def test_functional_backend_detects_no_expected_contract_blocks(self):
        evidence = run_support_tests.functional_backend_evidence(
            source_text="""int helper(int value) { return value; }
/*@ ensures \\result == value; */
int entry(int value) { return helper(value); }
""",
            entry_point="entry",
            tricera_result_present=True,
            tricera_result_text="SAFE\n",
            func_stdout_text="",
            func_stderr_text="",
            expect_tricera_result=True,
        )

        self.assertEqual(evidence["functional_backend_status"], "missing_output")
        self.assertEqual(evidence["functional_backend_error_kind"], "no_expected_helper_contract_blocks")

    def test_functional_backend_allows_no_helpers_to_infer(self):
        evidence = run_support_tests.functional_backend_evidence(
            source_text="""/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return value;
}
""",
            entry_point="entry",
            tricera_result_present=True,
            tricera_result_text="SAFE\n",
            func_stdout_text="",
            func_stderr_text="",
            expect_tricera_result=True,
        )

        self.assertEqual(evidence["functional_backend_status"], "pass")
        self.assertIsNone(evidence["functional_backend_error_kind"])
        self.assertIsNone(evidence["functional_backend_error_text"])
        self.assertIs(evidence["tricera_result_present"], True)

    def test_inferred_helper_contract_detection(self):
        source = """int helper(int value)
{
    return value < 0 ? 0 : value;
}

/*@
  assigns \\nothing;
  ensures \\result >= 0;
*/
int entry(int value)
{
    return helper(value);
}
"""
        generated = """/*@
  assigns \\nothing;
  ensures \\result >= 0;
*/
int helper(int value)
{
    return value < 0 ? 0 : value;
}

/*@
  assigns \\nothing;
  ensures \\result >= 0;
*/
int entry(int value)
{
    return helper(value);
}
"""
        counts = run_support_tests.inspect_generated_inference(source, generated, "entry")
        self.assertEqual(counts["inferred_helper_contract_count"], 1)
        self.assertEqual(counts["missing_inferred_contract_count"], 0)
        self.assertEqual(counts["helper_function_count"], 1)
        self.assertEqual(counts["unannotated_helper_function_count"], 1)
        quality, reason = run_support_tests.inferred_contract_quality_value(
            saida_output_parse_status="pass",
            inferred_helper_contract_count=counts["inferred_helper_contract_count"],
            missing_inferred_contract_count=counts["missing_inferred_contract_count"],
            unannotated_helper_function_count=counts["unannotated_helper_function_count"],
            suspicious_contract_markers=[],
        )
        self.assertEqual(quality, "usable_candidate")
        self.assertIn("parsed", reason)

    def test_missing_inferred_contract_detection(self):
        source = """int helper(int value)
{
    return value;
}

/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
"""
        generated = """//No inferred contract found for helper
int helper(int value)
{
    return value;
}

/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
"""
        counts = run_support_tests.inspect_generated_inference(source, generated, "entry")
        self.assertEqual(counts["inferred_helper_contract_count"], 0)
        self.assertEqual(counts["missing_inferred_contract_count"], 1)
        quality, reason = run_support_tests.inferred_contract_quality_value(
            saida_output_parse_status="pass",
            inferred_helper_contract_count=counts["inferred_helper_contract_count"],
            missing_inferred_contract_count=counts["missing_inferred_contract_count"],
            unannotated_helper_function_count=1,
            suspicious_contract_markers=[],
        )
        self.assertEqual(quality, "missing")
        self.assertIn("missing-contract", reason)

    def test_malformed_inferred_output_quality(self):
        quality, reason = run_support_tests.inferred_contract_quality_value(
            saida_output_parse_status="fail",
            inferred_helper_contract_count=1,
            missing_inferred_contract_count=0,
            unannotated_helper_function_count=1,
            suspicious_contract_markers=[],
        )
        self.assertEqual(quality, "syntactically_invalid")
        self.assertIn("did not parse", reason)

    def test_requires_false_is_vacuous_candidate(self):
        generated = """/*@
  requires \\false;
  ensures \\result == value;
*/
int helper(int value)
{
    return value;
}
"""
        markers = run_support_tests.suspicious_contract_markers(generated)
        quality, reason = run_support_tests.inferred_contract_quality_value(
            saida_output_parse_status="pass",
            inferred_helper_contract_count=1,
            missing_inferred_contract_count=0,
            unannotated_helper_function_count=1,
            suspicious_contract_markers=markers,
        )
        self.assertEqual(markers, ["requires \\false;"])
        self.assertEqual(quality, "vacuous_candidate")
        self.assertIn("manual review", reason)

    def test_ensures_false_is_vacuous_candidate(self):
        generated = """/*@
  ensures \\false;
*/
int helper(int value)
{
    return value;
}
"""
        markers = run_support_tests.suspicious_contract_markers(generated)
        quality, reason = run_support_tests.inferred_contract_quality_value(
            saida_output_parse_status="pass",
            inferred_helper_contract_count=1,
            missing_inferred_contract_count=0,
            unannotated_helper_function_count=1,
            suspicious_contract_markers=markers,
        )
        self.assertEqual(markers, ["ensures \\false;"])
        self.assertEqual(quality, "vacuous_candidate")
        self.assertIn("manual review", reason)

    def test_saida_success_with_missing_marker_is_not_clean_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            source_path = repo_root / "case.c"
            source_path.write_text(
                """int helper(int value)
{
    return value;
}

/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
""",
                encoding="utf-8",
            )
            work_dir = repo_root / "out" / "case"
            (work_dir / "func").mkdir(parents=True)
            (work_dir / "func" / "stderr.txt").write_text("", encoding="utf-8")
            (work_dir / "tmp_inferred_source_merged.c").write_text(
                """//No inferred contract found for helper
int helper(int value)
{
    return value;
}
""",
                encoding="utf-8",
            )
            result = {"status": "pass", "returncode": 0}
            case = {"path": "case.c", "entry_point": "entry"}

            run_support_tests.enrich_saida_phase_result(result, case, repo_root, work_dir)

            self.assertEqual(result["saida_process_returncode"], 0)
            self.assertEqual(result["missing_inferred_contract_count"], 1)
            self.assertEqual(result["inferred_helper_contract_count"], 0)
            self.assertEqual(result["inference_evidence"], "missing_helper_contracts")
            self.assertEqual(result["inferred_contract_quality"], "missing")

    def test_saida_success_with_horn_error_is_backend_translation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            source_path = repo_root / "case.c"
            source_path.write_text(
                """int helper(int value)
{
    return value;
}

/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
""",
                encoding="utf-8",
            )
            work_dir = repo_root / "out" / "case"
            (work_dir / "func").mkdir(parents=True)
            (work_dir / "func" / "stdout.txt").write_text("", encoding="utf-8")
            (work_dir / "func" / "stderr.txt").write_text("", encoding="utf-8")
            (work_dir / "saida_result_case.c").write_text(
                "Horn Translation Error: helper expects 21 argument(s), but got 20\n",
                encoding="utf-8",
            )
            (work_dir / "tmp_inferred_source_merged.c").write_text(
                """//No inferred contract found for helper
int helper(int value)
{
    return value;
}
""",
                encoding="utf-8",
            )
            result = {"status": "pass", "returncode": 0}
            case = {"path": "case.c", "entry_point": "entry"}

            run_support_tests.enrich_saida_phase_result(result, case, repo_root, work_dir)

            self.assertEqual(result["saida_process_returncode"], 0)
            self.assertEqual(result["functional_backend_status"], "translation_error")
            self.assertEqual(result["functional_backend_error_kind"], "horn_translation_arity_mismatch")
            self.assertTrue(result["tricera_error_detected"])
            self.assertTrue(result["tricera_result_present"])
            self.assertEqual(result["inference_evidence"], "tricera_error")


class RunSupportTestsClassificationTests(unittest.TestCase):
    def observed(self, phases, **overrides):
        item = {
            "id": "case",
            "kind": "micro_helper_inference",
            "lib_entry": True,
            "inference_evidence": "inferred_helpers",
            "inferred_helper_contract_count": 1,
            "missing_inferred_contract_count": 0,
            "unannotated_helper_function_count": 1,
            "functional_backend_status": "pass",
            "saida_output_parse_status": "pass",
            "inferred_contract_quality": "usable_candidate",
            "phases": phases,
        }
        item.update(overrides)
        return run_support_tests.observed_cell(item, Path("/unused"))

    def test_classification_supported_end_to_end(self):
        self.assertEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "pass"},
                    "wp": {"status": "pass", "wp_goals": "4/4"},
                }
            ),
            "supported_end_to_end",
        )

    def test_positive_support_gate_rejects_suspicious_contracts(self):
        self.assertNotEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "pass"},
                    "wp": {"status": "pass", "wp_goals": "4/4"},
                },
                inferred_contract_quality="vacuous_candidate",
                suspicious_contract_markers=["ensures \\false;"],
            ),
            "supported_end_to_end",
        )

    def test_positive_support_gate_rejects_backend_translation_error(self):
        self.assertNotEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "pass"},
                    "wp": {"status": "pass", "wp_goals": "4/4"},
                },
                functional_backend_status="translation_error",
                functional_backend_error_kind="horn_translation_arity_mismatch",
            ),
            "supported_end_to_end",
        )

    def test_backend_parser_error_is_failed_at_func(self):
        self.assertEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "pass"},
                    "wp": {"status": "pass", "wp_goals": "4/4"},
                },
                functional_backend_status="parser_error",
                functional_backend_error_kind="tricera_parser_error",
            ),
            "failed_at_func",
        )

    def test_missing_helper_contract_is_failed_at_func_even_if_wp_passes(self):
        self.assertEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "pass"},
                    "wp": {"status": "pass", "wp_goals": "4/4"},
                },
                inference_evidence="missing_helper_contracts",
                inferred_helper_contract_count=0,
                missing_inferred_contract_count=1,
                inferred_contract_quality="missing",
                functional_backend_status="missing_output",
                functional_backend_error_kind="no_expected_helper_contract_blocks",
            ),
            "failed_at_func",
        )

    def test_wp_pass_without_goal_summary_is_not_supported(self):
        self.assertNotEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "pass"},
                    "wp": {"status": "pass"},
                }
            ),
            "supported_end_to_end",
        )

    def test_wp_zero_of_zero_is_not_supported(self):
        self.assertNotEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "pass"},
                    "wp": {"status": "pass", "wp_goals": "0/0"},
                }
            ),
            "supported_end_to_end",
        )

    def test_persisted_classification_supported_end_to_end(self):
        item = {
            "id": "case",
            "kind": "micro_helper_inference",
            "expected_support": "supported",
            "lib_entry": True,
            "inference_evidence": "inferred_helpers",
            "inferred_helper_contract_count": 1,
            "missing_inferred_contract_count": 0,
            "unannotated_helper_function_count": 1,
            "functional_backend_status": "pass",
            "saida_output_parse_status": "pass",
            "inferred_contract_quality": "usable_candidate",
            "phases": {
                "frama_parse": {"status": "pass"},
                "func": {"status": "pass"},
                "aux": {"status": "pass"},
                "wp": {"status": "pass", "wp_goals": "4/4"},
            },
        }
        run_support_tests.persist_classification_fields(item, Path("/unused"))
        self.assertEqual(item["observed"], "supported_end_to_end")
        self.assertEqual(item["conclusion"], "supported_end_to_end")
        self.assertEqual(item["wp_goals"], "4/4")
        self.assertEqual(item["phase_statuses"]["wp"], "pass")

    def test_classification_failed_at_parse(self):
        self.assertEqual(self.observed({"frama_parse": {"status": "fail"}}), "failed_at_parse")

    def test_classification_failed_at_func(self):
        self.assertEqual(
            self.observed({"frama_parse": {"status": "pass"}, "func": {"status": "fail"}}),
            "failed_at_func",
        )

    def test_classification_failed_at_aux(self):
        self.assertEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "fail"},
                }
            ),
            "failed_at_aux",
        )

    def test_classification_failed_at_wp(self):
        self.assertEqual(
            self.observed(
                {
                    "frama_parse": {"status": "pass"},
                    "func": {"status": "pass"},
                    "aux": {"status": "pass"},
                    "wp": {"status": "pass", "wp_goals": "3/4"},
                }
            ),
            "failed_at_wp",
        )

    def test_rte_result_does_not_change_functional_observed(self):
        item = {
            "id": "case",
            "kind": "micro_helper_inference",
            "lib_entry": True,
            "inference_evidence": "inferred_helpers",
            "inferred_helper_contract_count": 1,
            "missing_inferred_contract_count": 0,
            "unannotated_helper_function_count": 1,
            "functional_backend_status": "pass",
            "saida_output_parse_status": "pass",
            "inferred_contract_quality": "usable_candidate",
            "phases": {
                "frama_parse": {"status": "pass"},
                "func": {"status": "pass"},
                "aux": {"status": "pass"},
                "wp": {"status": "pass", "wp_goals": "4/4"},
                "rte_wp": {"status": "pass", "rte_wp_goals": "3/5"},
            },
        }
        run_support_tests.persist_classification_fields(item, Path("/unused"))
        self.assertEqual(item["observed"], "supported_end_to_end")
        self.assertEqual(item["functional_wp_goals"], "4/4")
        self.assertEqual(item["rte_wp_goals"], "3/5")
        self.assertEqual(item["rte_result"], "failed_at_rte_wp_goals")

    def test_persisted_classification_partial_wp_goals(self):
        item = {
            "id": "case",
            "kind": "micro_helper_inference",
            "expected_support": "supported",
            "lib_entry": True,
            "inference_evidence": "inferred_helpers",
            "inferred_helper_contract_count": 1,
            "missing_inferred_contract_count": 0,
            "unannotated_helper_function_count": 1,
            "functional_backend_status": "pass",
            "saida_output_parse_status": "pass",
            "inferred_contract_quality": "usable_candidate",
            "phases": {
                "frama_parse": {"status": "pass"},
                "func": {"status": "pass"},
                "aux": {"status": "pass"},
                "wp": {"status": "pass", "wp_goals": "3/4"},
            },
        }
        run_support_tests.persist_classification_fields(item, Path("/unused"))
        self.assertEqual(item["observed"], "failed_at_wp")
        self.assertEqual(item["conclusion"], "failed_at_wp")
        self.assertEqual(item["wp_goals"], "3/4")

    def test_horn_translation_error_sets_evidence_failed_stage(self):
        item = {
            "id": "case",
            "kind": "micro_helper_inference",
            "expected_support": "supported",
            "lib_entry": True,
            "inference_evidence": "tricera_error",
            "inferred_helper_contract_count": 0,
            "missing_inferred_contract_count": 0,
            "unannotated_helper_function_count": 1,
            "functional_backend_status": "translation_error",
            "functional_backend_error_kind": "horn_translation_arity_mismatch",
            "functional_backend_error_text": "Horn Translation Error: expects 21 argument(s), but got 20",
            "saida_output_parse_status": "pass",
            "inferred_contract_quality": "missing",
            "phases": {
                "frama_parse": {"status": "pass"},
                "func": {"status": "pass"},
                "aux": {"status": "unknown"},
                "wp": {"status": "unknown"},
            },
        }

        run_support_tests.persist_classification_fields(item, Path("/unused"))

        self.assertEqual(item["process_first_failed_stage"], "-")
        self.assertEqual(item["evidence_first_failed_stage"], "func_backend_translation")

    def test_parser_error_sets_evidence_failed_stage(self):
        item = {
            "id": "case",
            "kind": "micro_helper_inference",
            "expected_support": "supported",
            "lib_entry": True,
            "inference_evidence": "tricera_error",
            "inferred_helper_contract_count": 0,
            "missing_inferred_contract_count": 0,
            "unannotated_helper_function_count": 1,
            "functional_backend_status": "parser_error",
            "functional_backend_error_kind": "tricera_parser_error",
            "functional_backend_error_text": 'Parse Error: At line 1, near "predicate"',
            "saida_output_parse_status": "pass",
            "inferred_contract_quality": "missing",
            "phases": {
                "frama_parse": {"status": "pass"},
                "func": {"status": "pass"},
                "aux": {"status": "unknown"},
                "wp": {"status": "unknown"},
            },
        }

        run_support_tests.persist_classification_fields(item, Path("/unused"))

        self.assertEqual(item["process_first_failed_stage"], "-")
        self.assertEqual(item["evidence_first_failed_stage"], "func_backend_parser")


class RunSupportTestsSelectionTests(unittest.TestCase):
    def test_baseline_group_selects_matching_cases(self):
        cases = [
            {"id": "academic", "module": "micro", "kind": "micro_helper_inference", "baseline_group": "academic_functional_v1"},
            {
                "id": "academic-v2",
                "module": "micro",
                "kind": "micro_helper_inference",
                "baseline_groups": ["academic_functional_v2"],
            },
            {"id": "control", "module": "micro", "kind": "micro_entry_control"},
        ]

        selected = run_support_tests.selected_cases(
            cases,
            ids=None,
            modules=None,
            kinds=None,
            exclude_kinds=None,
            baseline_groups=["academic_functional_v1"],
        )

        self.assertEqual([case["id"] for case in selected], ["academic"])

        selected_v2 = run_support_tests.selected_cases(
            cases,
            ids=None,
            modules=None,
            kinds=None,
            exclude_kinds=None,
            baseline_groups=["academic_functional_v2"],
        )

        self.assertEqual([case["id"] for case in selected_v2], ["academic-v2"])

    def test_case_selection_still_works_without_baseline_group(self):
        cases = [
            {"id": "academic", "module": "micro", "kind": "micro_helper_inference", "baseline_group": "academic_functional_v1"},
            {"id": "control", "module": "micro", "kind": "micro_entry_control"},
        ]

        selected = run_support_tests.selected_cases(
            cases,
            ids=["control"],
            modules=None,
            kinds=None,
            exclude_kinds=None,
            baseline_groups=None,
        )

        self.assertEqual([case["id"] for case in selected], ["control"])


class RunSupportTestsFreshRunTests(unittest.TestCase):
    def write_case_files(self, repo_root):
        source_path = repo_root / "case.c"
        source_path.write_text(
            """int helper(int value)
{
    return value;
}

/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
""",
            encoding="utf-8",
        )
        cases_path = repo_root / "cases.json"
        cases_path.write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            "id": "case",
                            "module": "micro",
                            "kind": "micro_helper_inference",
                            "path": "case.c",
                            "entry_point": "entry",
                            "description": "unit test case",
                            "expected_support": "supported",
                            "probe_role": "helper_inference",
                            "evidence_tier": "tier_1_helper_inference",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return cases_path

    def write_module_smoke_case_files(self, repo_root):
        for source_name in ("mini.c", "sample_module.c"):
            (repo_root / source_name).write_text(
                """int helper(int value)
{
    return value;
}

/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
""",
                encoding="utf-8",
            )
        cases_path = repo_root / "cases.json"
        cases_path.write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            "id": "sample_module_a",
                            "module": "sample-module-a",
                            "kind": "self_contained_verified_variant",
                            "path": "mini.c",
                            "entry_point": "entry",
                            "description": "unit module smoke case",
                            "evidence_tier": "tier_4_real_module_smoke_evidence",
                            "evidence_role": "module_smoke_evidence",
                            "baseline_group": "internal_module_smoke_v1",
                            "helper_inference_claim": "none",
                            "paper_model_input_classification": "module_smoke_only",
                        },
                        {
                            "id": "sample_module_b",
                            "module": "SAMPLE_MODULE",
                            "kind": "sample_module_anonymized",
                            "path": "sample_module.c",
                            "entry_point": "entry",
                            "description": "unit internal SAMPLE_MODULE smoke case",
                            "evidence_tier": "tier_4_real_module_smoke_evidence",
                            "evidence_role": "module_smoke_evidence",
                            "baseline_group": "internal_module_smoke_v1",
                            "helper_inference_claim": "none",
                            "paper_model_input_classification": "module_smoke_only",
                            "source_visibility": "internal",
                            "public_export": False,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        return cases_path

    def fake_successful_split_phase(self, phase, case, repo_root_arg, work_dir, *args):
        if phase == "func":
            (work_dir / "func").mkdir(parents=True, exist_ok=True)
            (work_dir / "func" / "stderr.txt").write_text("", encoding="utf-8")
            (work_dir / "func" / "stdout.txt").write_text("", encoding="utf-8")
            generated = work_dir / "tmp_inferred_source_merged.c"
            generated.write_text(
                """/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int helper(int value)
{
    return value;
}

/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
""",
                encoding="utf-8",
            )
            (work_dir / "saida_result_case.c").write_text(
                """Inferred ACSL annotations
/* contract for helper */
/*@
  assigns \\nothing;
  ensures \\result == value;
*/
SAFE
""",
                encoding="utf-8",
            )
            return {
                "status": "pass",
                "returncode": 0,
                "generated_files": [str(generated)],
                "saida_output_parse_status": "pass",
                "functional_backend_status": "pass",
                "tricera_result_present": True,
            }
        if phase == "aux":
            out_c = work_dir / "out.c"
            out_c.write_text("int helper(int value) { return value; }\n", encoding="utf-8")
            return {"status": "pass", "returncode": 0, "generated_files": [str(out_c)]}
        if phase == "wp":
            return {"status": "pass", "returncode": 0, "wp_goals": "4/4", "generated_files": []}
        return {"status": "pass", "returncode": 0, "generated_files": []}

    def test_lib_entry_commands_include_flag_in_all_canonical_phases(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_case_files(repo_root)
            case = {
                "id": "case",
                "path": "case.c",
                "entry_point": "entry",
            }
            work_dir = repo_root / "results" / "case"
            work_dir.mkdir(parents=True)
            commands = {}

            def fake_run_command(command, cwd, timeout, stdout_path, stderr_path, exit_code_path):
                phase = "func" if "-saida" in command else "aux" if "-isp" in command else "wp" if "-wp" in command else "frama_parse"
                commands[phase] = command
                stdout_path.write_text("[wp] Proved goals: 4 / 4\n" if phase == "wp" else "", encoding="utf-8")
                stderr_path.write_text("", encoding="utf-8")
                exit_code_path.write_text("0\n", encoding="utf-8")
                if phase == "func":
                    (cwd / "tmp_inferred_source_merged.c").write_text("int helper(int value) { return value; }\n", encoding="utf-8")
                    (cwd / "saida_result_case.c").write_text(
                        """/* contract for helper */
/*@
  assigns \\nothing;
  ensures \\result == value;
*/
SAFE
""",
                        encoding="utf-8",
                    )
                if phase == "aux":
                    (cwd / "out.c").write_text("int helper(int value) { return value; }\n", encoding="utf-8")
                return {"status": "pass", "returncode": 0, "command": command}

            with (
                mock.patch.object(run_support_tests, "executable", return_value="frama-c"),
                mock.patch.object(run_support_tests, "run_command", side_effect=fake_run_command),
            ):
                for phase in ("frama_parse", "func", "aux", "wp"):
                    run_support_tests.run_tool_phase(
                        phase,
                        case,
                        repo_root,
                        work_dir,
                        None,
                        600,
                        True,
                    )

            for phase in ("frama_parse", "func", "aux", "wp"):
                self.assertIn("-lib-entry", commands[phase], phase)
            self.assertEqual(commands["frama_parse"][0:5], ["frama-c", "-quiet", "-main", "entry", "-lib-entry"])
            self.assertEqual(commands["func"][0:5], ["frama-c", "-saida", "-main", "entry", "-lib-entry"])
            self.assertIn("-saida-keep-tmp", commands["func"])
            self.assertEqual(commands["aux"][0:5], ["frama-c", "-isp", "-main", "entry", "-lib-entry"])
            self.assertEqual(commands["wp"][0:5], ["frama-c", "-wp", "-main", "entry", "-lib-entry"])

    def test_func_phase_copy_preserves_local_include_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            source_dir = repo_root / "src"
            source_dir.mkdir()
            (source_dir / "local.h").write_text("#define IDENTITY_VALUE(value) (value)\n", encoding="utf-8")
            (source_dir / "case.c").write_text(
                """#include "local.h"

int helper(int value)
{
    return IDENTITY_VALUE(value);
}

/*@ ensures \\result == value; */
int entry(int value)
{
    return helper(value);
}
""",
                encoding="utf-8",
            )
            case = {
                "id": "case",
                "path": "src/case.c",
                "entry_point": "entry",
            }
            work_dir = repo_root / "results" / "case"
            work_dir.mkdir(parents=True)
            commands = []

            def fake_run_command(command, cwd, timeout, stdout_path, stderr_path, exit_code_path):
                commands.append(command)
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text("", encoding="utf-8")
                exit_code_path.write_text("0\n", encoding="utf-8")
                if "-saida" in command:
                    (cwd / "tmp_inferred_source_merged.c").write_text(
                        """/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int helper(int value)
{
    return value;
}

/*@ ensures \\result == value; */
int entry(int value)
{
    return helper(value);
}
""",
                        encoding="utf-8",
                    )
                    (cwd / "saida_result_case.c").write_text(
                        """/* contract for helper */
/*@
  assigns \\nothing;
  ensures \\result == value;
*/
SAFE
""",
                        encoding="utf-8",
                    )
                return {"status": "pass", "returncode": 0, "command": command}

            with (
                mock.patch.object(run_support_tests, "executable", return_value="frama-c"),
                mock.patch.object(run_support_tests, "run_command", side_effect=fake_run_command),
            ):
                result = run_support_tests.run_tool_phase(
                    "func",
                    case,
                    repo_root,
                    work_dir,
                    None,
                    600,
                    True,
                )

            saida_command = commands[0]
            self.assertIn("-saida-keep-tmp", saida_command)
            self.assertEqual(saida_command[-1], "case.c")
            self.assertTrue((work_dir / "case.c").exists())
            self.assertTrue(
                any(str(source_dir.resolve()) in argument for argument in saida_command),
                saida_command,
            )
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["functional_backend_status"], "pass")

    def test_func_phase_includes_case_tricera_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_case_files(repo_root)
            case = {
                "id": "case",
                "path": "case.c",
                "entry_point": "entry",
                "saida_tricera_opts": "-cpp -acsl",
            }
            work_dir = repo_root / "results" / "case"
            commands = []

            def fake_run_command(command, cwd, timeout, stdout_path, stderr_path, exit_code_path):
                commands.append(command)
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text("", encoding="utf-8")
                exit_code_path.write_text("0\n", encoding="utf-8")
                (cwd / "tmp_inferred_source_merged.c").write_text(
                    """/*@ ensures \\result == value; */
int helper(int value) { return value; }
/*@ ensures \\result == value; */
int entry(int value) { return helper(value); }
""",
                    encoding="utf-8",
                )
                (cwd / "saida_result_case.c").write_text(
                    """/* contract for helper */
/*@ ensures \\result == value; */
SAFE
""",
                    encoding="utf-8",
                )
                return {"status": "pass", "returncode": 0, "command": command}

            with (
                mock.patch.object(run_support_tests, "executable", return_value="frama-c"),
                mock.patch.object(run_support_tests, "run_command", side_effect=fake_run_command),
            ):
                run_support_tests.run_tool_phase("func", case, repo_root, work_dir, None, 600, True)

            self.assertIn("-saida-tricera-opts=-cpp -acsl", commands[0])

    def test_func_phase_parses_generated_saida_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_case_files(repo_root)
            case = {
                "id": "case",
                "path": "case.c",
                "entry_point": "entry",
            }
            work_dir = repo_root / "results" / "case"
            work_dir.mkdir(parents=True)
            commands = []

            def fake_run_command(command, cwd, timeout, stdout_path, stderr_path, exit_code_path):
                commands.append(command)
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text("", encoding="utf-8")
                exit_code_path.write_text("0\n", encoding="utf-8")
                if "-saida" in command:
                    (cwd / "tmp_inferred_source_merged.c").write_text(
                        """/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int helper(int value)
{
    return value;
}

/*@
  assigns \\nothing;
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
""",
                        encoding="utf-8",
                    )
                    (cwd / "saida_result_case.c").write_text(
                        """/* contract for helper */
/*@
  assigns \\nothing;
  ensures \\result == value;
*/
SAFE
""",
                        encoding="utf-8",
                    )
                return {"status": "pass", "returncode": 0, "command": command}

            with (
                mock.patch.object(run_support_tests, "executable", return_value="frama-c"),
                mock.patch.object(run_support_tests, "run_command", side_effect=fake_run_command),
            ):
                result = run_support_tests.run_tool_phase(
                    "func",
                    case,
                    repo_root,
                    work_dir,
                    None,
                    600,
                    True,
                )

            self.assertEqual(len(commands), 2)
            self.assertIn("-saida", commands[0])
            self.assertEqual(commands[1][0:5], ["frama-c", "-quiet", "-main", "entry", "-lib-entry"])
            self.assertEqual(commands[1][-1], "tmp_inferred_source_merged.c")
            self.assertEqual(result["saida_output_parse_status"], "pass")
            self.assertEqual(result["inferred_contract_quality"], "usable_candidate")

    def test_rte_wp_command_is_separate_from_functional_wp(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self.write_case_files(repo_root)
            case = {
                "id": "case",
                "path": "case.c",
                "entry_point": "entry",
            }
            work_dir = repo_root / "results" / "case"
            work_dir.mkdir(parents=True)
            (work_dir / "out.c").write_text("int entry(int value) { return value; }\n", encoding="utf-8")

            def fake_run_command(command, cwd, timeout, stdout_path, stderr_path, exit_code_path):
                stdout_path.write_text(
                    "[wp] [Qed] typed_entry_assert_rte_signed_overflow\n"
                    "[wp] Proved goals: 1 / 1\n",
                    encoding="utf-8",
                )
                stderr_path.write_text("", encoding="utf-8")
                exit_code_path.write_text("0\n", encoding="utf-8")
                return {"status": "pass", "returncode": 0, "command": command}

            with (
                mock.patch.object(run_support_tests, "executable", return_value="frama-c"),
                mock.patch.object(run_support_tests, "run_command", side_effect=fake_run_command),
            ):
                result = run_support_tests.run_tool_phase(
                    "rte_wp",
                    case,
                    repo_root,
                    work_dir,
                    None,
                    600,
                    True,
                )

            self.assertEqual(result["command"][0:3], ["frama-c", "-wp", "-wp-rte"])
            self.assertIn("-lib-entry", result["command"])
            self.assertEqual(result["command"][-1], "out.c")
            self.assertEqual(result["rte_wp_goals"], "1/1")
            self.assertEqual(
                result["rte_goal_breakdown"]["integer_overflow"],
                {"reported": 1, "proved": 1, "unproved": 0},
            )

    def test_selected_fresh_run_does_not_merge_old_phase_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            cases_path = self.write_case_files(repo_root)
            old_case_out = repo_root / "results" / "case"
            old_case_out.mkdir(parents=True)
            (old_case_out / "result.json").write_text(
                json.dumps(
                    {
                        "phases": {
                            "func": {"status": "pass"},
                            "aux": {"status": "pass"},
                            "wp": {"status": "pass", "wp_goals": "1/1"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_tool_phase(phase, *args, **kwargs):
                self.assertEqual(phase, "frama_parse")
                return {"status": "pass", "returncode": 0, "generated_files": []}

            with mock.patch.object(run_support_tests, "run_tool_phase", side_effect=fake_run_tool_phase):
                exit_code = run_support_tests.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--cases",
                        str(cases_path),
                        "--out",
                        "results",
                        "--case",
                        "case",
                        "--run-framac",
                    ]
                )

            self.assertEqual(exit_code, 0)
            result = json.loads((old_case_out / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(result["phases"]), ["frama_parse"])
            self.assertEqual(result["observed"], "parse_only")

            aggregate = json.loads((repo_root / "results" / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(aggregate[0]["phases"]), ["frama_parse"])
            self.assertEqual(aggregate[0]["observed"], "parse_only")

    def test_selected_fresh_summary_contains_only_selected_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            cases_path = self.write_case_files(repo_root)
            data = json.loads(cases_path.read_text(encoding="utf-8"))
            second_source = repo_root / "other.c"
            second_source.write_text(
                """/*@
  assigns \\nothing;
  ensures \\result == 1;
*/
int entry(void)
{
    return 1;
}
""",
                encoding="utf-8",
            )
            data["cases"].append(
                {
                    "id": "other",
                    "module": "micro",
                    "kind": "micro_entry_control",
                    "path": "other.c",
                    "entry_point": "entry",
                    "description": "unselected unit test case",
                    "expected_support": "supported",
                    "probe_role": "entry_pipeline_control",
                    "evidence_tier": "tier_2_entry_pipeline_control",
                }
            )
            cases_path.write_text(json.dumps(data), encoding="utf-8")
            out_dir = repo_root / "results"

            def fake_run_tool_phase(phase, *args, **kwargs):
                return {"status": "pass", "returncode": 0, "generated_files": []}

            with mock.patch.object(run_support_tests, "run_tool_phase", side_effect=fake_run_tool_phase):
                exit_code = run_support_tests.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--cases",
                        str(cases_path),
                        "--out",
                        "results",
                        "--case",
                        "case",
                        "--run-framac",
                    ]
                )

            self.assertEqual(exit_code, 0)
            aggregate = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            summary = (out_dir / "summary.md").read_text(encoding="utf-8")
            self.assertEqual([item["id"] for item in aggregate], ["case"])
            self.assertIn("| case | micro |", summary)
            self.assertNotIn("| other | micro |", summary)

    def test_main_persists_classification_to_case_aggregate_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            cases_path = self.write_case_files(repo_root)
            out_dir = repo_root / "results"
            old_case_out = out_dir / "case"
            old_case_out.mkdir(parents=True)
            (old_case_out / "result.json").write_text(
                json.dumps({"lib_entry": False, "phases": {"wp": {"status": "pass", "wp_goals": "1/1"}}}),
                encoding="utf-8",
            )

            def fake_run_tool_phase(phase, case, repo_root_arg, work_dir, *args):
                self.assertTrue(args[-1])
                return self.fake_successful_split_phase(phase, case, repo_root_arg, work_dir, *args)

            with mock.patch.object(run_support_tests, "run_tool_phase", side_effect=fake_run_tool_phase):
                exit_code = run_support_tests.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--cases",
                        str(cases_path),
                        "--out",
                        "results",
                        "--case",
                        "case",
                        "--run-framac",
                        "--run-split",
                        "--lib-entry",
                    ]
                )

            self.assertEqual(exit_code, 0)
            result = json.loads((out_dir / "case" / "result.json").read_text(encoding="utf-8"))
            aggregate = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            summary = (out_dir / "summary.md").read_text(encoding="utf-8")

            self.assertEqual(result["observed"], "supported_end_to_end")
            self.assertEqual(result["conclusion"], "supported_end_to_end")
            self.assertIs(result["lib_entry"], True)
            self.assertEqual(result["wp_goals"], "4/4")
            self.assertEqual(result["phase_statuses"]["wp"], "pass")
            self.assertEqual(aggregate[0]["observed"], result["observed"])
            self.assertEqual(aggregate[0]["conclusion"], result["conclusion"])
            self.assertIs(aggregate[0]["lib_entry"], True)
            self.assertIn("| case | micro | micro_helper_inference | helper_inference | supported | supported_end_to_end |", summary)
            self.assertIn("| 4/4 | - | - | not_run | supported_end_to_end |", summary)

    def test_fresh_module_smoke_metadata_persisted_to_case_and_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            cases_path = self.write_module_smoke_case_files(repo_root)
            out_dir = repo_root / "results"

            def fake_run_tool_phase(phase, *args, **kwargs):
                self.assertEqual(phase, "frama_parse")
                return {"status": "pass", "returncode": 0, "generated_files": []}

            with mock.patch.object(run_support_tests, "run_tool_phase", side_effect=fake_run_tool_phase):
                exit_code = run_support_tests.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--cases",
                        str(cases_path),
                        "--out",
                        "results",
                        "--run-framac",
                        "--baseline-group",
                        "internal_module_smoke_v1",
                    ]
                )

            self.assertEqual(exit_code, 0)
            aggregate = {
                item["id"]: item
                for item in json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            }
            self.assertEqual(set(aggregate), {"sample_module_a", "sample_module_b"})

            for case_id in aggregate:
                result = json.loads((out_dir / case_id / "result.json").read_text(encoding="utf-8"))
                self.assertEqual(result["evidence_role"], "module_smoke_evidence")
                self.assertEqual(result["baseline_group"], "internal_module_smoke_v1")
                self.assertEqual(result["helper_inference_claim"], "none")
                self.assertEqual(result["paper_model_input_classification"], "module_smoke_only")
                self.assertEqual(aggregate[case_id]["helper_inference_claim"], "none")
                self.assertEqual(aggregate[case_id]["paper_model_input_classification"], "module_smoke_only")

            self.assertEqual(aggregate["sample_module_b"]["source_visibility"], "internal")
            self.assertIs(aggregate["sample_module_b"]["public_export"], False)

    def test_merge_run_uses_manifest_metadata_over_stale_result_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            cases_path = self.write_module_smoke_case_files(repo_root)
            out_dir = repo_root / "results"
            case_out = out_dir / "sample_module_b"
            case_out.mkdir(parents=True)
            (case_out / "result.json").write_text(
                json.dumps(
                    {
                        "helper_inference_claim": None,
                        "paper_model_input_classification": None,
                        "source_visibility": "stale-public",
                        "public_export": True,
                        "phases": {"frama_parse": {"status": "pass"}},
                    }
                ),
                encoding="utf-8",
            )

            exit_code = run_support_tests.main(
                [
                    "--repo-root",
                    str(repo_root),
                    "--cases",
                    str(cases_path),
                    "--out",
                    "results",
                    "--case",
                    "sample_module_b",
                ]
            )

            self.assertEqual(exit_code, 0)
            result = json.loads((case_out / "result.json").read_text(encoding="utf-8"))
            aggregate = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))[0]
            for item in (result, aggregate):
                self.assertEqual(item["helper_inference_claim"], "none")
                self.assertEqual(item["paper_model_input_classification"], "module_smoke_only")
                self.assertEqual(item["source_visibility"], "internal")
                self.assertIs(item["public_export"], False)

    def test_main_persists_rte_profile_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            cases_path = self.write_case_files(repo_root)
            out_dir = repo_root / "results"

            def fake_run_tool_phase(phase, case, repo_root_arg, work_dir, *args):
                if phase == "rte_wp":
                    return {
                        "status": "pass",
                        "returncode": 0,
                        "rte_wp_goals": "1/2",
                        "rte_goal_breakdown": {
                            "pointer_validity": {"reported": 0, "proved": 0, "unproved": 0},
                            "array_bounds": {"reported": 0, "proved": 0, "unproved": 0},
                            "integer_overflow": {"reported": 1, "proved": 0, "unproved": 1},
                            "floating_point": {"reported": 0, "proved": 0, "unproved": 0},
                            "other_rte": {"reported": 0, "proved": 0, "unproved": 0},
                        },
                        "generated_files": [],
                    }
                return self.fake_successful_split_phase(phase, case, repo_root_arg, work_dir, *args)

            with mock.patch.object(run_support_tests, "run_tool_phase", side_effect=fake_run_tool_phase):
                exit_code = run_support_tests.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--cases",
                        str(cases_path),
                        "--out",
                        "results",
                        "--case",
                        "case",
                        "--run-framac",
                        "--run-split",
                        "--run-rte-wp",
                        "--lib-entry",
                    ]
                )

            self.assertEqual(exit_code, 0)
            result = json.loads((out_dir / "case" / "result.json").read_text(encoding="utf-8"))
            aggregate = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(result["observed"], "supported_end_to_end")
            self.assertEqual(result["functional_wp_goals"], "4/4")
            self.assertEqual(result["rte_wp_goals"], "1/2")
            self.assertEqual(result["rte_result"], "failed_at_rte_wp_goals")
            self.assertEqual(result["rte_goal_breakdown"]["integer_overflow"]["unproved"], 1)
            self.assertEqual(aggregate[0]["rte_wp_goals"], "1/2")
            self.assertEqual(aggregate[0]["phase_statuses"]["rte_wp"], "pass")

    def test_non_lib_entry_fresh_run_persists_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            cases_path = self.write_case_files(repo_root)
            out_dir = repo_root / "results"

            with mock.patch.object(run_support_tests, "run_tool_phase", side_effect=self.fake_successful_split_phase):
                exit_code = run_support_tests.main(
                    [
                        "--repo-root",
                        str(repo_root),
                        "--cases",
                        str(cases_path),
                        "--out",
                        "results",
                        "--case",
                        "case",
                        "--run-framac",
                        "--run-split",
                    ]
                )

            self.assertEqual(exit_code, 0)
            result = json.loads((out_dir / "case" / "result.json").read_text(encoding="utf-8"))
            aggregate = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            self.assertIs(result["lib_entry"], False)
            self.assertIs(aggregate[0]["lib_entry"], False)

    def test_merge_without_phase_run_preserves_existing_lib_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            cases_path = self.write_case_files(repo_root)
            out_dir = repo_root / "results"
            case_out = out_dir / "case"
            case_out.mkdir(parents=True)
            (case_out / "result.json").write_text(
                json.dumps(
                    {
                        "lib_entry": True,
                        "phases": {
                            "frama_parse": {"status": "pass"},
                            "func": {"status": "pass"},
                            "aux": {"status": "pass"},
                            "wp": {"status": "pass", "wp_goals": "4/4"},
                        },
                    }
                ),
                encoding="utf-8",
            )

            exit_code = run_support_tests.main(
                [
                    "--repo-root",
                    str(repo_root),
                    "--cases",
                    str(cases_path),
                    "--out",
                    "results",
                    "--case",
                    "case",
                ]
            )

            self.assertEqual(exit_code, 0)
            result = json.loads((case_out / "result.json").read_text(encoding="utf-8"))
            aggregate = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))
            self.assertIs(result["lib_entry"], True)
            self.assertIs(aggregate[0]["lib_entry"], True)


class RunSupportTestsManifestTests(unittest.TestCase):
    P0_CASES = {
        "helper_stack_pointer",
        "helper_two_level_call_chain",
        "helper_multiple_call_contexts",
        "contract_logic_function_helper",
        "contract_behavior_helper",
        "contract_predicate_helper",
    }
    P1_CASES = {
        "helper_struct_return_whole",
        "helper_enum_indexed_array_struct_return",
        "helper_array_struct_output_parameter_rewrite",
        "helper_int_indexed_array_struct_return",
        "helper_int_indexed_array_scalar_return",
    }
    BACKEND_BOUNDARY_CASES = set()
    BACKEND_REWRITE_CASES = {}
    FINAL_REWRITE_CASES = {
        "helper_stack_pointer_return_value_rewrite": "helper_stack_pointer",
        "contract_logic_inline_rewrite": "contract_logic_function_helper",
        "contract_behavior_plain_ensures_rewrite": "contract_behavior_helper",
        "contract_predicate_inline_rewrite": "contract_predicate_helper",
        "helper_int_indexed_scalar_array_return": "helper_int_indexed_array_scalar_return",
        "helper_fixed_index_array_struct_scalar_return": "helper_int_indexed_array_scalar_return",
        "helper_single_global_struct_scalar_return": "helper_fixed_index_array_struct_scalar_return",
    }
    INTERNAL_MODULE_SMOKE_CASES = set()
    REQUIRED_BASELINE_CASES = {
        "micro_int_if_helper",
        "micro_local_static_helper_persistence",
        "helper_struct_basic",
        "helper_enum_switch_basic",
        "helper_valid_pointer_store",
        "helper_global_array_update",
        "helper_assigns_old_basic",
        "helper_stack_pointer",
        "helper_two_level_call_chain",
        "helper_multiple_call_contexts",
        "contract_logic_function_helper",
        "contract_behavior_helper",
        "contract_predicate_helper",
        "helper_float_arithmetic",
        "helper_pointer_arithmetic",
        "helper_nested_pointer",
        "helper_loop_without_invariant",
        "helper_valid_pointer_store_simpler",
        "helper_global_array_update_fixed_index",
        "helper_struct_return_whole",
        "helper_enum_indexed_array_struct_return",
        "helper_array_struct_output_parameter_rewrite",
        "helper_int_indexed_array_struct_return",
        "helper_int_indexed_array_scalar_return",
        *FINAL_REWRITE_CASES.keys(),
    }
    REQUIRED_BASELINE_V2_CASES = REQUIRED_BASELINE_CASES | BACKEND_BOUNDARY_CASES
    REQUIRED_BASELINE_V3_CASES = REQUIRED_BASELINE_V2_CASES | set(BACKEND_REWRITE_CASES)

    FUNCTION_RE = re.compile(
        r"^[ \t]*(?:[A-Za-z_][A-Za-z0-9_]*[ \t\*]+)+(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*\([^;{}]*\)\s*\{",
        re.MULTILINE,
    )
    CONTRACTED_FUNCTION_RE = re.compile(
        r"/\*@(?P<body>.*?)\*/\s*(?:[A-Za-z_][A-Za-z0-9_]*[ \t\*]+)+(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*\(",
        re.DOTALL,
    )

    def load_cases(self):
        repo_root = Path(__file__).resolve().parents[2]
        cases_path = repo_root / "autodeduct-support" / "cases.json"
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
        return repo_root, {case["id"]: case for case in cases}

    def function_names(self, source_text):
        return {match.group("name") for match in self.FUNCTION_RE.finditer(source_text)}

    def contracted_function_names(self, source_text):
        names = set()
        for match in self.CONTRACTED_FUNCTION_RE.finditer(source_text):
            body = match.group("body")
            if any(keyword in body for keyword in ("requires", "ensures", "assigns", "behavior")):
                names.add(match.group("name"))
        return names

    def entry_body(self, source_text):
        match = re.search(r"\bentry[ \t]*\([^;{}]*\)\s*\{(?P<body>.*?)\n\}", source_text, re.DOTALL)
        self.assertIsNotNone(match)
        return match.group("body")

    def test_p0_manifest_entries_have_required_metadata(self):
        _, cases = self.load_cases()
        self.assertTrue(self.P0_CASES.issubset(cases))
        for case_id in self.P0_CASES:
            case = cases[case_id]
            self.assertEqual(case["module"], "micro")
            self.assertEqual(case["entry_point"], "entry")
            self.assertEqual(case["evidence_tier"], "tier_1_helper_inference")
            self.assertIn(case["probe_role"], {"helper_inference", "contract_guided_helper_inference"})
            self.assertIn(case["feature_location"], {"helper_body", "entry_body_and_helper_body", "entry_call_contexts_and_helper_body", "entry_contract"})
            self.assertIn(case["expected_support"], {"boundary", "expected_unsupported", "supported"})
            self.assertIn("paper_limit", case)
            if case["expected_support"] == "expected_unsupported":
                self.assertNotEqual(case["paper_limit"], "none")

    def test_p0_sources_follow_helper_inference_shape(self):
        repo_root, cases = self.load_cases()
        for case_id in self.P0_CASES:
            case = cases[case_id]
            source_path = repo_root / case["path"]
            self.assertTrue(source_path.exists(), case_id)
            source_text = source_path.read_text(encoding="utf-8")
            names = self.function_names(source_text)
            helpers = names - {"entry"}
            self.assertIn("entry", names, case_id)
            self.assertGreaterEqual(len(helpers), 1, case_id)
            self.assertEqual(self.contracted_function_names(source_text), {"entry"}, case_id)
            self.assertNotRegex(source_text, r"\bstatic\b", case_id)
            self.assertNotRegex(source_text, r"//@[ \t]*assert|/\*@[ \t]*assert", case_id)
            body = self.entry_body(source_text)
            self.assertTrue(any(f"{helper}(" in body for helper in helpers), case_id)

    def test_p1_manifest_entries_have_required_metadata(self):
        _, cases = self.load_cases()
        self.assertTrue(self.P1_CASES.issubset(cases))
        for case_id in self.P1_CASES:
            case = cases[case_id]
            self.assertEqual(case["module"], "micro")
            self.assertEqual(case["entry_point"], "entry")
            self.assertEqual(case["expected_support"], "boundary")
            self.assertEqual(case["probe_role"], "helper_inference")
            self.assertEqual(case["evidence_tier"], "tier_1_helper_inference")
            self.assertEqual(case["feature_location"], "helper_body")
            self.assertIn("paper_limit", case)
        self.assertEqual(
            cases["helper_array_struct_output_parameter_rewrite"]["rewrite_of"],
            "helper_enum_indexed_array_struct_return",
        )
        self.assertEqual(
            cases["helper_int_indexed_array_scalar_return"]["rewrite_of"],
            "helper_enum_indexed_array_struct_return",
        )

    def test_final_rewrite_manifest_entries_have_required_metadata(self):
        _, cases = self.load_cases()
        self.assertTrue(set(self.FINAL_REWRITE_CASES).issubset(cases))
        for case_id, direct_case in self.FINAL_REWRITE_CASES.items():
            case = cases[case_id]
            self.assertEqual(case["module"], "micro")
            self.assertEqual(case["entry_point"], "entry")
            self.assertEqual(case["expected_support"], "boundary")
            self.assertIn(case["kind"], {"micro_helper_inference_rewrite", "micro_contract_guided_helper_inference_rewrite", "micro_helper_inference_reduction"})
            self.assertIn(case["probe_role"], {"helper_inference", "contract_guided_helper_inference"})
            self.assertEqual(case["evidence_tier"], "tier_1_helper_inference")
            self.assertIn(case["feature_location"], {"helper_body", "entry_contract"})
            self.assertEqual(case["paper_limit"], "none")
            self.assertEqual(case["helper_inference_claim"], "hypothesis")
            self.assertEqual(case["rewrite_of"], direct_case)

    def test_final_rewrite_sources_follow_helper_inference_shape(self):
        repo_root, cases = self.load_cases()
        for case_id in self.FINAL_REWRITE_CASES:
            case = cases[case_id]
            source_path = repo_root / case["path"]
            self.assertTrue(source_path.exists(), case_id)
            source_text = source_path.read_text(encoding="utf-8")
            names = self.function_names(source_text)
            helpers = names - {"entry"}
            self.assertIn("entry", names, case_id)
            self.assertGreaterEqual(len(helpers), 1, case_id)
            self.assertEqual(self.contracted_function_names(source_text), {"entry"}, case_id)
            self.assertNotRegex(source_text, r"\bstatic\b", case_id)
            self.assertNotRegex(source_text, r"//@[ \t]*assert|/\*@[ \t]*assert", case_id)
            body = self.entry_body(source_text)
            self.assertTrue(any(f"{helper}(" in body for helper in helpers), case_id)

    def test_academic_baseline_group_contains_only_functional_tier1_cases(self):
        repo_root, cases = self.load_cases()
        baseline_cases = {
            case_id: case
            for case_id, case in cases.items()
            if case.get("baseline_group") == "academic_functional_v1"
        }
        blocked = {
            "micro_assigns_old",
            "micro_behavior_basic",
            "micro_local_static_as_global_rewrite",
            "micro_array_struct_read_helper_isp_crash",
            "helper_acsl_logic_function",
            "helper_loop_with_manual_invariant",
            "sample_module_a",
            "sample_state_ghost",
            "sample_signal_ghost",
            "sample_module_d",
            "sample_state_original",
            "sample_signal_original",
            "sample_module_nl_annotated",
        }

        self.assertEqual(set(baseline_cases), self.REQUIRED_BASELINE_CASES)
        self.assertFalse(blocked & set(baseline_cases))
        for case_id, case in baseline_cases.items():
            self.assertEqual(case["evidence_tier"], "tier_1_helper_inference", case_id)
            self.assertIn(case.get("probe_role", "helper_inference"), {"helper_inference", "contract_guided_helper_inference"}, case_id)
            self.assertNotIn(case["kind"], {"micro_wp_control", "micro_entry_control"}, case_id)
            self.assertTrue((repo_root / case["path"]).exists(), case_id)

    def test_academic_functional_v2_group_contains_v1_plus_backend_boundaries(self):
        repo_root, cases = self.load_cases()
        baseline_cases = {
            case_id: case
            for case_id, case in cases.items()
            if "academic_functional_v2" in run_support_tests.case_baseline_groups(case)
        }

        self.assertEqual(set(baseline_cases), self.REQUIRED_BASELINE_V2_CASES)
        for case_id, case in baseline_cases.items():
            self.assertEqual(case["evidence_tier"], "tier_1_helper_inference", case_id)
            self.assertIn(case.get("probe_role", "helper_inference"), {"helper_inference", "contract_guided_helper_inference"}, case_id)
            self.assertNotIn(case["kind"], {"micro_wp_control", "micro_entry_control"}, case_id)
            self.assertTrue((repo_root / case["path"]).exists(), case_id)

    def test_academic_functional_v3_group_contains_v2_plus_repeated_backend_rewrite(self):
        repo_root, cases = self.load_cases()
        baseline_cases = {
            case_id: case
            for case_id, case in cases.items()
            if "academic_functional_v3" in run_support_tests.case_baseline_groups(case)
        }

        self.assertEqual(set(baseline_cases), self.REQUIRED_BASELINE_V3_CASES)
        for case_id, case in baseline_cases.items():
            self.assertEqual(case["evidence_tier"], "tier_1_helper_inference", case_id)
            self.assertIn(case.get("probe_role", "helper_inference"), {"helper_inference", "contract_guided_helper_inference"}, case_id)
            self.assertNotIn(case["kind"], {"micro_wp_control", "micro_entry_control"}, case_id)
            self.assertTrue((repo_root / case["path"]).exists(), case_id)
            self.assertIn(case.get("evaluation_profile"), {"strict_library_profile", "configured_tricera_profile"}, case_id)
            self.assertIn("direct_or_rewrite_relation", case, case_id)

    def test_backend_boundary_manifest_entries_have_required_metadata(self):
        repo_root, cases = self.load_cases()
        for case_id in self.BACKEND_BOUNDARY_CASES:
            case = cases[case_id]
            self.assertEqual(case["module"], "micro")
            self.assertEqual(case["entry_point"], "entry")
            self.assertEqual(case["expected_support"], "boundary")
            self.assertEqual(case["evidence_tier"], "tier_1_helper_inference")
            self.assertEqual(case["baseline_group"], "academic_functional_v2")
            self.assertEqual(case["source_visibility"], "public_safe_synthetic")
            self.assertIs(case["public_export"], True)
            self.assertEqual(case["saida_tricera_opts"], "-cpp -acsl")
            self.assertEqual(case["evaluation_profile"], "configured_tricera_profile")
            self.assertTrue((repo_root / case["path"]).exists(), case_id)

    def test_backend_rewrite_manifest_entries_have_required_metadata(self):
        repo_root, cases = self.load_cases()
        for case_id, direct_case in self.BACKEND_REWRITE_CASES.items():
            case = cases[case_id]
            self.assertEqual(case["module"], "micro")
            self.assertEqual(case["entry_point"], "entry")
            self.assertEqual(case["expected_support"], "boundary")
            self.assertEqual(case["evidence_tier"], "tier_1_helper_inference")
            self.assertEqual(case["baseline_group"], "academic_functional_v3")
            self.assertEqual(case["rewrite_of"], direct_case)
            self.assertEqual(case["direct_or_rewrite_relation"], f"rewrite_of:{direct_case}")
            self.assertEqual(case["source_visibility"], "public_safe_synthetic")
            self.assertIs(case["public_export"], True)
            self.assertEqual(case["saida_tricera_opts"], "-cpp -acsl")
            self.assertEqual(case["evaluation_profile"], "configured_tricera_profile")
            self.assertTrue((repo_root / case["path"]).exists(), case_id)

    def test_backend_boundary_sources_follow_helper_inference_shape(self):
        repo_root, cases = self.load_cases()
        for case_id in self.BACKEND_BOUNDARY_CASES | set(self.BACKEND_REWRITE_CASES):
            case = cases[case_id]
            source_text = (repo_root / case["path"]).read_text(encoding="utf-8")
            names = self.function_names(source_text)
            helpers = names - {"entry"}
            self.assertIn("entry", names, case_id)
            self.assertGreaterEqual(len(helpers), 1, case_id)
            self.assertEqual(self.contracted_function_names(source_text), {"entry"}, case_id)
            self.assertNotRegex(source_text, r"\bstatic\b", case_id)
            self.assertNotRegex(source_text, r"//@[ \t]*assert|/\*@[ \t]*assert", case_id)
            body = self.entry_body(source_text)
            self.assertTrue(any(f"{helper}(" in body for helper in helpers), case_id)

    def test_internal_module_smoke_group_contains_only_smoke_cases(self):
        _, cases = self.load_cases()
        baseline_cases = {
            case_id: case
            for case_id, case in cases.items()
            if case.get("baseline_group") == "internal_module_smoke_v1"
        }
        self.assertEqual(set(baseline_cases), self.INTERNAL_MODULE_SMOKE_CASES)
        for case_id, case in cases.items():
            self.assertNotEqual(case.get("baseline_group"), "internal_module_smoke_v1", case_id)

        for case_id, case in baseline_cases.items():
            self.assertEqual(case["evidence_role"], "module_smoke_evidence", case_id)
            self.assertEqual(case["helper_inference_claim"], "none", case_id)
            self.assertEqual(case["paper_model_input_classification"], "module_smoke_only", case_id)
            self.assertNotEqual(case.get("baseline_group"), "academic_functional_v1", case_id)
            self.assertNotEqual(case.get("module"), "micro", case_id)
            self.assertNotEqual(case.get("evidence_role"), "requires_harness", case_id)
            self.assertNotEqual(case.get("kind"), "optional_boundary_case", case_id)

    def test_public_manifest_contains_no_private_smoke_cases(self):
        _, cases = self.load_cases()
        for case_id, case in cases.items():
            self.assertEqual(case["module"], "micro", case_id)
            self.assertEqual(case["source_visibility"], "public", case_id)
            self.assertIs(case["public_export"], True, case_id)

    def test_p1_sources_follow_helper_inference_shape(self):
        repo_root, cases = self.load_cases()
        for case_id in self.P1_CASES:
            case = cases[case_id]
            source_path = repo_root / case["path"]
            self.assertTrue(source_path.exists(), case_id)
            source_text = source_path.read_text(encoding="utf-8")
            names = self.function_names(source_text)
            helpers = names - {"entry"}
            self.assertIn("entry", names, case_id)
            self.assertGreaterEqual(len(helpers), 1, case_id)
            self.assertEqual(self.contracted_function_names(source_text), {"entry"}, case_id)
            self.assertNotRegex(source_text, r"//@[ \t]*assert|/\*@[ \t]*assert", case_id)
            body = self.entry_body(source_text)
            self.assertTrue(any(f"{helper}(" in body for helper in helpers), case_id)


if __name__ == "__main__":
    unittest.main()
