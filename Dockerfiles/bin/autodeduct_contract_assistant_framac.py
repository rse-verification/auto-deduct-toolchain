"""Frama-C execution helpers for the AutoDeduct contract assistant GUI."""

from __future__ import annotations

import shlex
import subprocess
import tempfile
from pathlib import Path

from autodeduct_contract_assistant_project import display_path, write_project_files


def parse_extra_args(extra_args: str | list[str] | None) -> list[str]:
    if extra_args is None:
        return []
    if isinstance(extra_args, list):
        return [str(arg) for arg in extra_args]
    return shlex.split(extra_args)


def frama_c_command(
    mode: str, c_files: list[Path], extra_args: str | list[str] | None = None
) -> list[str]:
    parsed_extra_args = parse_extra_args(extra_args)
    if mode == "eva":
        return ["frama-c", *parsed_extra_args, "-eva", *[str(path) for path in c_files]]
    if mode == "wp":
        return ["frama-c", *parsed_extra_args, "-wp", *[str(path) for path in c_files]]
    raise ValueError(f"Unsupported Frama-C mode: {mode}")


def run_frama_c_on_paths(
    root: Path,
    c_files: list[Path],
    file_count: int,
    mode: str,
    extra_args: str | list[str] | None = None,
    file_step_name: str = "Use project files",
) -> dict[str, object]:
    if not c_files:
        raise ValueError("Frama-C requires at least one .c file")
    command = frama_c_command(mode, c_files, extra_args)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
            check=False,
        )
        raw_output = completed.stdout
    except FileNotFoundError:
        return {
            "status": "Frama-C is not installed in this environment.",
            "pipeline": [
                {
                    "status": "ok",
                    "name": file_step_name,
                    "detail": f"Selected {file_count} file(s).",
                },
                {
                    "status": "error",
                    "name": f"Run Frama-C {mode.upper()}",
                    "detail": "Could not find the frama-c executable.",
                },
            ],
            "command": command,
            "returncode": 127,
            "output": "frama-c executable not found\n",
        }
    except subprocess.TimeoutExpired as exc:
        raw_output = exc.stdout or ""
        if isinstance(raw_output, bytes):
            raw_output = raw_output.decode("utf-8", errors="replace")
        returncode = 124
        status = "Frama-C run timed out."
    else:
        returncode = completed.returncode
        status = (
            f"Frama-C {mode.upper()} completed."
            if returncode == 0
            else f"Frama-C {mode.upper()} exited with status {returncode}."
        )

    display_command = [
        display_path(Path(arg), root) if str(arg).startswith(str(root)) else arg
        for arg in command
    ]
    output = "$ " + " ".join(display_command) + "\n\n" + raw_output
    return {
        "status": status,
        "pipeline": [
            {
                "status": "ok",
                "name": file_step_name,
                "detail": f"Selected {file_count} file(s).",
            },
            {
                "status": "ok" if c_files else "warn",
                "name": "Select C inputs",
                "detail": f"Running on {len(c_files)} .c file(s).",
            },
            {
                "status": "ok" if returncode == 0 else "warn",
                "name": f"Run Frama-C {mode.upper()}",
                "detail": f"Exit status {returncode}.",
            },
        ],
        "command": display_command,
        "returncode": returncode,
        "output": output,
    }


def run_frama_c(
    files: list[dict[str, str]], mode: str, extra_args: str | list[str] | None = None
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="autodeduct-contract-assistant-") as tmpdir:
        root = Path(tmpdir)
        written = write_project_files(files, root)
        c_files = [path for path in written if path.suffix.lower() == ".c"]
        return run_frama_c_on_paths(
            root, c_files, len(written), mode, extra_args, "Write project files"
        )
