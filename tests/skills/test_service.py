from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from kis_mcp.skills.backend import FastMcpWorkBackend
from kis_mcp.skills.catalogue import SkillCatalogue
from kis_mcp.skills.config import SkillsConfig
from kis_mcp.skills.errors import SkillsError
from kis_mcp.skills.service import SkillsService


class RecordingFilesystemBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def create_directory(self, path: str) -> None:
        self.calls.append(("create_directory", (path,)))
        Path(path).mkdir(parents=True, exist_ok=False)

    async def write_text(self, path: str, content: str) -> None:
        self.calls.append(("write_text", (path, content)))
        Path(path).write_bytes(content.encode("utf-8"))

    async def move(self, source: str, destination: str) -> None:
        self.calls.append(("move", (source, destination)))
        Path(source).replace(destination)

    async def replace_text(
        self, path: str, old_string: str, new_string: str
    ) -> None:
        self.calls.append(("replace_text", (path, old_string, new_string)))
        target = Path(path)
        current = target.read_bytes().decode("utf-8")
        if current.count(old_string) != 1:
            raise AssertionError("expected one exact replacement")
        target.write_bytes(current.replace(old_string, new_string).encode("utf-8"))


class NoOpReplacementBackend(RecordingFilesystemBackend):
    async def replace_text(
        self, path: str, old_string: str, new_string: str
    ) -> None:
        self.calls.append(("replace_text", (path, old_string, new_string)))


class RecordingServer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], bool]] = []

    async def call_tool(
        self, name: str, arguments: dict[str, object], *, run_middleware: bool
    ):
        self.calls.append((name, arguments, run_middleware))
        return type("Result", (), {"is_error": False, "content": []})()


def test_create_skill_uses_work_backend_and_refreshes_catalogue(
    skills_config: SkillsConfig,
) -> None:
    backend = RecordingFilesystemBackend()
    catalogue = SkillCatalogue(skills_config)
    service = SkillsService(catalogue, backend)
    content = "---\nname: new-skill\ndescription: New skill\n---\n# New\n"

    result = asyncio.run(service.create_skill("new-skill", content))

    assert [call[0] for call in backend.calls] == [
        "create_directory",
        "write_text",
        "move",
    ]
    assert Path(backend.calls[0][1][0]).parent == skills_config.staging_root
    assert backend.calls[2][1][1] == str(skills_config.root / "new-skill")
    assert (skills_config.root / "new-skill" / "SKILL.md").read_bytes() == content.encode(
        "utf-8"
    )
    assert result.skill_id == "new-skill"
    assert result.before_sha256 is None
    assert result.after_sha256 == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert service.load_skill("new-skill").sha256 == result.after_sha256


def test_improve_skill_requires_current_hash_before_backend_call(
    skills_config: SkillsConfig, make_skill
) -> None:
    root = make_skill("alpha-skill")
    backend = RecordingFilesystemBackend()
    service = SkillsService(SkillCatalogue(skills_config), backend)
    current = (root / "SKILL.md").read_bytes().decode("utf-8")
    replacement = current.replace("Summary for alpha-skill", "Improved")

    with pytest.raises(SkillsError, match="SKILLS_HASH_MISMATCH"):
        asyncio.run(
            service.improve_skill(
                "alpha-skill",
                "SKILL.md",
                "0" * 64,
                replacement,
            )
        )

    assert backend.calls == []


def test_improve_skill_uses_exact_backend_replacement_and_refreshes(
    skills_config: SkillsConfig, make_skill
) -> None:
    root = make_skill("alpha-skill")
    backend = RecordingFilesystemBackend()
    service = SkillsService(SkillCatalogue(skills_config), backend)
    loaded = service.load_skill("alpha-skill")
    current = (root / "SKILL.md").read_bytes().decode("utf-8")
    replacement = current.replace("Summary for alpha-skill", "Improved summary")

    result = asyncio.run(
        service.improve_skill(
            "alpha-skill", "SKILL.md", loaded.sha256, replacement
        )
    )

    assert [call[0] for call in backend.calls] == ["replace_text"]
    assert backend.calls[0][1] == (str(root / "SKILL.md"), current, replacement)
    assert result.before_sha256 == loaded.sha256
    assert result.after_sha256 == hashlib.sha256(
        replacement.encode("utf-8")
    ).hexdigest()
    assert service.load_skill("alpha-skill").sha256 == result.after_sha256


def test_improve_skill_rejects_backend_noop_after_hash_precondition(
    skills_config: SkillsConfig, make_skill
) -> None:
    root = make_skill("alpha-skill")
    backend = NoOpReplacementBackend()
    service = SkillsService(SkillCatalogue(skills_config), backend)
    loaded = service.load_skill("alpha-skill")
    current = (root / "SKILL.md").read_bytes().decode("utf-8")
    replacement = current.replace("Summary for alpha-skill", "Improved summary")

    with pytest.raises(SkillsError, match="SKILLS_HASH_MISMATCH"):
        asyncio.run(
            service.improve_skill(
                "alpha-skill", "SKILL.md", loaded.sha256, replacement
            )
        )

    assert service.load_skill("alpha-skill").sha256 == loaded.sha256
    assert [call[0] for call in backend.calls] == ["replace_text"]


def test_fastmcp_backend_reenters_server_middleware_for_every_mutation() -> None:
    server = RecordingServer()
    backend = FastMcpWorkBackend(server)  # type: ignore[arg-type]

    async def exercise() -> None:
        await backend.create_directory(r"C:\Projects\.kis-mcp\temp\skills\stage")
        await backend.write_text(
            r"C:\Projects\.kis-mcp\temp\skills\stage\SKILL.md", "x"
        )
        await backend.move(
            r"C:\Projects\.kis-mcp\temp\skills\stage",
            r"C:\Projects\.agents\skills\new-skill",
        )
        await backend.replace_text(
            r"C:\Projects\.agents\skills\new-skill\SKILL.md", "before", "after"
        )

    asyncio.run(exercise())

    assert server.calls == [
        (
            "create_directory",
            {"path": r"C:\Projects\.kis-mcp\temp\skills\stage"},
            True,
        ),
        (
            "write_file",
            {
                "path": r"C:\Projects\.kis-mcp\temp\skills\stage\SKILL.md",
                "content": "x",
                "mode": "rewrite",
                "origin": "llm",
            },
            True,
        ),
        (
            "move_file",
            {
                "source": r"C:\Projects\.kis-mcp\temp\skills\stage",
                "destination": r"C:\Projects\.agents\skills\new-skill",
            },
            True,
        ),
        (
            "edit_block",
            {
                "file_path": r"C:\Projects\.agents\skills\new-skill\SKILL.md",
                "old_string": "before",
                "new_string": "after",
                "expected_replacements": 1,
                "origin": "llm",
            },
            True,
        ),
    ]


def test_fastmcp_backend_normalizes_provider_error() -> None:
    class FailedServer(RecordingServer):
        async def call_tool(
            self, name: str, arguments: dict[str, object], *, run_middleware: bool
        ):
            return type(
                "Result",
                (),
                {"is_error": True, "content": [type("Text", (), {"text": "failure"})()]},
            )()

    backend = FastMcpWorkBackend(FailedServer())  # type: ignore[arg-type]

    with pytest.raises(SkillsError, match="SKILLS_BACKEND_FAILED"):
        asyncio.run(
            backend.create_directory(r"C:\Projects\.kis-mcp\temp\skills\stage")
        )
