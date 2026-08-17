from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path
from typing import Any, Mapping

from .models import ReservationAdmissionError


class LocalGovernanceAdapter:
    def __init__(self, repository: Path) -> None:
        self._repository = Path(repository).resolve()
        self._workflow = self._repository / "scripts" / "change-workflow.ps1"
        if not self._workflow.is_file():
            raise ReservationAdmissionError(
                "CHANGE_WORKFLOW_MISSING",
                f"Governed change workflow not found at {self._workflow}.",
            )

    def list_claims(self) -> list[dict[str, Any]]:
        result = self._run_workflow("list")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ReservationAdmissionError(
                "CHANGE_CLAIM_LIST_INVALID",
                "Governed change list did not return JSON.",
            ) from exc
        if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
            raise ReservationAdmissionError(
                "CHANGE_CLAIM_LIST_INVALID",
                "Governed change list must return an array of objects.",
            )
        return [dict(item) for item in payload]

    def resolve_base(self, base: str) -> dict[str, str]:
        commit = self._run_git("rev-parse", "--verify", f"{base}^{{commit}}").stdout.strip().lower()
        tree = self._run_git("rev-parse", "--verify", f"{commit}^{{tree}}").stdout.strip().lower()
        return {"commit_sha": commit, "tree_sha": tree}

    def create_change(self, request: Mapping[str, Any]) -> dict[str, Any]:
        expected_base = request.get("exact_base")
        if not isinstance(expected_base, Mapping):
            raise ReservationAdmissionError(
                "EXACT_BASE_REQUIRED",
                "Governed change creation requires exact base identity.",
            )
        current_base = self.resolve_base(str(request["base"]))
        if current_base != dict(expected_base):
            raise ReservationAdmissionError(
                "BASE_CHANGED_BEFORE_GOVERNED_CREATION",
                "The governed base changed after reservation admission began.",
            )
        arguments = [
            "new",
            str(request["change_id"]),
            "--outcome",
            str(request["outcome"]),
            "--complexity",
            str(request["complexity"]),
            "--base",
            str(request["base"]),
        ]
        for path in request.get("owned_paths", ()):
            arguments.extend(("--owned", str(path)))
        for path in request.get("shared_paths", ()):
            arguments.extend(("--shared", str(path)))
        for path in request.get("excluded_paths", ()):
            arguments.extend(("--exclude", str(path)))
        for dependency in request.get("dependencies", ()):
            arguments.extend(("--depends-on", str(dependency)))
        integration_owner = request.get("integration_owner")
        if integration_owner:
            arguments.extend(("--integration-owner", str(integration_owner)))
        for trigger in request.get("risk_triggers", ()):
            arguments.extend(("--risk-trigger", str(trigger)))
        work = request.get("work_management")
        if isinstance(work, Mapping):
            arguments.extend(self._work_management_arguments(work))
        result = self._run_workflow(*arguments)
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ReservationAdmissionError(
                "GOVERNED_CHANGE_RESULT_INVALID",
                "Governed change creation did not return JSON.",
            ) from exc
        if not isinstance(payload, dict):
            raise ReservationAdmissionError(
                "GOVERNED_CHANGE_RESULT_INVALID",
                "Governed change creation result must be an object.",
            )
        return dict(payload)

    def amend_change(self, request: Mapping[str, Any]) -> dict[str, Any]:
        change_id = str(request.get("change_id", ""))
        expected = request.get("expected_claim")
        proposed = request.get("proposed_claim")
        if not change_id or not isinstance(expected, Mapping) or not isinstance(proposed, Mapping):
            raise ReservationAdmissionError(
                "GOVERNED_SCOPE_AMEND_INVALID",
                "Scope amendment requires change_id, expected_claim, and proposed_claim.",
            )
        scope_path = self._scope_path(change_id)
        try:
            payload = json.loads(scope_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ReservationAdmissionError(
                "GOVERNED_SCOPE_READ_FAILED", f"Cannot read {scope_path}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ReservationAdmissionError(
                "GOVERNED_SCOPE_READ_FAILED", "Governed scope must be a JSON object."
            )
        for field in (
            "outcome",
            "owned_paths",
            "shared_paths",
            "excluded_paths",
            "dependencies",
            "integration_owner",
        ):
            if payload.get(field) != expected.get(field):
                raise ReservationAdmissionError(
                    "GOVERNED_SCOPE_CAS_CONFLICT",
                    f"Governed scope field {field} changed before amendment.",
                )
        for field in ("owned_paths", "shared_paths", "dependencies", "integration_owner"):
            payload[field] = proposed.get(field)

        temporary = scope_path.with_name(f"{scope_path.name}.tmp-{uuid.uuid4().hex}")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, scope_path)
        return {"mode": "apply", "success": True, "scope_path": str(scope_path)}

    def _scope_path(self, change_id: str) -> Path:
        candidates = [
            self._repository / ".work" / "changes" / change_id / "scope.json",
            self._repository / ".work" / "worktrees" / change_id / ".work" / "changes" / change_id / "scope.json",
        ]
        if self._repository.parent.name == "worktrees":
            candidates.append(
                self._repository.parent / change_id / ".work" / "changes" / change_id / "scope.json"
            )
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise ReservationAdmissionError(
            "GOVERNED_SCOPE_NOT_FOUND",
            f"Cannot locate governed scope for {change_id} from {self._repository}.",
        )

    def _work_management_arguments(self, work: Mapping[str, Any]) -> list[str]:
        fields = (
            ("--work-project-id", "project_id"),
            ("--work-record-id", "record_id"),
            ("--work-source-repository", "source_repository"),
            ("--work-source-number", "source_number"),
            ("--work-source-kind", "source_kind"),
            ("--documentation-impact", "documentation_impact"),
        )
        arguments: list[str] = []
        for flag, key in fields:
            value = work.get(key)
            if value is None:
                raise ReservationAdmissionError(
                    "WORK_MANAGEMENT_METADATA_INCOMPLETE",
                    f"Missing Work Management field {key}.",
                )
            arguments.extend((flag, str(value)))
        return arguments

    def _run_workflow(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        command = [
            "pwsh",
            "-NoProfile",
            "-File",
            str(self._workflow),
            *arguments,
        ]
        return self._run(command, "CHANGE_WORKFLOW_FAILED")

    def _run_git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self._run(["git", *arguments], "GIT_COMMAND_FAILED")

    def _run(
        self,
        command: list[str],
        error_code: str,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            command,
            cwd=self._repository,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "unknown failure"
            raise ReservationAdmissionError(error_code, detail[:1000])
        return completed


__all__ = ["LocalGovernanceAdapter"]
