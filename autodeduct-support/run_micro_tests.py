#!/usr/bin/env python3
"""Run the public micro-test support checks."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ENTRY_POINT = "entry"
PHASES = ("frama_parse", "func", "aux", "wp")
WP_GOALS_RE = re.compile(r"Proved goals:\s*(\d+)\s*/\s*(\d+)")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def cases_path_from_script() -> Path:
    return Path(__file__).resolve().with_name("cases.json")


def load_micro_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return [case for case in data["cases"] if case.get("module") == "micro"]


def selected_cases(
    cases: list[dict[str, Any]],
    case_ids: list[str] | None,
    kinds: list[str] | None,
) -> list[dict[str, Any]]:
    selected = list(cases)

    if case_ids:
        wanted = set(case_ids)
        selected = [case for case in selected if case["id"] in wanted]
        missing = sorted(wanted - {case["id"] for case in selected})
        if missing:
            raise SystemExit(f"Unknown micro case id(s): {', '.join(missing)}")

    if kinds:
        wanted_kinds = set(kinds)
        selected = [case for case in selected if case["kind"] in wanted_kinds]

    return selected


def executable(name: str) -> str | None:
    return shutil.which(name)


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


def phase_result_dir(case_dir: Path, phase: str) -> Path:
    phase_dir = case_dir / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    return phase_dir


def write_result(path: Path, result: dict[str, Any]) -> dict[str, Any]:
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def unknown_phase(case_dir: Path, phase: str, reason: str) -> dict[str, Any]:
    phase_dir = phase_result_dir(case_dir, phase)
    stdout_path = phase_dir / "stdout.txt"
    stderr_path = phase_dir / "stderr.txt"
    exit_code_path = phase_dir / "exit_code.txt"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    exit_code_path.write_text("unknown\n", encoding="utf-8")
    result = {
        "status": "unknown",
        "reason": reason,
        "returncode": None,
        "command": None,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "exit_code": str(exit_code_path),
        "generated_files": [],
    }
    return write_result(phase_dir / "result.json", result)


def phase_passed_with_output(result: dict[str, Any], output_path: Path) -> bool:
    return result.get("status") == "pass" and output_path.exists()


def extract_wp_goals(text: str) -> str:
    match = WP_GOALS_RE.search(text)
    if match is None:
        return "-"
    return f"{match.group(1)}/{match.group(2)}"


def run_phase(
    phase: str,
    case: dict[str, Any],
    repo_root: Path,
    case_dir: Path,
    timeout: int,
) -> dict[str, Any]:
    tool = executable("frama-c")
    if tool is None:
        return unknown_phase(case_dir, phase, "frama-c not found")

    source = (repo_root / case["path"]).resolve()
    phase_dir = phase_result_dir(case_dir, phase)
    stdout_path = phase_dir / "stdout.txt"
    stderr_path = phase_dir / "stderr.txt"
    exit_code_path = phase_dir / "exit_code.txt"

    if phase == "frama_parse":
        command = [tool, "-quiet", str(source)]
        generated: list[Path] = []
    elif phase == "func":
        command = [
            tool,
            "-saida",
            "-main",
            ENTRY_POINT,
            "-saida-out=tmp_inferred_source_merged.c",
            str(source),
        ]
        generated = [case_dir / "tmp_inferred_source_merged.c"]
    elif phase == "aux":
        inferred = case_dir / "tmp_inferred_source_merged.c"
        if not inferred.exists():
            return unknown_phase(case_dir, phase, "missing Saida output")
        command = [
            tool,
            "-isp",
            "-isp-entry-point",
            ENTRY_POINT,
            inferred.name,
            "-isp-print-file",
            "out.c",
        ]
        generated = [case_dir / "out.c"]
    elif phase == "wp":
        annotated = case_dir / "out.c"
        if not annotated.exists():
            return unknown_phase(case_dir, phase, "missing ISP output")
        command = [tool, "-wp", "-main", ENTRY_POINT, annotated.name]
        generated = []
    else:
        raise ValueError(f"unknown phase {phase}")

    result = run_command(command, case_dir, timeout, stdout_path, stderr_path, exit_code_path)
    result["generated_files"] = [
        str(path) for path in generated if result["status"] == "pass" and path.exists()
    ]
    if phase == "wp":
        result["wp_goals"] = extract_wp_goals(
            stdout_path.read_text(encoding="utf-8", errors="replace")
            + "\n"
            + stderr_path.read_text(encoding="utf-8", errors="replace")
        )
    return write_result(phase_dir / "result.json", result)


def status_cell(phases: dict[str, Any], phase: str) -> str:
    result = phases.get(phase)
    if not isinstance(result, dict):
        return "unknown" if phase != "frama_parse" else "-"
    status = result.get("status", "unknown")
    if status == "fail":
        return f"fail({result.get('returncode')})"
    return str(status)


def wp_goals(phases: dict[str, Any]) -> str:
    result = phases.get("wp")
    if isinstance(result, dict) and isinstance(result.get("wp_goals"), str):
        return result["wp_goals"]
    return "-"


def goals_complete(goals: str) -> bool | None:
    match = re.fullmatch(r"(\d+)/(\d+)", goals)
    if match is None:
        return None
    return int(match.group(1)) == int(match.group(2))


def observed(phases: dict[str, Any]) -> str:
    parse = status_cell(phases, "frama_parse")
    func = status_cell(phases, "func")
    aux = status_cell(phases, "aux")
    wp = status_cell(phases, "wp")
    complete = goals_complete(wp_goals(phases))

    if parse == "pass" and func == "pass" and aux == "pass" and wp == "pass" and complete is not False:
        return "supported_end_to_end"
    if parse.startswith("fail") or parse == "timeout":
        return "failed_at_parse"
    if func.startswith("fail") or func == "timeout":
        return "failed_at_func"
    if aux.startswith("fail") or aux == "timeout":
        return "failed_at_aux"
    if wp.startswith("fail") or wp == "timeout" or (wp == "pass" and complete is False):
        return "failed_at_wp"
    if parse == "pass" and func == "unknown" and aux == "unknown" and wp == "unknown":
        return "parse_only"
    return "unknown"


def expected(case: dict[str, Any]) -> str:
    value = case.get("expected_support", "-")
    return value if isinstance(value, str) else "-"


def match_cell(case: dict[str, Any], phases: dict[str, Any]) -> str:
    exp = expected(case)
    obs = observed(phases)
    if exp == "supported":
        if obs == "supported_end_to_end":
            return "yes"
        if obs in {"unknown", "parse_only"}:
            return "unknown"
        return "no"
    if exp == "expected_unsupported":
        if obs in {"failed_at_func", "failed_at_aux", "failed_at_wp"}:
            return "yes"
        if obs == "supported_end_to_end":
            return "no"
        if obs in {"failed_at_parse"}:
            return "no"
        return "unknown"
    return "-"


def conclusion(case: dict[str, Any], phases: dict[str, Any]) -> str:
    exp = expected(case)
    obs = observed(phases)
    if exp == "expected_unsupported":
        if obs in {"failed_at_func", "failed_at_aux", "failed_at_wp"}:
            return "expected_unsupported"
        if obs == "supported_end_to_end":
            return "unexpected_pass"
        if obs == "failed_at_parse":
            return "unexpected_fail"
        return "unknown"
    return obs


def result_item(case: dict[str, Any], phases: dict[str, Any]) -> dict[str, Any]:
    item = {
        "id": case["id"],
        "module": "micro",
        "path": case["path"],
        "kind": case["kind"],
        "entry_point": ENTRY_POINT,
        "expected_support": expected(case),
        "observed": observed(phases),
        "match": match_cell(case, phases),
        "conclusion": conclusion(case, phases),
        "phases": phases,
    }
    if "expected_reason" in case:
        item["expected_reason"] = case["expected_reason"]
    return item


def write_summary(items: list[dict[str, Any]], out_dir: Path) -> None:
    lines = [
        "# Micro-Test Summary",
        "",
        "| Case | Kind | Expected | Observed | Match | Frama-C parse | Func / Saida | Aux / ISP | WP | WP goals | Conclusion |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in items:
        phases = item["phases"]
        lines.append(
            "| {case} | {kind} | {expected} | {observed} | {match} | {parse} | {func} | {aux} | {wp} | {goals} | {conclusion} |".format(
                case=item["id"],
                kind=item["kind"],
                expected=item["expected_support"],
                observed=item["observed"],
                match=item["match"],
                parse=status_cell(phases, "frama_parse"),
                func=status_cell(phases, "func"),
                aux=status_cell(phases, "aux"),
                wp=status_cell(phases, "wp"),
                goals=wp_goals(phases),
                conclusion=item["conclusion"],
            )
        )
    lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-framac", action="store_true", help="Run Frama-C parse checks.")
    parser.add_argument("--run-split", action="store_true", help="Run Saida, ISP, and WP.")
    parser.add_argument("--case", dest="case_ids", action="append", help="Run one micro-test case id. May be repeated.")
    parser.add_argument("--kind", action="append", help="Run one micro-test kind. May be repeated.")
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    repo_root = repo_root_from_script()
    out_dir = repo_root / "autodeduct-support-results" / "public-micro"
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = selected_cases(load_micro_cases(cases_path_from_script()), args.case_ids, args.kind)
    items = []

    for case in cases:
        case_dir = out_dir / case["id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        phases: dict[str, Any] = {}

        print(f"[{case['id']}] selected", flush=True)
        if args.run_framac:
            print(f"[{case['id']}] frama-c parse", flush=True)
            phases["frama_parse"] = run_phase("frama_parse", case, repo_root, case_dir, args.timeout)

        if args.run_split:
            print(f"[{case['id']}] func / saida", flush=True)
            phases["func"] = run_phase("func", case, repo_root, case_dir, args.timeout)

            if phase_passed_with_output(phases["func"], case_dir / "tmp_inferred_source_merged.c"):
                print(f"[{case['id']}] aux / isp", flush=True)
                phases["aux"] = run_phase("aux", case, repo_root, case_dir, args.timeout)
            else:
                phases["aux"] = unknown_phase(case_dir, "aux", "Saida did not produce output")

            if phase_passed_with_output(phases["aux"], case_dir / "out.c"):
                print(f"[{case['id']}] wp", flush=True)
                phases["wp"] = run_phase("wp", case, repo_root, case_dir, args.timeout)
            else:
                phases["wp"] = unknown_phase(case_dir, "wp", "ISP did not produce output")

        item = result_item(case, phases)
        write_result(case_dir / "result.json", item)
        items.append(item)

    write_result(out_dir / "results.json", items)
    write_summary(items, out_dir)
    print(f"Wrote {out_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
