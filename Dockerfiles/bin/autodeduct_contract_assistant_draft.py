"""Draft contract application helpers for the AutoDeduct GUI."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from autodeduct_contract_assistant_framac import run_frama_c_on_paths
from autodeduct_contract_assistant_project import (
    display_path,
    safe_relative_path,
    source_paths_from_project_path,
)


def strip_markdown_code_fence(contract: str) -> str:
    stripped = contract.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def ensure_no_nested_block_comment(contract: str) -> None:
    if "/*" in contract or "*/" in contract:
        raise ValueError(
            "Draft contract contains nested C block-comment markers. "
            "Edit the draft so the contract is one ACSL block comment only."
        )


def normalize_contract(contract: str) -> str:
    stripped = strip_markdown_code_fence(contract)
    if stripped.startswith("/*"):
        if not stripped.startswith("/*@"):
            raise ValueError(
                "Draft contract must be an ACSL block comment starting with /*@, "
                "not a regular C comment."
            )
        if not stripped.endswith("*/"):
            raise ValueError("Draft ACSL block comment is missing its closing */")
        ensure_no_nested_block_comment(stripped[3:-2])
        return stripped + "\n"

    ensure_no_nested_block_comment(stripped)
    lines = ["/*@"]
    for line in stripped.splitlines():
        lines.append("  " + line.strip())
    lines.append("*/")
    return "\n".join(lines) + "\n"


def draft_suggestions(draft: object) -> list[dict[str, str]]:
    if not isinstance(draft, dict):
        raise ValueError("LLM draft must be a JSON object")
    suggestions = draft.get("suggestions")
    if not isinstance(suggestions, list):
        raise ValueError("LLM draft must contain a suggestions array")

    result: list[dict[str, str]] = []
    for item in suggestions:
        if not isinstance(item, dict):
            raise ValueError("Each LLM suggestion must be an object")
        file_name = item.get("file")
        function_name = item.get("function")
        contract = item.get("contract")
        values = (file_name, function_name, contract)
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError("Each LLM suggestion must include file, function, and contract strings")
        result.append(
            {
                "file": file_name.strip(),
                "function": function_name.strip(),
                "contract": normalize_contract(contract),
            }
        )
    return result


def apply_contract_draft_to_copy(
    original_root: Path, copy_root: Path, reports: list[Any], draft: object
) -> int:
    targets: dict[tuple[str, str], Any] = {}
    for report in reports:
        relative = display_path(report.path, original_root)
        for function in report.missing_helper_contracts:
            targets[(relative, function.name)] = function

    grouped: dict[str, list[tuple[int, str]]] = {}
    for suggestion in draft_suggestions(draft):
        key = (suggestion["file"], suggestion["function"])
        function = targets.get(key)
        if function is None:
            raise ValueError(
                f"LLM suggestion does not match a missing helper contract: {key[0]}:{key[1]}"
            )
        grouped.setdefault(suggestion["file"], []).append(
            (function.start, suggestion["contract"])
        )

    for relative, inserts in grouped.items():
        target = copy_root / safe_relative_path(relative)
        if not target.exists():
            raise FileNotFoundError(f"Draft target file not found in temporary copy: {relative}")
        text = target.read_text(encoding="utf-8")
        for index, contract in sorted(inserts, reverse=True):
            text = text[:index] + contract + text[index:]
        target.write_text(text, encoding="utf-8")

    return sum(len(inserts) for inserts in grouped.values())


def copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {".git", "_build", "node_modules", "__pycache__"}
    return {name for name in names if name in ignored}


def run_frama_c_project_path_with_draft(
    project_path: str,
    mode: str,
    draft: object,
    assistant: Any,
    extra_args: str | list[str] | None = None,
) -> dict[str, object]:
    original_root, source_paths = source_paths_from_project_path(project_path, assistant)
    reports = assistant.analyze_files(source_paths, include_main=False)
    with tempfile.TemporaryDirectory(prefix="autodeduct-contract-draft-") as tmpdir:
        copy_root = Path(tmpdir) / "project"
        shutil.copytree(original_root, copy_root, ignore=copy_ignore)
        applied = apply_contract_draft_to_copy(original_root, copy_root, reports, draft)
        copied_c_files = [
            copy_root / path.relative_to(original_root)
            for path in source_paths
            if path.suffix.lower() == ".c"
        ]
        response = run_frama_c_on_paths(
            copy_root,
            copied_c_files,
            len(source_paths),
            mode,
            extra_args,
            "Use temporary draft copy",
        )
        response["draft_contracts_applied"] = applied
        response["output"] = (
            f"Applied {applied} draft contract(s) to a temporary copy. "
            "Original mounted files were not modified.\n\n"
            + str(response["output"])
        )
        return response
