from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import InvalidSecretReferenceError


_SCHEME = "secret://"
_MAX_URI_LENGTH = 255
_MAX_SEGMENTS = 16
_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def _invalid() -> InvalidSecretReferenceError:
    return InvalidSecretReferenceError("KIS_MCP_SECRET_REFERENCE_INVALID")


@dataclass(frozen=True, slots=True)
class SecretReference:
    path: str

    @classmethod
    def parse(cls, value: str) -> "SecretReference":
        if not isinstance(value, str) or len(value) > _MAX_URI_LENGTH:
            raise _invalid()
        if not value.startswith(_SCHEME):
            raise _invalid()
        if any(character in value for character in ("\\", "?", "#", "%")):
            raise _invalid()

        path = value[len(_SCHEME) :]
        segments = path.split("/")
        if not 2 <= len(segments) <= _MAX_SEGMENTS:
            raise _invalid()
        if any(segment in {"", ".", ".."} or _SEGMENT.fullmatch(segment) is None for segment in segments):
            raise _invalid()
        return cls(path="/".join(segments))

    @property
    def uri(self) -> str:
        return f"{_SCHEME}{self.path}"

    def __str__(self) -> str:
        return self.uri
