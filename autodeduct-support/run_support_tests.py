#!/usr/bin/env python3
"""Run AutoDeduct support checks for the small-case-studies modules.

The script is intentionally dependency-free. It can be used locally in static
mode, or inside the AutoDeduct container to run Frama-C and AutoDeduct phases.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


FEATURE_PATTERNS = {
    "acsl_blocks": re.compile(r"/\*@"),
    "acsl_line_annotations": re.compile(r"//@"),
    "ghost_code": re.compile(r"//@\s*ghost|/\*@\s*ghost"),
    "predicates": re.compile(r"/\*@\s*predicate|\bpredicate\b"),
    "logic_definitions": re.compile(r"/\*@\s*logic|\blogic\b"),
    "behaviors": re.compile(r"\bbehavior\s+[A-Za-z0-9_]+"),
    "assertions": re.compile(r"//@\s*assert|/\*@\s*assert"),
    "valid_pointer_clauses": re.compile(r"\\valid(?:_read)?\s*\("),
    "old_or_at_labels": re.compile(r"\\old\s*\(|\\at\s*\("),
    "assigns_clauses": re.compile(r"\bassigns\b"),
    "array_assigns": re.compile(r"\bassigns\b[^\n;]*\[[^\]]+\]"),
    "extern_contracts": re.compile(r"\bextern\b"),
    "preprocessor_includes": re.compile(r"^\s*#\s*include\b", re.MULTILINE),
    "switch_statements": re.compile(r"\bswitch\s*\("),
    "loops": re.compile(r"\b(for|while|do)\b"),
    "structs": re.compile(r"\bstruct\b"),
    "enums": re.compile(r"\benum\b"),
    "arrays": re.compile(r"\[[^\]]*\]"),
    "pointer_syntax": re.compile(r"\*+\s*(?:const\s+)?[A-Za-z_][A-Za-z0-9_]*|\b[A-Za-z_][A-Za-z0-9_]*\s*\*+"),
    "nested_pointers": re.compile(r"\*\s*\*"),
    "float_or_double": re.compile(r"\b(float|double|long\s+double)\b"),
}

CODE_ONLY_FEATURES = {
    "extern_contracts",
    "preprocessor_includes",
    "switch_statements",
    "loops",
    "structs",
    "enums",
    "arrays",
    "pointer_syntax",
    "nested_pointers",
    "float_or_double",
}

RISK_NOTES = {
    "local_static_variables": "AutoDeduct paper lists local static variables as unsupported.",
    "nested_pointers": "Nested pointers are listed as unsupported.",
    "float_or_double": "Functional inference does not support floating-point arithmetic.",
    "loops": "Loops are accepted, but automatic loop invariant inference is not implemented.",
    "logic_definitions": "General ACSL logic functions are listed as unsupported; logic aliases should be tested explicitly.",
    "preprocessor_includes": "Industrial originals need platform headers/stubs before support can be measured fairly.",
    "pointer_syntax": "Pointer-heavy APIs usually exercise auxiliary inference and validity contracts.",
    "array_assigns": "Array frame conditions are important support-frontier tests.",
    "ghost_code": "Ghost variables/actions need Frama-C parsing and may not be useful input for functional inference.",
    "behaviors": "ACSL behaviors should be checked against the AutoDeduct phase that consumes contracts.",
}

PHASE_ORDER = ("frama_parse", "autodeduct_full", "func", "aux", "wp")
SPLIT_PHASES = ("func", "aux", "wp")
FAILED_STATUSES = {"fail", "timeout"}
CASE_METADATA_FIELDS = (
    "module",
    "kind",
    "probe_role",
    "evidence_tier",
    "evidence_role",
    "expected_support",
    "expected_result",
    "expected_reason",
    "rewrite_of",
    "baseline_group",
    "baseline_groups",
    "helper_inference_claim",
    "paper_model_input_classification",
    "source_visibility",
    "public_export",
    "feature_location",
    "paper_limit",
    "evaluation_profile",
    "direct_or_rewrite_relation",
    "include_dirs",
    "cpp_extra_args",
    "saida_tricera_opts",
)
MISSING_PLATFORM_HEADERS = {"platform_types.h", "domain_types.h"}
MISSING_HEADER_RE = re.compile(r"fatal error:\s+([A-Za-z0-9_./-]+\.h): No such file or directory")
WP_GOALS_RE = re.compile(r"Proved goals:\s*(\d+)\s*/\s*(\d+)")
WP_STATUS_GOAL_RE = re.compile(r"^\[wp\]\s+\[(?P<status>[A-Za-z -]+)\]\s+(?P<name>[A-Za-z0-9_]+)\b")
NO_INFERRED_CONTRACT_RE = re.compile(r"//\s*No inferred contract found for\s+([A-Za-z_][A-Za-z0-9_]*)")
SUSPICIOUS_CONTRACT_MARKER_RE = re.compile(
    r"\b(?P<keyword>requires|ensures)\s+\\false\s*;",
    re.IGNORECASE,
)
FUNCTION_DEF_RE = re.compile(
    r"(?m)^[ \t]*(?P<return_type>(?:[A-Za-z_][A-Za-z0-9_]*|const|volatile|static|inline|extern|signed|unsigned|long|short|struct\s+[A-Za-z_][A-Za-z0-9_]*|enum\s+[A-Za-z_][A-Za-z0-9_]*)[\w\s\*]*)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*\{"
)
TRICERA_ERROR_RE = re.compile(
    r"\bTriCera\b.*\b(?:syntax|parse|parser|parsing)\b.*\berror\b"
    r"|\b(?:syntax|parse|parser|parsing)\b.*\berror\b.*\bTriCera\b"
    r"|\b(?:mismatched input|extraneous input|no viable alternative at input)\b"
    r"|\bHorn Translation Error\b"
    r"|\bexpects\s+\d+\s+argument\(s\),\s+but\s+got\s+\d+\b",
    re.IGNORECASE,
)
TRICERA_CONTEXT_RE = re.compile(r"\bTriCera\b", re.IGNORECASE)
PARSER_ERROR_RE = re.compile(
    r"\b(?:syntax|parse|parser|parsing)\b.*\berror\b"
    r"|\b(?:mismatched input|extraneous input|no viable alternative at input)\b",
    re.IGNORECASE,
)
HORN_TRANSLATION_ERROR_RE = re.compile(r"\bHorn Translation Error\b.*", re.IGNORECASE)
ARITY_MISMATCH_RE = re.compile(
    r"\bexpects\s+\d+\s+argument\(s\),\s+but\s+got\s+\d+\b",
    re.IGNORECASE,
)
TRICERA_PARSER_ERROR_RE = re.compile(
    r"\bTriCera\b.*\b(?:syntax|parse|parser|parsing)\b.*\berror\b"
    r"|\b(?:syntax|parse|parser|parsing)\b.*\berror\b.*\bTriCera\b"
    r"|\b(?:mismatched input|extraneous input|no viable alternative at input)\b",
    re.IGNORECASE,
)
TRICERA_RESULT_PARSE_ERROR_RE = re.compile(
    r"(?mi)^\s*Parse Error:.*\b(?:Unrecoverable\s+Syntax\s+Error|Syntax\s+Error)\b"
)
SAIDA_BACKEND_RECOVERY_ERROR_RE = re.compile(
    r"(?is)\bSyntax Error,\s*trying to recover and continue parse\b"
    r".*\binput program could not be parsed\b"
)
TRICERA_SOLVER_ERROR_RE = re.compile(
    r"\b(?:solver|Eldarica|Princess|Z3|Alt-Ergo)\b.*\b(?:error|exception|failed)\b"
    r"|\b(?:error|exception|failed)\b.*\b(?:solver|Eldarica|Princess|Z3|Alt-Ergo)\b",
    re.IGNORECASE,
)
TRICERA_CONTRACT_RE = re.compile(
    r"/\*\s*contracts?\s+for\s+([A-Za-z_][A-Za-z0-9_]*)\s*\*/",
    re.IGNORECASE,
)
C_CONTROL_KEYWORDS = {"if", "for", "while", "switch", "return", "sizeof"}
CONTRACT_KEYWORD_RE = re.compile(
    r"\b(?:requires|ensures|assigns|assumes|behavior|complete|disjoint|decreases|terminates)\b"
)
NON_CONTRACT_ACSL_RE = re.compile(r"^\s*(?:logic|predicate|axiomatic|lemma|type|model)\b")
MANUALLY_ANNOTATED_KINDS = {
    "self_contained_verified_variant",
    "signal_status_verified_variant",
    "sample_module_d",
    "sample_module_anonymized",
    "optional_boundary_case",
}
REQUIRES_HARNESS_KINDS = {
    "original_industrial_source",
    "original_harness_experiment",
    "original_utility_source",
}
PROBE_OWNERSHIP_VALUES = {
    "entry_contract_only",
    "manually_annotated_variant",
    "helper_inference_probe",
    "wp_control",
    "requires_harness",
}
RTE_GOAL_CATEGORIES = (
    "pointer_validity",
    "array_bounds",
    "integer_overflow",
    "floating_point",
    "other_rte",
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data["cases"]


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def resolve_repo_path(repo_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def strip_comments_for_static_scan(source: str) -> str:
    # Keep ACSL comments in the main scan, but remove comments for local-static
    # detection to avoid counting examples or prose.
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"//.*", "", source)
    return source


def count_local_static_variables(source: str) -> int:
    cleaned = strip_comments_for_static_scan(source)
    depth = 0
    count = 0
    token = []
    for char in cleaned:
        if char == "{":
            depth += 1
            token.clear()
        elif char == "}":
            depth = max(depth - 1, 0)
            token.clear()
        elif char == ";":
            statement = "".join(token)
            if depth > 0 and re.search(r"\bstatic\b[^;=()]*\b[A-Za-z_][A-Za-z0-9_]*", statement):
                count += 1
            token.clear()
        else:
            token.append(char)
    return count


def count_immediate_acsl_contract_blocks(text: str, start: int) -> int:
    prefix = text[:start]
    count = 0
    while True:
        prefix = prefix.rstrip()
        if not prefix.endswith("*/"):
            return count
        block_start = prefix.rfind("/*@")
        if block_start < 0:
            return count
        between = prefix[block_start + 3 : -2]
        if "\n}" in between:
            return count
        if is_function_contract_block(between):
            count += 1
        prefix = prefix[:block_start]


def is_function_contract_block(block_text: str) -> bool:
    stripped = block_text.strip()
    if NON_CONTRACT_ACSL_RE.match(stripped):
        return False
    return bool(CONTRACT_KEYWORD_RE.search(stripped))


def function_contract_counts(source: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for match in FUNCTION_DEF_RE.finditer(source):
        name = match.group("name")
        if name in C_CONTROL_KEYWORDS:
            continue
        counts[name] = count_immediate_acsl_contract_blocks(source, match.start())
    return counts


def unannotated_helper_names(source: str, entry_point: str) -> list[str]:
    counts = function_contract_counts(source)
    return sorted(name for name, contract_count in counts.items() if name != entry_point and contract_count == 0)


def helper_contract_inventory(source: str | None, entry_point: str) -> dict[str, int]:
    if source is None:
        return {
            "helper_function_count": 0,
            "unannotated_helper_function_count": 0,
            "manually_annotated_helper_count": 0,
        }

    counts = function_contract_counts(source)
    helper_counts = {name: count for name, count in counts.items() if name != entry_point}
    return {
        "helper_function_count": len(helper_counts),
        "unannotated_helper_function_count": sum(1 for count in helper_counts.values() if count == 0),
        "manually_annotated_helper_count": sum(1 for count in helper_counts.values() if count > 0),
    }


def detect_tricera_error(stderr_text: str) -> bool:
    if TRICERA_RESULT_PARSE_ERROR_RE.search(stderr_text):
        return True
    if SAIDA_BACKEND_RECOVERY_ERROR_RE.search(stderr_text):
        return True
    if TRICERA_ERROR_RE.search(stderr_text):
        return True
    lines = stderr_text.splitlines()
    for index in range(len(lines)):
        window = "\n".join(lines[max(0, index - 2) : index + 3])
        if TRICERA_CONTEXT_RE.search(window) and PARSER_ERROR_RE.search(window):
            return True
    return False


def first_matching_line(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    line_start = text.rfind("\n", 0, match.start()) + 1
    line_end = text.find("\n", match.end())
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()


def tricera_result_file(case: dict[str, Any], repo_root: Path, work_dir: Path) -> Path:
    source_path = resolve_repo_path(repo_root, case["path"])
    return work_dir / f"saida_result_{source_path.name}"


def tricera_harness_file(case: dict[str, Any], repo_root: Path, work_dir: Path) -> Path:
    source_path = resolve_repo_path(repo_root, case["path"])
    return work_dir / f"saida_harness_{source_path.name}"


def tricera_contract_names(result_text: str) -> list[str]:
    names = []
    for name in TRICERA_CONTRACT_RE.findall(result_text):
        if name not in names:
            names.append(name)
    return names


def backend_parser_error_line(
    *,
    tricera_result_text: str,
    func_stderr_text: str,
    combined_text: str,
) -> str | None:
    # These messages come from the retained functional backend artifacts. They
    # mean TriCera did not produce usable contract inference output.
    parser_line = first_matching_line(TRICERA_RESULT_PARSE_ERROR_RE, tricera_result_text)
    if parser_line is not None:
        return parser_line

    parser_line = first_matching_line(SAIDA_BACKEND_RECOVERY_ERROR_RE, func_stderr_text)
    if parser_line is not None:
        return parser_line

    return first_matching_line(TRICERA_PARSER_ERROR_RE, combined_text)


def functional_backend_evidence(
    *,
    source_text: str | None,
    entry_point: str,
    tricera_result_present: bool,
    tricera_result_text: str,
    func_stdout_text: str,
    func_stderr_text: str,
    expect_tricera_result: bool,
) -> dict[str, Any]:
    combined = "\n".join((tricera_result_text, func_stdout_text, func_stderr_text))
    expected_helpers = unannotated_helper_names(source_text, entry_point) if source_text is not None else []

    horn_line = first_matching_line(HORN_TRANSLATION_ERROR_RE, combined)
    if horn_line is not None:
        kind = "horn_translation_arity_mismatch" if ARITY_MISMATCH_RE.search(horn_line) else "horn_translation_error"
        return {
            "functional_backend_status": "translation_error",
            "functional_backend_error_kind": kind,
            "functional_backend_error_text": horn_line,
            "tricera_result_present": tricera_result_present,
        }

    arity_line = first_matching_line(ARITY_MISMATCH_RE, combined)
    if arity_line is not None:
        return {
            "functional_backend_status": "translation_error",
            "functional_backend_error_kind": "arity_mismatch",
            "functional_backend_error_text": arity_line,
            "tricera_result_present": tricera_result_present,
        }

    parser_line = backend_parser_error_line(
        tricera_result_text=tricera_result_text,
        func_stderr_text=func_stderr_text,
        combined_text=combined,
    )
    if parser_line is not None:
        return {
            "functional_backend_status": "parser_error",
            "functional_backend_error_kind": "tricera_parser_error",
            "functional_backend_error_text": parser_line,
            "tricera_result_present": tricera_result_present,
        }

    solver_line = first_matching_line(TRICERA_SOLVER_ERROR_RE, combined)
    if solver_line is not None:
        return {
            "functional_backend_status": "solver_error",
            "functional_backend_error_kind": "tricera_solver_error",
            "functional_backend_error_text": solver_line,
            "tricera_result_present": tricera_result_present,
        }

    if expect_tricera_result and not tricera_result_present:
        return {
            "functional_backend_status": "missing_output",
            "functional_backend_error_kind": "missing_tricera_result",
            "functional_backend_error_text": "Saida completed but the TriCera result file is missing",
            "tricera_result_present": False,
        }

    contract_names = tricera_contract_names(tricera_result_text)
    if expected_helpers:
        if not contract_names:
            return {
                "functional_backend_status": "missing_output",
                "functional_backend_error_kind": "no_expected_helper_contract_blocks",
                "functional_backend_error_text": "TriCera result contains no expected helper contract blocks",
                "tricera_result_present": tricera_result_present,
            }
        missing_helpers = [name for name in expected_helpers if name not in contract_names]
        if missing_helpers:
            return {
                "functional_backend_status": "missing_output",
                "functional_backend_error_kind": "missing_expected_helper_contract_blocks",
                "functional_backend_error_text": "TriCera result is missing contract block(s) for: "
                + ", ".join(missing_helpers),
                "tricera_result_present": tricera_result_present,
            }

    if tricera_result_present:
        return {
            "functional_backend_status": "pass",
            "functional_backend_error_kind": None,
            "functional_backend_error_text": None,
            "tricera_result_present": True,
        }

    return {
        "functional_backend_status": "unknown",
        "functional_backend_error_kind": None,
        "functional_backend_error_text": None,
        "tricera_result_present": False,
    }


def inspect_generated_inference(
    source_text: str,
    generated_text: str,
    entry_point: str,
) -> dict[str, int]:
    source_counts = function_contract_counts(source_text)
    generated_counts = function_contract_counts(generated_text)
    inferred_count = 0

    for name, generated_contract_count in generated_counts.items():
        if name == entry_point:
            continue
        source_contract_count = source_counts.get(name, 0)
        if generated_contract_count > source_contract_count:
            inferred_count += generated_contract_count - source_contract_count

    return {
        "inferred_helper_contract_count": inferred_count,
        "missing_inferred_contract_count": len(NO_INFERRED_CONTRACT_RE.findall(generated_text)),
        **helper_contract_inventory(source_text, entry_point),
    }


def suspicious_contract_markers(generated_text: str) -> list[str]:
    markers = {
        f"{match.group('keyword').lower()} \\false;"
        for match in SUSPICIOUS_CONTRACT_MARKER_RE.finditer(generated_text)
    }
    return sorted(markers)


def inferred_contract_quality_value(
    *,
    saida_output_parse_status: str,
    inferred_helper_contract_count: int,
    missing_inferred_contract_count: int,
    unannotated_helper_function_count: int,
    suspicious_contract_markers: list[str],
) -> tuple[str, str]:
    if saida_output_parse_status in {"fail", "timeout"}:
        return "syntactically_invalid", "generated Saida output did not parse with Frama-C"
    if missing_inferred_contract_count > 0:
        return "missing", "generated Saida output contains a missing-contract marker"
    if unannotated_helper_function_count > 0 and inferred_helper_contract_count == 0:
        return "missing", "no inferred contract was found for an unannotated helper"
    if suspicious_contract_markers:
        return (
            "vacuous_candidate",
            "generated Saida output contains suspicious contract marker(s): "
            + ", ".join(suspicious_contract_markers)
            + "; manual review required",
        )
    if saida_output_parse_status == "pass" and inferred_helper_contract_count > 0:
        return (
            "usable_candidate",
            "generated Saida output parsed and inferred helper contracts have no suspicious markers",
        )
    return "unknown", "not enough generated Saida output evidence"


def inference_evidence_value(
    *,
    tricera_error_detected: bool,
    inferred_helper_contract_count: int,
    missing_inferred_contract_count: int,
    helper_function_count: int,
    unannotated_helper_function_count: int,
    manually_annotated_helper_count: int,
) -> str:
    if tricera_error_detected:
        return "tricera_error"
    if missing_inferred_contract_count > 0:
        return "missing_helper_contracts"
    if manually_annotated_helper_count > 0:
        return "manually_annotated_helper"
    if helper_function_count == 0:
        return "no_helpers_to_infer"
    if unannotated_helper_function_count > 0 and inferred_helper_contract_count == 0:
        return "missing_helper_contracts"
    if inferred_helper_contract_count > 0:
        return "inferred_helpers"
    return "unclear"


def probe_ownership(case: dict[str, Any], repo_root: Path) -> list[str]:
    ownership: list[str] = []
    declared = case.get("probe_ownership", case.get("evidence_role"))
    if isinstance(declared, str):
        declared_values = [declared]
    elif isinstance(declared, list):
        declared_values = [str(value) for value in declared]
    else:
        declared_values = []

    for value in declared_values:
        if value in PROBE_OWNERSHIP_VALUES and value not in ownership:
            ownership.append(value)

    kind = str(case.get("kind", ""))
    if kind in MANUALLY_ANNOTATED_KINDS and "manually_annotated_variant" not in ownership:
        ownership.append("manually_annotated_variant")
    if kind in REQUIRES_HARNESS_KINDS and "requires_harness" not in ownership:
        ownership.append("requires_harness")

    source_path = resolve_repo_path(repo_root, case["path"])
    source_text: str | None = None
    if source_path.exists():
        source_text = source_path.read_text(encoding="utf-8", errors="replace")
        helper_names = unannotated_helper_names(source_text, case["entry_point"])
        if helper_names and "helper_inference_probe" not in ownership:
            ownership.append("helper_inference_probe")

        function_names = function_contract_counts(source_text)
        if (
            case.get("module") == "micro"
            and not helper_names
            and set(function_names).issubset({case["entry_point"]})
            and "entry_contract_only" not in ownership
        ):
            ownership.append("entry_contract_only")

    if str(case.get("expected_reason", "")).startswith("wp_control") and "wp_control" not in ownership:
        ownership.append("wp_control")

    return ownership


def probe_role_cell(item: dict[str, Any]) -> str:
    for key in ("probe_role", "evidence_role"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    ownership = item.get("probe_ownership")
    if isinstance(ownership, list) and ownership:
        return ", ".join(str(value) for value in ownership)
    return "-"


def enrich_saida_phase_result(
    result: dict[str, Any],
    case: dict[str, Any],
    repo_root: Path,
    work_dir: Path,
) -> dict[str, Any]:
    source_path = resolve_repo_path(repo_root, case["path"])
    generated_path = work_dir / "tmp_inferred_source_merged.c"
    tricera_result_path = tricera_result_file(case, repo_root, work_dir)
    stdout_path = work_dir / "func" / "stdout.txt"
    stderr_path = work_dir / "func" / "stderr.txt"

    source_text = (
        source_path.read_text(encoding="utf-8", errors="replace") if source_path.exists() else None
    )
    generated_text = (
        generated_path.read_text(encoding="utf-8", errors="replace") if generated_path.exists() else ""
    )
    tricera_result_text = (
        tricera_result_path.read_text(encoding="utf-8", errors="replace")
        if tricera_result_path.exists()
        else ""
    )
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""

    if source_text is not None and generated_text:
        counts = inspect_generated_inference(source_text, generated_text, case["entry_point"])
    else:
        counts = {
            "inferred_helper_contract_count": result.get("inferred_helper_contract_count", 0),
            "missing_inferred_contract_count": result.get("missing_inferred_contract_count", 0),
            **helper_contract_inventory(source_text, case["entry_point"]),
        }
    backend = functional_backend_evidence(
        source_text=source_text,
        entry_point=case["entry_point"],
        tricera_result_present=tricera_result_path.exists(),
        tricera_result_text=tricera_result_text,
        func_stdout_text=stdout_text,
        func_stderr_text=stderr_text,
        expect_tricera_result=result.get("status") == "pass",
    )
    tricera_error = backend["functional_backend_status"] in {
        "translation_error",
        "parser_error",
        "solver_error",
    } or detect_tricera_error("\n".join((tricera_result_text, stdout_text, stderr_text)))

    result["saida_process_returncode"] = result.get("saida_process_returncode", result.get("returncode"))
    result["tricera_error_detected"] = tricera_error
    result["functional_backend_status"] = backend["functional_backend_status"]
    result["functional_backend_error_kind"] = backend["functional_backend_error_kind"]
    result["functional_backend_error_text"] = backend["functional_backend_error_text"]
    result["tricera_result_present"] = backend["tricera_result_present"]
    result["inferred_helper_contract_count"] = counts["inferred_helper_contract_count"]
    result["missing_inferred_contract_count"] = counts["missing_inferred_contract_count"]
    result["helper_function_count"] = counts["helper_function_count"]
    result["unannotated_helper_function_count"] = counts["unannotated_helper_function_count"]
    result["manually_annotated_helper_count"] = counts["manually_annotated_helper_count"]
    result["saida_output_parse_status"] = result.get("saida_output_parse_status", "unknown")
    markers = suspicious_contract_markers(generated_text)
    result["suspicious_contract_markers"] = markers
    quality, reason = inferred_contract_quality_value(
        saida_output_parse_status=result["saida_output_parse_status"],
        inferred_helper_contract_count=counts["inferred_helper_contract_count"],
        missing_inferred_contract_count=counts["missing_inferred_contract_count"],
        unannotated_helper_function_count=counts["unannotated_helper_function_count"],
        suspicious_contract_markers=markers,
    )
    result["inferred_contract_quality"] = quality
    result["inferred_contract_quality_reason"] = reason
    if generated_text or not isinstance(result.get("inference_evidence"), str):
        result["inference_evidence"] = inference_evidence_value(
            tricera_error_detected=tricera_error,
            inferred_helper_contract_count=counts["inferred_helper_contract_count"],
            missing_inferred_contract_count=counts["missing_inferred_contract_count"],
            helper_function_count=counts["helper_function_count"],
            unannotated_helper_function_count=counts["unannotated_helper_function_count"],
            manually_annotated_helper_count=counts["manually_annotated_helper_count"],
        )
    return result


def enrich_case_evidence(item: dict[str, Any], case: dict[str, Any], repo_root: Path, case_out: Path) -> dict[str, Any]:
    item["probe_ownership"] = probe_ownership(case, repo_root)
    item["probe_role"] = probe_role_cell(case)
    func = item.get("phases", {}).get("func")
    if isinstance(func, dict):
        enrich_saida_phase_result(func, case, repo_root, case_out)
        item["inference_evidence"] = func.get("inference_evidence", "unclear")
        item["saida_process_returncode"] = func.get("saida_process_returncode")
        item["tricera_error_detected"] = func.get("tricera_error_detected", False)
        item["functional_backend_status"] = func.get("functional_backend_status", "unknown")
        item["functional_backend_error_kind"] = func.get("functional_backend_error_kind")
        item["functional_backend_error_text"] = func.get("functional_backend_error_text")
        item["tricera_result_present"] = func.get("tricera_result_present", False)
        item["inferred_helper_contract_count"] = func.get("inferred_helper_contract_count", 0)
        item["missing_inferred_contract_count"] = func.get("missing_inferred_contract_count", 0)
        item["saida_output_parse_status"] = func.get("saida_output_parse_status", "unknown")
        item["inferred_contract_quality"] = func.get("inferred_contract_quality", "unknown")
        item["suspicious_contract_markers"] = func.get("suspicious_contract_markers", [])
        item["inferred_contract_quality_reason"] = func.get(
            "inferred_contract_quality_reason", "not enough generated Saida output evidence"
        )
        item["helper_function_count"] = func.get("helper_function_count", 0)
        item["unannotated_helper_function_count"] = func.get("unannotated_helper_function_count", 0)
        item["manually_annotated_helper_count"] = func.get("manually_annotated_helper_count", 0)
    else:
        source_path = resolve_repo_path(repo_root, case["path"])
        source_text = source_path.read_text(encoding="utf-8", errors="replace") if source_path.exists() else None
        helper_counts = helper_contract_inventory(source_text, case["entry_point"])
        item["inference_evidence"] = "unclear"
        item["saida_process_returncode"] = None
        item["tricera_error_detected"] = False
        item["functional_backend_status"] = "unknown"
        item["functional_backend_error_kind"] = None
        item["functional_backend_error_text"] = None
        item["tricera_result_present"] = False
        item["inferred_helper_contract_count"] = 0
        item["missing_inferred_contract_count"] = 0
        item["saida_output_parse_status"] = "unknown"
        item["inferred_contract_quality"] = "unknown"
        item["suspicious_contract_markers"] = []
        item["inferred_contract_quality_reason"] = "not enough generated Saida output evidence"
        item["helper_function_count"] = helper_counts["helper_function_count"]
        item["unannotated_helper_function_count"] = helper_counts["unannotated_helper_function_count"]
        item["manually_annotated_helper_count"] = helper_counts["manually_annotated_helper_count"]
    return item


def static_scan(case: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    path = resolve_repo_path(repo_root, case["path"])
    result: dict[str, Any] = {
        "exists": path.exists(),
        "loc": 0,
        "features": {},
        "risk_notes": [],
    }
    if not path.exists():
        result["risk_notes"].append(f"Missing file: {case['path']}")
        return result

    source = path.read_text(encoding="utf-8", errors="replace")
    code_only_source = strip_comments_for_static_scan(source)
    result["loc"] = len(source.splitlines())
    for name, pattern in FEATURE_PATTERNS.items():
        scan_source = code_only_source if name in CODE_ONLY_FEATURES else source
        matches = pattern.findall(scan_source)
        result["features"][name] = len(matches)

    local_static = count_local_static_variables(source)
    result["features"]["local_static_variables"] = local_static

    for feature, note in RISK_NOTES.items():
        if result["features"].get(feature, 0) > 0:
            result["risk_notes"].append(note)

    return result


def base_case_result(case: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    result = {
        "id": case["id"],
        "path": case["path"],
        "entry_point": case["entry_point"],
        "description": case["description"],
        "probe_ownership": probe_ownership(case, repo_root),
        "inference_evidence": "unclear",
        "static": static_scan(case, repo_root),
        "phases": {},
    }
    for key in CASE_METADATA_FIELDS:
        if key in case:
            result[key] = case[key]
    result["module"] = result.get("module", case.get("module"))
    result["kind"] = result.get("kind", case.get("kind"))
    result["probe_role"] = result.get("probe_role", probe_role_cell(case))
    result["evaluation_profile"] = result.get(
        "evaluation_profile",
        "configured_tricera_profile" if case.get("saida_tricera_opts") else "strict_library_profile",
    )
    result["direct_or_rewrite_relation"] = result.get(
        "direct_or_rewrite_relation",
        f"rewrite_of:{case['rewrite_of']}" if case.get("rewrite_of") else "direct",
    )
    return result


def copy_existing_run_metadata(item: dict[str, Any], existing: dict[str, Any]) -> None:
    if isinstance(existing.get("lib_entry"), bool):
        item["lib_entry"] = existing["lib_entry"]


def sanitized_result_map(out_dir: Path) -> dict[str, dict[str, Any]]:
    snapshot = read_json(out_dir / "results-summary.json")
    if not isinstance(snapshot, list):
        return {}
    return {
        str(item["id"]): item
        for item in snapshot
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def has_recorded_phase(item: dict[str, Any]) -> bool:
    phases = item.get("phases", {})
    if not isinstance(phases, dict):
        return False
    for phase_result in phases.values():
        if isinstance(phase_result, dict) and phase_result.get("status") not in {None, "unknown"}:
            return True
    return False


def uses_sanitized_snapshot(item: dict[str, Any]) -> bool:
    phases = item.get("phases", {})
    if not isinstance(phases, dict):
        return False
    return any(
        isinstance(phase_result, dict)
        and phase_result.get("source") == "results-summary.json"
        for phase_result in phases.values()
    )


def apply_sanitized_snapshot(item: dict[str, Any], snapshot: dict[str, Any]) -> None:
    statuses = snapshot.get("phase_statuses")
    if isinstance(statuses, dict):
        for phase in PHASE_ORDER:
            status = statuses.get(phase)
            if isinstance(status, str):
                item["phases"][phase] = {"status": status, "source": "results-summary.json"}

    wp_phase = item["phases"].setdefault("wp", {"status": "unknown", "source": "results-summary.json"})
    if isinstance(snapshot.get("wp_goals"), str):
        wp_phase["wp_goals"] = snapshot["wp_goals"]

    func_phase = item["phases"].setdefault("func", {"status": "unknown", "source": "results-summary.json"})
    for key in (
        "inference_evidence",
        "inferred_helper_contract_count",
        "missing_inferred_contract_count",
        "saida_output_parse_status",
        "inferred_contract_quality",
        "suspicious_contract_markers",
        "inferred_contract_quality_reason",
        "functional_backend_status",
        "functional_backend_error_kind",
        "functional_backend_error_text",
        "tricera_result_present",
    ):
        if key in snapshot:
            item[key] = snapshot[key]
            func_phase[key] = snapshot[key]

    for key in ("lib_entry", "observed", "conclusion"):
        if key in snapshot:
            item[key] = snapshot[key]


def legacy_frama_parse_result(case_out: Path) -> dict[str, Any] | None:
    stdout_path = case_out / "logs" / "frama_parse.stdout.txt"
    stderr_path = case_out / "logs" / "frama_parse.stderr.txt"
    if not stdout_path.exists() and not stderr_path.exists():
        return None

    stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    stderr = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
    combined = f"{stdout}\n{stderr}"
    failed = any(
        marker in combined
        for marker in (
            "fatal error:",
            "Frama-C aborted",
            "User Error",
            "compilation terminated.",
        )
    )
    return {
        "status": "fail" if failed else "pass",
        "returncode": 1 if failed else 0,
        "command": None,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "generated_files": [],
        "source": "legacy_logs",
    }


def merged_case_result(case: dict[str, Any], repo_root: Path, out_dir: Path) -> dict[str, Any]:
    item = base_case_result(case, repo_root)
    case_out = out_dir / case["id"]

    existing = read_json(case_out / "result.json")
    if isinstance(existing, dict) and isinstance(existing.get("phases"), dict):
        copy_existing_run_metadata(item, existing)
        item["phases"].update(existing["phases"])

    if "frama_parse" not in item["phases"]:
        legacy_parse = legacy_frama_parse_result(case_out)
        if legacy_parse is not None:
            item["phases"]["frama_parse"] = legacy_parse

    for phase in PHASE_ORDER:
        phase_result = read_json(case_out / phase / "result.json")
        if isinstance(phase_result, dict):
            item["phases"][phase] = phase_result

    item = enrich_case_evidence(item, case, repo_root, case_out)
    if not has_recorded_phase(item) or uses_sanitized_snapshot(item):
        snapshot = sanitized_result_map(out_dir).get(case["id"])
        if isinstance(snapshot, dict):
            apply_sanitized_snapshot(item, snapshot)
    return item


def all_merged_results(cases: list[dict[str, Any]], repo_root: Path, out_dir: Path) -> list[dict[str, Any]]:
    return [persist_classification_fields(merged_case_result(case, repo_root, out_dir), out_dir) for case in cases]


def fresh_case_result(case: dict[str, Any], repo_root: Path, out_dir: Path) -> dict[str, Any]:
    return enrich_case_evidence(base_case_result(case, repo_root), case, repo_root, out_dir / case["id"])


def phase_output_paths(item: dict[str, Any], case_out: Path, phase: str) -> list[Path]:
    paths = [
        case_out / phase / "stdout.txt",
        case_out / phase / "stderr.txt",
        case_out / "logs" / f"{phase}.stdout.txt",
        case_out / "logs" / f"{phase}.stderr.txt",
    ]
    phase_result = item.get("phases", {}).get(phase)
    if isinstance(phase_result, dict):
        for key in ("stdout", "stderr"):
            value = phase_result.get(key)
            if isinstance(value, str):
                paths.append(Path(value))
    return paths


def read_phase_output(item: dict[str, Any], out_dir: Path, phase: str) -> str:
    case_out = out_dir / item["id"]
    seen: set[Path] = set()
    chunks = []
    for path in phase_output_paths(item, case_out, phase):
        normalized = path.resolve() if path.exists() else path
        if normalized in seen or not path.exists():
            continue
        seen.add(normalized)
        chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def extract_wp_goals_from_text(text: str) -> str:
    match = WP_GOALS_RE.search(text)
    if not match:
        return "-"
    return f"{match.group(1)}/{match.group(2)}"


def empty_rte_goal_breakdown() -> dict[str, dict[str, int]]:
    return {
        category: {"reported": 0, "proved": 0, "unproved": 0}
        for category in RTE_GOAL_CATEGORIES
    }


def rte_goal_category(goal_name: str) -> str | None:
    name = goal_name.lower()
    if "rte" not in name:
        return None
    if any(token in name for token in ("float", "double", "nan", "finite")):
        return "floating_point"
    if any(token in name for token in ("mem_access", "valid", "pointer", "ptr", "separated")):
        return "pointer_validity"
    if any(token in name for token in ("index", "bound", "bounds", "array")):
        return "array_bounds"
    if any(token in name for token in ("overflow", "underflow", "div", "mod", "shift", "signed", "unsigned")):
        return "integer_overflow"
    return "other_rte"


def extract_rte_goal_breakdown_from_text(text: str) -> dict[str, dict[str, int]]:
    breakdown = empty_rte_goal_breakdown()
    for line in text.splitlines():
        match = WP_STATUS_GOAL_RE.search(line.strip())
        if not match:
            continue
        category = rte_goal_category(match.group("name"))
        if category is None:
            continue
        status = match.group("status").lower()
        breakdown[category]["reported"] += 1
        if any(token in status for token in ("failure", "timeout", "failed", "invalid")):
            breakdown[category]["unproved"] += 1
        else:
            breakdown[category]["proved"] += 1
    return breakdown


def wp_goals_cell(item: dict[str, Any], out_dir: Path) -> str:
    phase_result = item.get("phases", {}).get("wp")
    if isinstance(phase_result, dict) and isinstance(phase_result.get("wp_goals"), str):
        return phase_result["wp_goals"]
    return extract_wp_goals_from_text(read_phase_output(item, out_dir, "wp"))


def rte_wp_goals_cell(item: dict[str, Any], out_dir: Path) -> str:
    phase_result = item.get("phases", {}).get("rte_wp")
    if isinstance(phase_result, dict) and isinstance(phase_result.get("rte_wp_goals"), str):
        return phase_result["rte_wp_goals"]
    return extract_wp_goals_from_text(read_phase_output(item, out_dir, "rte_wp"))


def wp_goal_counts(item: dict[str, Any], out_dir: Path) -> tuple[int, int] | None:
    goals = wp_goals_cell(item, out_dir)
    match = re.fullmatch(r"(\d+)/(\d+)", goals)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def wp_goals_complete(item: dict[str, Any], out_dir: Path) -> bool | None:
    counts = wp_goal_counts(item, out_dir)
    if counts is None:
        return None
    proved, total = counts
    if total <= 0:
        return False
    return proved == total


def wp_goals_fully_proved(item: dict[str, Any], out_dir: Path) -> bool:
    return wp_goals_complete(item, out_dir) is True


def rte_wp_goal_counts(item: dict[str, Any], out_dir: Path) -> tuple[int, int] | None:
    goals = rte_wp_goals_cell(item, out_dir)
    match = re.fullmatch(r"(\d+)/(\d+)", goals)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def rte_result_cell(item: dict[str, Any], out_dir: Path) -> str:
    rte_wp = phase_status(item, "rte_wp")
    if rte_wp is None:
        return "not_run"
    if rte_wp in FAILED_STATUSES:
        return "failed_at_rte_wp"
    if rte_wp == "pass":
        counts = rte_wp_goal_counts(item, out_dir)
        if counts is None:
            return "unknown"
        proved, total = counts
        if total <= 0:
            return "unknown"
        if proved == total:
            return "rte_goals_proved"
        return "failed_at_rte_wp_goals"
    return "unknown"


def missing_platform_header(item: dict[str, Any], out_dir: Path) -> str | None:
    text = read_phase_output(item, out_dir, "frama_parse")
    for match in MISSING_HEADER_RE.finditer(text):
        header = Path(match.group(1)).name
        if header in MISSING_PLATFORM_HEADERS:
            return header
    return None


def phase_status(item: dict[str, Any], phase: str) -> str | None:
    value = item.get("phases", {}).get(phase)
    if not isinstance(value, dict):
        return None
    status = value.get("status")
    return status if isinstance(status, str) else None


def phase_status_map(item: dict[str, Any]) -> dict[str, str]:
    return {phase: phase_status(item, phase) or "unknown" for phase in PHASE_ORDER}


def process_first_failed_stage(item: dict[str, Any], out_dir: Path) -> str:
    for phase in ("frama_parse", "func", "aux", "wp"):
        if phase_status(item, phase) in FAILED_STATUSES:
            return phase
    if phase_status(item, "wp") == "pass" and wp_goals_complete(item, out_dir) is False:
        return "wp"
    return "-"


def evidence_first_failed_stage(item: dict[str, Any], out_dir: Path) -> str:
    if phase_status(item, "frama_parse") in FAILED_STATUSES:
        return "frama_parse"
    if phase_status(item, "func") in FAILED_STATUSES:
        return "func"

    backend_status = item.get("functional_backend_status")
    if backend_status == "translation_error":
        return "func_backend_translation"
    if backend_status == "parser_error":
        return "func_backend_parser"
    if backend_status == "solver_error":
        return "func_backend_solver"
    if backend_status == "missing_output":
        return "func_backend_output"

    if item.get("saida_output_parse_status") in {"fail", "timeout"}:
        return "func_output_validation"
    if item.get("inferred_contract_quality") == "syntactically_invalid":
        return "func_output_validation"
    if (
        item.get("inference_evidence") == "missing_helper_contracts"
        or item.get("inferred_contract_quality") == "missing"
    ):
        return "func_contract_inference"
    if item.get("inferred_contract_quality") == "vacuous_candidate":
        return "func_contract_quality"
    if phase_status(item, "aux") in FAILED_STATUSES:
        return "aux"
    if phase_status(item, "wp") in FAILED_STATUSES:
        return "wp"
    if phase_status(item, "wp") == "pass" and wp_goals_complete(item, out_dir) is not True:
        return "wp"
    if observed_cell(item, out_dir) == "supported_end_to_end":
        return "-"
    return "-"


def split_was_run(item: dict[str, Any]) -> bool:
    phases = item.get("phases", {})
    return isinstance(phases, dict) and any(phase in phases for phase in SPLIT_PHASES)


def expected_cell(item: dict[str, Any]) -> str:
    expected = item.get("expected_support", item.get("expected_result", "-"))
    return expected if isinstance(expected, str) else "-"


def end_to_end_passed(item: dict[str, Any], out_dir: Path) -> bool:
    return (
        item.get("lib_entry") is True
        and item.get("inference_evidence") == "inferred_helpers"
        and item.get("unannotated_helper_function_count", 0) > 0
        and item.get("inferred_helper_contract_count", 0)
        >= item.get("unannotated_helper_function_count", 0)
        and item.get("missing_inferred_contract_count", 0) == 0
        and item.get("functional_backend_status") == "pass"
        and item.get("saida_output_parse_status") == "pass"
        and item.get("inferred_contract_quality") == "usable_candidate"
        and phase_status(item, "frama_parse") == "pass"
        and phase_status(item, "func") == "pass"
        and phase_status(item, "aux") == "pass"
        and phase_status(item, "wp") == "pass"
        and wp_goals_fully_proved(item, out_dir)
    )


def split_failed(item: dict[str, Any], out_dir: Path) -> bool:
    return any(phase_status(item, phase) in FAILED_STATUSES for phase in SPLIT_PHASES) or (
        phase_status(item, "wp") == "pass" and wp_goals_complete(item, out_dir) is False
    )


def observed_cell(item: dict[str, Any], out_dir: Path) -> str:
    parse = phase_status(item, "frama_parse")
    func = phase_status(item, "func")
    aux = phase_status(item, "aux")
    wp = phase_status(item, "wp")

    if end_to_end_passed(item, out_dir):
        return "supported_end_to_end"

    if parse in FAILED_STATUSES and (
        missing_platform_header(item, out_dir) is not None or str(item.get("kind", "")).startswith("original_")
    ):
        return "requires_harness"

    if parse in FAILED_STATUSES:
        return "failed_at_parse"
    if func in FAILED_STATUSES:
        return "failed_at_func"
    if func == "pass" and item.get("functional_backend_status") in {
        "translation_error",
        "parser_error",
        "solver_error",
        "missing_output",
    }:
        return "failed_at_func"
    if func == "pass" and item.get("saida_output_parse_status") in {"fail", "timeout", "missing"}:
        return "failed_at_func"
    if func == "pass" and (
        item.get("inference_evidence") == "missing_helper_contracts"
        or item.get("inferred_contract_quality") in {"missing", "syntactically_invalid", "vacuous_candidate"}
    ):
        return "failed_at_func"
    if func == "pass" and aux in FAILED_STATUSES:
        return "failed_at_aux"
    if func == "pass" and aux == "pass" and (
        wp in FAILED_STATUSES or (wp == "pass" and wp_goals_complete(item, out_dir) is False)
    ):
        return "failed_at_wp"

    if parse == "pass" and not split_was_run(item):
        return "parse_only"

    return "unknown"


def match_cell(item: dict[str, Any], out_dir: Path) -> str:
    expected = expected_cell(item)
    observed = observed_cell(item, out_dir)

    if expected == "supported":
        if observed == "supported_end_to_end":
            return "yes"
        if observed in {"parse_only", "unknown"}:
            return "unknown"
        return "no"

    if expected == "expected_unsupported":
        if split_failed(item, out_dir):
            return "yes"
        if observed == "supported_end_to_end":
            return "no"
        if observed in {"failed_at_parse", "requires_harness"}:
            return "no"
        return "unknown"

    return "-"


def conclusion_cell(item: dict[str, Any], out_dir: Path) -> str:
    expected = expected_cell(item)
    observed = observed_cell(item, out_dir)

    if expected == "expected_unsupported":
        if split_failed(item, out_dir):
            return "expected_unsupported"
        if observed == "supported_end_to_end":
            return "unexpected_pass"
        if observed in {"failed_at_parse", "requires_harness"}:
            return "unexpected_fail"
        return "unknown"

    return observed


def persist_classification_fields(item: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    item["observed"] = observed_cell(item, out_dir)
    item["match"] = match_cell(item, out_dir)
    item["conclusion"] = conclusion_cell(item, out_dir)
    item["process_first_failed_stage"] = process_first_failed_stage(item, out_dir)
    item["evidence_first_failed_stage"] = evidence_first_failed_stage(item, out_dir)
    item["wp_goals"] = wp_goals_cell(item, out_dir)
    item["functional_wp_goals"] = item["wp_goals"]
    if "rte_wp" in item.get("phases", {}):
        item["rte_wp_goals"] = rte_wp_goals_cell(item, out_dir)
        item["rte_result"] = rte_result_cell(item, out_dir)
        rte_phase = item["phases"].get("rte_wp", {})
        if isinstance(rte_phase, dict) and isinstance(rte_phase.get("rte_goal_breakdown"), dict):
            item["rte_goal_breakdown"] = rte_phase["rte_goal_breakdown"]
    item["phase_statuses"] = phase_status_map(item)
    if "rte_wp" in item.get("phases", {}):
        item["phase_statuses"]["rte_wp"] = phase_status(item, "rte_wp") or "unknown"
    return item


def executable(name: str, tool_dir: Path | None = None) -> str | None:
    if tool_dir is not None:
        candidate = tool_dir / name
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def framac_cpp_args(
    case: dict[str, Any],
    repo_root: Path,
    extra_include_dirs: list[Path] | None = None,
) -> list[str]:
    cpp_args: list[str] = []

    for include_dir in case.get("include_dirs", []):
        include_path = resolve_repo_path(repo_root, include_dir).resolve()
        cpp_args.append(f"-I{include_path}")
    for include_path in extra_include_dirs or []:
        cpp_args.append(f"-I{include_path.resolve()}")

    extra = case.get("cpp_extra_args", [])
    if isinstance(extra, str):
        extra_args = [extra]
    elif isinstance(extra, list):
        extra_args = [str(arg) for arg in extra]
    else:
        extra_args = []
    cpp_args.extend(extra_args)

    if not cpp_args:
        return []
    return [f"-cpp-extra-args={' '.join(shlex.quote(arg) for arg in cpp_args)}"]


def lib_entry_args(enabled: bool) -> list[str]:
    return ["-lib-entry"] if enabled else []


def lib_entry_main_args(case: dict[str, Any], enabled: bool) -> list[str]:
    return ["-main", case["entry_point"], "-lib-entry"] if enabled else []


def case_baseline_groups(case: dict[str, Any]) -> set[str]:
    groups: set[str] = set()
    single_group = case.get("baseline_group")
    if isinstance(single_group, str) and single_group:
        groups.add(single_group)
    extra_groups = case.get("baseline_groups", [])
    if isinstance(extra_groups, str) and extra_groups:
        groups.add(extra_groups)
    elif isinstance(extra_groups, list):
        groups.update(str(group) for group in extra_groups if str(group))
    return groups


def saida_tricera_args(case: dict[str, Any]) -> list[str]:
    value = case.get("saida_tricera_opts")
    if isinstance(value, str) and value.strip():
        return [f"-saida-tricera-opts={value.strip()}"]
    if isinstance(value, list):
        opts = [str(item) for item in value if str(item)]
        if opts:
            return [f"-saida-tricera-opts={' '.join(shlex.quote(item) for item in opts)}"]
    return []


def run_command(
    command: list[str],
    cwd: Path,
    timeout: int,
    stdout_path: Path,
    stderr_path: Path,
    exit_code_path: Path,
) -> dict[str, Any]:
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        stdout_path.write_text(completed.stdout, encoding="utf-8", errors="replace")
        stderr_path.write_text(completed.stderr, encoding="utf-8", errors="replace")
        exit_code_path.write_text(f"{completed.returncode}\n", encoding="utf-8")
        return {
            "status": "pass" if completed.returncode == 0 else "fail",
            "returncode": completed.returncode,
            "seconds": round(time.monotonic() - start, 3),
            "command": command,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "exit_code": str(exit_code_path),
        }
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "", encoding="utf-8", errors="replace")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8", errors="replace")
        exit_code_path.write_text("timeout\n", encoding="utf-8")
        return {
            "status": "timeout",
            "returncode": None,
            "seconds": round(time.monotonic() - start, 3),
            "command": command,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "exit_code": str(exit_code_path),
        }


def write_phase_result(phase_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    phase_dir.mkdir(parents=True, exist_ok=True)
    (phase_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def unknown_phase(
    phase: str,
    work_dir: Path,
    reason: str,
    command: list[str] | None = None,
) -> dict[str, Any]:
    phase_dir = work_dir / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = phase_dir / "stdout.txt"
    stderr_path = phase_dir / "stderr.txt"
    exit_code_path = phase_dir / "exit_code.txt"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    exit_code_path.write_text("unknown\n", encoding="utf-8")
    return write_phase_result(
        phase_dir,
        {
            "status": "unknown",
            "reason": reason,
            "returncode": None,
            "command": command,
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "exit_code": str(exit_code_path),
            "generated_files": [],
        },
    )


def parse_generated_saida_output(
    case: dict[str, Any],
    repo_root: Path,
    work_dir: Path,
    tool_dir: Path | None,
    timeout: int,
    lib_entry: bool,
) -> dict[str, Any]:
    generated_path = work_dir / "tmp_inferred_source_merged.c"
    if not generated_path.exists():
        return {"status": "missing", "returncode": None, "reason": "tmp_inferred_source_merged.c is missing"}

    tool = executable("frama-c", tool_dir)
    if tool is None:
        return {"status": "unknown", "returncode": None, "reason": "frama-c not found"}

    phase_dir = work_dir / "func"
    phase_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = phase_dir / "saida_output_parse_stdout.txt"
    stderr_path = phase_dir / "saida_output_parse_stderr.txt"
    exit_code_path = phase_dir / "saida_output_parse_exit_code.txt"
    command = [
        tool,
        "-quiet",
        *lib_entry_main_args(case, lib_entry),
        *framac_cpp_args(case, repo_root),
        generated_path.name,
    ]
    return run_command(command, work_dir, timeout, stdout_path, stderr_path, exit_code_path)


def run_tool_phase(
    phase: str,
    case: dict[str, Any],
    repo_root: Path,
    work_dir: Path,
    tool_dir: Path | None,
    timeout: int,
    lib_entry: bool,
) -> dict[str, Any]:
    source = resolve_repo_path(repo_root, case["path"]).resolve()
    phase_dir = work_dir / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = phase_dir / "stdout.txt"
    stderr_path = phase_dir / "stderr.txt"
    exit_code_path = phase_dir / "exit_code.txt"

    tool_names = {
        "frama_parse": "frama-c",
        "autodeduct_full": "autodeduct",
        "func": "frama-c",
        "aux": "frama-c",
        "wp": "frama-c",
        "rte_wp": "frama-c",
    }
    tool = executable(tool_names[phase], tool_dir)
    if tool is None:
        result = unknown_phase(phase, work_dir, f"{tool_names[phase]} not found")
        if phase == "func":
            enrich_saida_phase_result(result, case, repo_root, work_dir)
            return write_phase_result(work_dir / phase, result)
        return result

    if phase == "frama_parse":
        command = [
            tool,
            "-quiet",
            *lib_entry_main_args(case, lib_entry),
            *framac_cpp_args(case, repo_root),
            str(source),
        ]
        generated_outputs: list[Path] = []
    elif phase == "autodeduct_full":
        command = [tool, str(source)]
        generated_outputs = []
    elif phase == "func":
        func_source = source
        func_cpp_extra_include_dirs: list[Path] = []
        if source.exists():
            # Keep Saida temporary files in the case work directory, not beside
            # the repository source file.
            func_source = work_dir / source.name
            shutil.copyfile(source, func_source)
            func_cpp_extra_include_dirs.append(source.parent)
        generated_outputs = [
            work_dir / "tmp_inferred_source_merged.c",
            tricera_harness_file(case, repo_root, work_dir),
            tricera_result_file(case, repo_root, work_dir),
        ]
        command = [
            tool,
            "-saida",
            "-main",
            case["entry_point"],
            *lib_entry_args(lib_entry),
            "-saida-keep-tmp",
            "-saida-out=tmp_inferred_source_merged.c",
            *saida_tricera_args(case),
            *framac_cpp_args(case, repo_root, func_cpp_extra_include_dirs),
            func_source.name if func_source.parent == work_dir else str(func_source),
        ]
    elif phase == "aux":
        inferred = work_dir / "tmp_inferred_source_merged.c"
        if not inferred.exists():
            return unknown_phase(phase, work_dir, f"Missing Saida output: {inferred.name}")
        generated_outputs = [work_dir / "out.c"]
        command = [
            tool,
            "-isp",
            *lib_entry_main_args(case, lib_entry),
            "-isp-entry-point",
            case["entry_point"],
            *framac_cpp_args(case, repo_root),
            inferred.name,
            "-isp-print-file",
            "out.c",
        ]
    elif phase == "wp":
        annotated = work_dir / "out.c"
        if not annotated.exists():
            return unknown_phase(phase, work_dir, f"Missing ISP output: {annotated.name}")
        command = [
            tool,
            "-wp",
            "-main",
            case["entry_point"],
            *lib_entry_args(lib_entry),
            *framac_cpp_args(case, repo_root),
            annotated.name,
        ]
        generated_outputs = []
    elif phase == "rte_wp":
        annotated = work_dir / "out.c"
        if not annotated.exists():
            return unknown_phase(phase, work_dir, f"Missing ISP output: {annotated.name}")
        command = [
            tool,
            "-wp",
            "-wp-rte",
            "-main",
            case["entry_point"],
            *lib_entry_args(lib_entry),
            *framac_cpp_args(case, repo_root),
            annotated.name,
        ]
        generated_outputs = []
    else:
        raise ValueError(f"unknown phase {phase}")

    result = run_command(command, work_dir, timeout, stdout_path, stderr_path, exit_code_path)
    result["lib_entry"] = lib_entry
    result["generated_files"] = [
        str(path) for path in generated_outputs if result["status"] == "pass" and path.exists()
    ]
    if phase == "wp":
        result["wp_goals"] = extract_wp_goals_from_text(
            stdout_path.read_text(encoding="utf-8", errors="replace")
            + "\n"
            + stderr_path.read_text(encoding="utf-8", errors="replace")
        )
    if phase == "rte_wp":
        rte_text = (
            stdout_path.read_text(encoding="utf-8", errors="replace")
            + "\n"
            + stderr_path.read_text(encoding="utf-8", errors="replace")
        )
        result["rte_wp_goals"] = extract_wp_goals_from_text(rte_text)
        result["rte_goal_breakdown"] = extract_rte_goal_breakdown_from_text(rte_text)
    if phase == "func":
        if result["status"] == "pass":
            parse_result = parse_generated_saida_output(
                case,
                repo_root,
                work_dir,
                tool_dir,
                timeout,
                lib_entry,
            )
            result["saida_output_parse_status"] = parse_result["status"]
            result["saida_output_parse_returncode"] = parse_result.get("returncode")
            if "reason" in parse_result:
                result["saida_output_parse_reason"] = parse_result["reason"]
        enrich_saida_phase_result(result, case, repo_root, work_dir)
    return write_phase_result(phase_dir, result)


def format_feature_summary(features: dict[str, int]) -> str:
    interesting = [
        "acsl_blocks",
        "ghost_code",
        "predicates",
        "behaviors",
        "logic_definitions",
        "valid_pointer_clauses",
        "array_assigns",
        "pointer_syntax",
        "local_static_variables",
        "loops",
        "preprocessor_includes",
    ]
    parts = [f"{name}={features.get(name, 0)}" for name in interesting if features.get(name, 0)]
    return ", ".join(parts) if parts else "none"


def status_cell(results: dict[str, Any], phase: str) -> str:
    value = results.get(phase)
    if not value:
        return "unknown" if phase in {"func", "aux", "wp"} else "-"
    status = value.get("status", "-")
    if status == "fail":
        return f"fail({value.get('returncode')})"
    if status == "unknown":
        return "unknown"
    if status == "timeout":
        return "timeout"
    return status


def list_cell(values: Any) -> str:
    if isinstance(values, list):
        return ", ".join(str(value) for value in values) if values else "-"
    if isinstance(values, str) and values:
        return values
    return "-"


def write_summary(results: list[dict[str, Any]], out_dir: Path) -> None:
    lines = [
        "# AutoDeduct support test summary",
        "",
        "This file is generated by `autodeduct-support/run_support_tests.py`.",
        "",
        "| Case | Module | Kind | Probe role | Expected | Observed | Match | LOC | Static feature highlights | Risks | Frama-C parse | AutoDeduct | Func / Saida | Inference evidence | Aux / ISP | Functional WP | Functional WP goals | RTE WP | RTE WP goals | RTE result | Conclusion |",
        "|---|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in results:
        persist_classification_fields(item, out_dir)
        static = item["static"]
        risks = "<br>".join(static["risk_notes"]) if static["risk_notes"] else ""
        lines.append(
            "| {id} | {module} | {kind} | {ownership} | {expected} | {observed} | {match} | {loc} | {features} | {risks} | {frama} | {full} | {func} | {inference} | {aux} | {wp} | {wp_goals} | {rte_wp} | {rte_wp_goals} | {rte_result} | {conclusion} |".format(
                id=item["id"],
                module=item["module"],
                kind=item["kind"],
                ownership=probe_role_cell(item),
                expected=expected_cell(item),
                observed=item["observed"],
                match=item["match"],
                loc=static["loc"],
                features=format_feature_summary(static["features"]),
                risks=risks,
                frama=status_cell(item["phases"], "frama_parse"),
                full=status_cell(item["phases"], "autodeduct_full"),
                func=status_cell(item["phases"], "func"),
                inference=item.get("inference_evidence", "unclear"),
                aux=status_cell(item["phases"], "aux"),
                wp=status_cell(item["phases"], "wp"),
                wp_goals=item["wp_goals"],
                rte_wp=status_cell(item["phases"], "rte_wp"),
                rte_wp_goals=item.get("rte_wp_goals", "-"),
                rte_result=item.get("rte_result", "not_run"),
                conclusion=item["conclusion"],
            )
        )
    lines.extend(
        [
            "",
            "## How to read this",
            "",
            "`pass` means the phase exited with code 0. `fail(n)` means the tool ran and returned exit code `n`. `unknown` means the phase was not run because its tool or prerequisite output was unavailable. Inspect the corresponding phase directory under the case directory for stdout, stderr, exit code, generated files, and `result.json`.",
            "",
            "`Func / Saida` remains the process status. `Inference evidence` is separate and is derived from Func stderr plus `tmp_inferred_source_merged.c`.",
            "",
            "`supported_end_to_end` requires Frama-C parse, Saida, ISP, and WP to pass, and WP must report a nonzero goal total with every goal proved. `parse_only` means only the parse check has passed so far. `requires_harness` marks original sources whose parse logs show missing platform headers or known external dependencies.",
            "",
            "For `expected_unsupported` cases, `expected_unsupported` means a known support-boundary test failed in Saida, ISP, or WP. `unexpected_pass` means a boundary test passed end to end. `unexpected_fail` means it failed before the intended split-pipeline boundary.",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def phase_passed_with_output(result: dict[str, Any], output_path: Path) -> bool:
    return result.get("status") == "pass" and output_path.exists()


def selected_cases(
    all_cases: list[dict[str, Any]],
    ids: list[str] | None,
    modules: list[str] | None,
    kinds: list[str] | None,
    exclude_kinds: list[str] | None,
    baseline_groups: list[str] | None,
) -> list[dict[str, Any]]:
    if not ids:
        cases = list(all_cases)
    else:
        wanted = set(ids)
        cases = [case for case in all_cases if case["id"] in wanted]
        missing = sorted(wanted - {case["id"] for case in cases})
        if missing:
            raise SystemExit(f"Unknown case id(s): {', '.join(missing)}")

    if modules:
        allowed_modules = set(modules)
        cases = [case for case in cases if case["module"] in allowed_modules]
    if kinds:
        allowed = set(kinds)
        cases = [case for case in cases if case["kind"] in allowed]
    if exclude_kinds:
        excluded = set(exclude_kinds)
        cases = [case for case in cases if case["kind"] not in excluded]
    if baseline_groups:
        allowed_groups = set(baseline_groups)
        cases = [case for case in cases if case_baseline_groups(case) & allowed_groups]
    return cases


def run_parser_self_tests() -> None:
    source = """int helper(int value)
{
    return value < 0 ? 0 : value;
}

