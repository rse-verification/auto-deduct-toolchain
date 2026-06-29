"""OpenAI contract-drafting helpers for the AutoDeduct GUI."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from autodeduct_contract_assistant_project import display_path

OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-4.1"


def missing_helper_targets(reports: list[Any], root: Path) -> list[dict[str, object]]:
    targets: list[dict[str, object]] = []
    for report in reports:
        text = report.path.read_text(encoding="utf-8")
        for function in report.missing_helper_contracts:
            targets.append(
                {
                    "file": display_path(report.path, root),
                    "function": function.name,
                    "signature": " ".join(function.signature.split()),
                    "line": function.line,
                    "called_by": report.called_by.get(function.name, []),
                    "code": text[function.start : function.end].strip(),
                }
            )
    return targets


def contract_suggestion_schema() -> dict[str, object]:
    suggestion = {
        "type": "object",
        "properties": {
            "file": {"type": "string"},
            "function": {"type": "string"},
            "contract": {"type": "string"},
            "rationale": {"type": "string"},
        },
        "required": ["file", "function", "contract", "rationale"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "suggestions": {
                "type": "array",
                "items": suggestion,
            }
        },
        "required": ["suggestions"],
        "additionalProperties": False,
    }


def llm_contract_prompt(reports: list[Any], root: Path) -> str:
    targets = missing_helper_targets(reports, root)
    return (
        "Generate draft ACSL contracts for the missing helper functions below.\n"
        "Return JSON only. Each contract must be a complete ACSL block comment "
        "that starts with /*@ and ends with */ and can be inserted immediately "
        "before the named function. Do not use /** comments, Markdown fences, "
        "or nested /* ... */ comments inside the contract string.\n"
        "Do not modify function bodies, include directives, global variables, or "
        "files not listed here. Prefer conservative requires/assigns/ensures "
        "clauses. If a precise postcondition is not justified by the code, say so "
        "in rationale and use a conservative contract.\n\n"
        f"Missing helper targets:\n{json.dumps(targets, indent=2)}\n"
    )


def openai_response_payload(prompt: str, model: str) -> dict[str, object]:
    return {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are an expert in C formal verification and ACSL. "
                            "You draft contracts for human review; never claim they "
                            "are verified."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "acsl_contract_suggestions",
                "schema": contract_suggestion_schema(),
                "strict": True,
            }
        },
        "store": False,
    }


def extract_response_text(response: dict[str, object]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str):
        return output_text

    chunks: list[str] = []
    output = response.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
    return "\n".join(chunks)


def call_openai_contract_draft(prompt: str) -> tuple[dict[str, object], str, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in the container environment")

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    payload = openai_response_payload(prompt, model)
    request = urllib.request.Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"OpenAI API request failed with status {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"OpenAI API request failed: {exc.reason}") from exc

    raw_response = json.loads(response_body)
    text = extract_response_text(raw_response)
    if not text.strip():
        raise ValueError("OpenAI API response did not include output text")
    draft = json.loads(text)
    return draft, model, text


def suggest_contracts(
    reports: list[Any],
    root: Path,
    pipeline_for_reports: Callable[[list[Any]], list[dict[str, str]]],
) -> dict[str, object]:
    targets = missing_helper_targets(reports, root)
    prompt = llm_contract_prompt(reports, root)
    if not targets:
        draft = {"suggestions": []}
        return {
            "status": "No missing helper contracts found.",
            "pipeline": pipeline_for_reports(reports),
            "prompt": prompt,
            "draft": draft,
            "model": os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        }

    draft, model, raw_text = call_openai_contract_draft(prompt)
    return {
        "status": "LLM contract draft generated.",
        "pipeline": [
            *pipeline_for_reports(reports),
            {
                "status": "ok",
                "name": "Generate LLM draft",
                "detail": f"Generated {len(draft.get('suggestions', []))} suggestion(s) with {model}.",
            },
        ],
        "prompt": prompt,
        "draft": draft,
        "raw_output": raw_text,
        "model": model,
    }
