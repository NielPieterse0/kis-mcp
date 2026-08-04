from __future__ import annotations


class SkillsError(RuntimeError):
    """Corrective structural or backend failure for the Skills interface."""

    def __init__(self, code: str, message: str, *, subject: str | None = None) -> None:
        self.code = code
        self.message = message
        self.subject = subject
        detail = f"{code}: {message}"
        if subject is not None:
            detail = f"{detail} [{subject}]"
        super().__init__(detail)