/*@
  ensures \\result >= 0;
*/
int entry(int value)
{
    return helper(value);
}
"""
    generated = """/*@
  requires \\true;
  ensures \\result >= 0;
*/
int helper(int value)
{
    return value < 0 ? 0 : value;
}

/*@
  ensures \\result >= 0;
*/
int entry(int value)
{
    return helper(value);
}
"""
    counts = inspect_generated_inference(source, generated, "entry")
    assert counts["inferred_helper_contract_count"] == 1
    assert counts["missing_inferred_contract_count"] == 0
    assert (
        inference_evidence_value(
            tricera_error_detected=False,
            inferred_helper_contract_count=1,
            missing_inferred_contract_count=0,
            helper_function_count=1,
            unannotated_helper_function_count=1,
            manually_annotated_helper_count=0,
        )
        == "inferred_helpers"
    )

    missing_generated = """//No inferred contract found for helper
int helper(int value)
{
    return value;
}

/*@
  ensures \\result == value;
*/
int entry(int value)
{
    return helper(value);
}
"""
    counts = inspect_generated_inference(source, missing_generated, "entry")
    assert counts["inferred_helper_contract_count"] == 0
    assert counts["missing_inferred_contract_count"] == 1
    assert (
        inference_evidence_value(
            tricera_error_detected=False,
            inferred_helper_contract_count=0,
            missing_inferred_contract_count=1,
            helper_function_count=1,
            unannotated_helper_function_count=1,
            manually_annotated_helper_count=0,
        )
        == "missing_helper_contracts"
    )

    entry_only_source = """/*@
  ensures \\result == value;
*/
int entry(int value)
{
    return value;
}
"""
    assert unannotated_helper_names(entry_only_source, "entry") == []
    assert (
        inference_evidence_value(
            tricera_error_detected=False,
            inferred_helper_contract_count=0,
            missing_inferred_contract_count=0,
            helper_function_count=0,
            unannotated_helper_function_count=0,
            manually_annotated_helper_count=0,
        )
        == "no_helpers_to_infer"
    )

    assert (
        inference_evidence_value(
            tricera_error_detected=False,
            inferred_helper_contract_count=0,
            missing_inferred_contract_count=0,
            helper_function_count=1,
            unannotated_helper_function_count=0,
            manually_annotated_helper_count=1,
        )
        == "manually_annotated_helper"
    )

    assert detect_tricera_error("TriCera parser error: syntax error near token")
    assert detect_tricera_error("line 3:7 mismatched input '}' expecting ID")
    assert not detect_tricera_error("Frama-C warning: user annotation was not proved")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test-parsers", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--repo-root", type=Path, default=repo_root_from_script())
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--out", type=Path, default=Path("autodeduct-support-results"))
    parser.add_argument("--case", dest="case_ids", action="append", help="Run only one case id. May be repeated.")
    parser.add_argument("--module", dest="modules", action="append", help="Run only cases for this module. May be repeated.")
    parser.add_argument("--kind", action="append", help="Run only cases with this kind. May be repeated.")
    parser.add_argument("--exclude-kind", action="append", help="Exclude cases with this kind. May be repeated.")
    parser.add_argument("--baseline-group", action="append", help="Run only cases in this baseline group. May be repeated.")
    parser.add_argument("--tool-dir", type=Path, help="Directory containing autodeduct scripts, if they are not in PATH.")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--run-framac", action="store_true", help="Run `frama-c -quiet` parse checks.")
    parser.add_argument("--run-full", action="store_true", help="Run the one-shot `autodeduct` command.")
    parser.add_argument("--run-split", action="store_true", help="Run `frama-c -saida`, `frama-c -isp`, and `frama-c -wp`.")
    parser.add_argument("--run-rte-wp", action="store_true", help="Run separate `frama-c -wp -wp-rte` RTE proof on generated out.c.")
    parser.add_argument("--lib-entry", action="store_true", help="Pass `-lib-entry` to Frama-C split-pipeline phases.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.self_test_parsers:
        run_parser_self_tests()
        print("Parser self-tests passed")
        return 0

    repo_root = args.repo_root.resolve()
    out_dir = (repo_root / args.out).resolve() if not args.out.is_absolute() else args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_cases = load_cases(args.cases)
    cases = selected_cases(all_cases, args.case_ids, args.modules, args.kind, args.exclude_kind, args.baseline_group)
    fresh_phase_run = args.run_framac or args.run_full or args.run_split or args.run_rte_wp

    run_results: list[dict[str, Any]] = []

    for case in cases:
        case_out = out_dir / case["id"]
        case_out.mkdir(parents=True, exist_ok=True)
        print(f"[{case['id']}] static scan", flush=True)
        item = fresh_case_result(case, repo_root, out_dir) if fresh_phase_run else merged_case_result(case, repo_root, out_dir)
        if fresh_phase_run:
            item["lib_entry"] = args.lib_entry

        if args.run_framac:
            print(f"[{case['id']}] frama-c parse", flush=True)
            item["phases"]["frama_parse"] = run_tool_phase(
                "frama_parse", case, repo_root, case_out, args.tool_dir, args.timeout, args.lib_entry
            )
        if args.run_full:
            print(f"[{case['id']}] autodeduct full", flush=True)
            item["phases"]["autodeduct_full"] = run_tool_phase(
                "autodeduct_full", case, repo_root, case_out, args.tool_dir, args.timeout, args.lib_entry
            )
        if args.run_split:
            print(f"[{case['id']}] func / saida", flush=True)
            item["phases"]["func"] = run_tool_phase(
                "func", case, repo_root, case_out, args.tool_dir, args.timeout, args.lib_entry
            )

            saida_out = case_out / "tmp_inferred_source_merged.c"
            if phase_passed_with_output(item["phases"]["func"], saida_out):
                print(f"[{case['id']}] aux / isp", flush=True)
                item["phases"]["aux"] = run_tool_phase(
                    "aux", case, repo_root, case_out, args.tool_dir, args.timeout, args.lib_entry
                )
            else:
                item["phases"]["aux"] = unknown_phase(
                    "aux", case_out, "Saida did not pass and produce tmp_inferred_source_merged.c"
                )

            isp_out = case_out / "out.c"
            if phase_passed_with_output(item["phases"]["aux"], isp_out):
                print(f"[{case['id']}] wp", flush=True)
                item["phases"]["wp"] = run_tool_phase(
                    "wp", case, repo_root, case_out, args.tool_dir, args.timeout, args.lib_entry
                )
            else:
                item["phases"]["wp"] = unknown_phase(
                    "wp", case_out, "ISP did not pass and produce out.c"
                )
        if args.run_rte_wp:
            isp_out = case_out / "out.c"
            if isp_out.exists():
                print(f"[{case['id']}] rte wp", flush=True)
                item["phases"]["rte_wp"] = run_tool_phase(
                    "rte_wp", case, repo_root, case_out, args.tool_dir, args.timeout, args.lib_entry
                )
            else:
                item["phases"]["rte_wp"] = unknown_phase(
                    "rte_wp", case_out, "ISP did not produce out.c for RTE WP"
                )

        persist_classification_fields(enrich_case_evidence(item, case, repo_root, case_out), out_dir)
        (case_out / "result.json").write_text(json.dumps(item, indent=2), encoding="utf-8")
        run_results.append(item)

    results = run_results if fresh_phase_run else all_merged_results(cases, repo_root, out_dir)
    (out_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_summary(results, out_dir)
    print(f"Wrote {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
