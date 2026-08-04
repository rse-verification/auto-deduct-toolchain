#!/usr/bin/env python3
"""Write a sanitized AutoDeduct result snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PHASES = ("frama_parse", "autodeduct_full", "func", "aux", "wp")
ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(?:/[^\s:;,)\]\"']+)+")
METADATA_FIELDS = (
    "module",
    "kind",
    "probe_role",
    "evidence_tier",
    "evidence_role",
    "expected_support",
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
    "saida_tricera_opts",
)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def read_results(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return [item for item in data["results"] if isinstance(item, dict)]
    raise ValueError(f"unsupported results format: {path}")


def load_case_metadata(repo_root: Path) -> dict[str, dict[str, Any]]:
    path = repo_root / "autodeduct-support" / "cases.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        return {}
    return {
        str(case["id"]): case
        for case in cases
        if isinstance(case, dict) and isinstance(case.get("id"), str)
    }


def source_sha256(item: dict[str, Any], repo_root: Path) -> str | None:
    existing = item.get("source_sha256")
    if isinstance(existing, str) and existing:
        return existing
    raw_path = item.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phase_statuses(item: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    stored = item.get("phase_statuses")
    phases = item.get("phases", {})
    for phase in PHASES:
        status = None
        if isinstance(stored, dict) and isinstance(stored.get(phase), str):
            status = stored[phase]
        elif isinstance(phases, dict) and isinstance(phases.get(phase), dict):
            value = phases[phase].get("status")
            if isinstance(value, str):
                status = value
        statuses[phase] = status or "unknown"
    if (
        (isinstance(stored, dict) and "rte_wp" in stored)
        or (isinstance(phases, dict) and "rte_wp" in phases)
    ):
        status = None
        if isinstance(stored, dict) and isinstance(stored.get("rte_wp"), str):
            status = stored["rte_wp"]
        elif isinstance(phases, dict) and isinstance(phases.get("rte_wp"), dict):
            value = phases["rte_wp"].get("status")
            if isinstance(value, str):
                status = value
        statuses["rte_wp"] = status or "unknown"
    return statuses


def has_executed_phase(item: dict[str, Any]) -> bool:
    return any(status != "unknown" for status in phase_statuses(item).values())


def wp_goals(item: dict[str, Any]) -> str:
    value = item.get("wp_goals")
    if isinstance(value, str):
        return value
    phases = item.get("phases", {})
    if isinstance(phases, dict) and isinstance(phases.get("wp"), dict):
        phase_value = phases["wp"].get("wp_goals")
        if isinstance(phase_value, str):
            return phase_value
    return "-"


def rte_wp_goals(item: dict[str, Any]) -> str:
    value = item.get("rte_wp_goals")
    if isinstance(value, str):
        return value
    phases = item.get("phases", {})
    if isinstance(phases, dict) and isinstance(phases.get("rte_wp"), dict):
        phase_value = phases["rte_wp"].get("rte_wp_goals")
        if isinstance(phase_value, str):
            return phase_value
    return "-"


def rte_goal_breakdown(item: dict[str, Any]) -> dict[str, Any] | None:
    value = item.get("rte_goal_breakdown")
    if isinstance(value, dict):
        return value
    phases = item.get("phases", {})
    if isinstance(phases, dict) and isinstance(phases.get("rte_wp"), dict):
        phase_value = phases["rte_wp"].get("rte_goal_breakdown")
        if isinstance(phase_value, dict):
            return phase_value
    return None


def phase_or_top_level_value(item: dict[str, Any], key: str, phase: str = "func", default: Any = None) -> Any:
    if key in item:
        return item.get(key)
    phases = item.get("phases", {})
    if isinstance(phases, dict) and isinstance(phases.get(phase), dict):
        return phases[phase].get(key, default)
    return default


def sanitize_text_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return ABSOLUTE_PATH_RE.sub("<path>", value)


def lib_entry_value(item: dict[str, Any]) -> bool | None:
    value = item.get("lib_entry")
    if isinstance(value, bool):
        return value

    phases = item.get("phases", {})
    if not isinstance(phases, dict):
        return None
    phase_values = [
        phase.get("lib_entry")
        for phase in phases.values()
        if isinstance(phase, dict) and isinstance(phase.get("lib_entry"), bool)
    ]
    if phase_values and all(value is True for value in phase_values):
        return True
    if phase_values and all(value is False for value in phase_values):
        return False
    return None


def merged_metadata(item: dict[str, Any], case_metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    metadata = case_metadata.get(str(item.get("id")), {})
    merged: dict[str, Any] = {}
    for field in METADATA_FIELDS:
        value = metadata.get(field) if isinstance(metadata, dict) and field in metadata else item.get(field)
        merged[field] = value
    if not merged.get("evaluation_profile"):
        merged["evaluation_profile"] = (
            "configured_tricera_profile" if merged.get("saida_tricera_opts") else "strict_library_profile"
        )
    if not merged.get("direct_or_rewrite_relation"):
        rewrite_of = merged.get("rewrite_of")
        merged["direct_or_rewrite_relation"] = f"rewrite_of:{rewrite_of}" if rewrite_of else "direct"
    return merged


def sanitize_result(
    item: dict[str, Any],
    repo_root: Path,
    case_metadata: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    metadata = merged_metadata(item, case_metadata or {})
    return {
        "id": item.get("id"),
        "source_sha256": source_sha256(item, repo_root),
        "module": metadata["module"],
        "kind": metadata["kind"],
        "probe_role": metadata["probe_role"],
        "evidence_tier": metadata["evidence_tier"],
        "evidence_role": metadata["evidence_role"],
        "expected_support": metadata["expected_support"],
        "rewrite_of": metadata["rewrite_of"],
        "baseline_group": metadata["baseline_group"],
        "baseline_groups": metadata["baseline_groups"],
        "helper_inference_claim": metadata["helper_inference_claim"],
        "paper_model_input_classification": metadata["paper_model_input_classification"],
        "source_visibility": metadata["source_visibility"],
        "public_export": metadata["public_export"],
        "feature_location": metadata["feature_location"],
        "paper_limit": metadata["paper_limit"],
        "evaluation_profile": metadata["evaluation_profile"],
        "direct_or_rewrite_relation": metadata["direct_or_rewrite_relation"],
        "saida_tricera_opts": metadata["saida_tricera_opts"],
        "observed": item.get("observed"),
        "conclusion": item.get("conclusion"),
        "inference_evidence": item.get("inference_evidence"),
        "inferred_helper_contract_count": item.get("inferred_helper_contract_count", 0),
        "missing_inferred_contract_count": item.get("missing_inferred_contract_count", 0),
        "saida_output_parse_status": item.get("saida_output_parse_status", "unknown"),
        "inferred_contract_quality": item.get("inferred_contract_quality", "unknown"),
        "suspicious_contract_markers": item.get("suspicious_contract_markers", []),
        "inferred_contract_quality_reason": item.get(
            "inferred_contract_quality_reason", "not enough generated Saida output evidence"
        ),
        "functional_backend_status": phase_or_top_level_value(item, "functional_backend_status", default="unknown"),
        "functional_backend_error_kind": phase_or_top_level_value(item, "functional_backend_error_kind"),
        "functional_backend_error_text": sanitize_text_value(
            phase_or_top_level_value(item, "functional_backend_error_text")
        ),
        "tricera_result_present": phase_or_top_level_value(item, "tricera_result_present", default=False),
        "process_first_failed_stage": item.get("process_first_failed_stage", "-"),
        "evidence_first_failed_stage": item.get("evidence_first_failed_stage", "-"),
        "lib_entry": lib_entry_value(item),
        "phase_statuses": phase_statuses(item),
        "wp_goals": wp_goals(item),
        "functional_wp_goals": item.get("functional_wp_goals", wp_goals(item)),
        "rte_wp_goals": rte_wp_goals(item),
        "rte_result": item.get("rte_result", "not_run"),
        "rte_goal_breakdown": rte_goal_breakdown(item),
    }


def export_results(
    input_path: Path,
    output_path: Path,
    repo_root: Path,
    *,
    include_unexecuted: bool = False,
) -> list[dict[str, Any]]:
    case_metadata = load_case_metadata(repo_root)
    sanitized = [
        sanitize_result(item, repo_root, case_metadata)
        for item in read_results(input_path)
        if include_unexecuted or has_executed_phase(item)
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sanitized


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", metavar="INPUT", type=Path, help="Raw results.json file to read.")
    parser.add_argument("output", metavar="OUTPUT", type=Path, help="Sanitized JSON file to write.")
    parser.add_argument(
        "--repo-root",
        metavar="ROOT",
        type=Path,
        default=repo_root_from_script(),
        help="Repository root used to resolve relative source paths.",
    )
    parser.add_argument(
        "--include-unexecuted",
        action="store_true",
        help="Keep rows where every phase status is unknown.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    input_path = args.input if args.input.is_absolute() else repo_root / args.input
    output_path = args.output if args.output.is_absolute() else repo_root / args.output
    export_results(input_path, output_path, repo_root, include_unexecuted=args.include_unexecuted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
