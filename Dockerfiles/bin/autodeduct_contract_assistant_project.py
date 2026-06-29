"""Project/path helpers for the AutoDeduct contract assistant GUI."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any


def safe_relative_path(filename: str) -> Path:
    raw_parts = PurePosixPath(filename.replace("\\", "/")).parts
    parts = [
        part
        for part in raw_parts
        if part not in ("", ".", "..", "/") and not part.endswith(":")
    ]
    if not parts:
        return Path("input.c")
    return Path(*parts)


def write_project_files(files: list[dict[str, str]], root: Path) -> list[Path]:
    written: list[Path] = []
    for item in files:
        code = item["code"]
        if not code.strip():
            continue
        path = root / safe_relative_path(item["filename"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code, encoding="utf-8")
        written.append(path)
    if not written:
        raise ValueError("C source is empty")
    return written


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def display_reports(reports: list[Any], root: Path) -> list[dict[str, object]]:
    result = []
    for report in reports:
        item = report.to_json()
        item["file"] = display_path(report.path, root)
        result.append(item)
    return result


def source_paths_from_project_path(project_path: str, assistant: Any) -> tuple[Path, list[Path]]:
    path = Path(project_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Project path does not exist in the container: {path}")
    root = path if path.is_dir() else path.parent
    source_paths = [
        source
        for source in assistant.collect_source_paths([path])
        if source.suffix.lower() in assistant.SOURCE_SUFFIXES
    ]
    if not source_paths:
        raise ValueError("No .c or .h source files were found at the project path")
    return root, source_paths


def list_project_path(project_path: str | None, source_suffixes: set[str]) -> dict[str, object]:
    path = Path(project_path or "/project").expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Project path does not exist in the container: {path}")

    current = path.parent if path.is_file() else path
    entries = []
    for child in sorted(current.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        is_source = child.suffix.lower() in source_suffixes
        if not child.is_dir() and not is_source:
            continue
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
                "is_source": is_source,
            }
        )

    parent = str(current.parent) if current.parent != current else None
    return {
        "path": str(current),
        "parent": parent,
        "entries": entries,
    }


def replace_project_paths(text: str, paths: list[Path], root: Path) -> str:
    updated = text
    for path in paths:
        updated = updated.replace(str(path), display_path(path, root))
    return updated
