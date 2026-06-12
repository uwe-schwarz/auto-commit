import subprocess
import sys
import unittest
from pathlib import Path
from importlib.metadata import distribution, version


def parse_version(raw: str) -> tuple[int, ...]:
    return tuple(int(part) for part in raw.split("."))


class DependencyStackTest(unittest.TestCase):
    def test_uv_project_files_define_runtime_and_entrypoint(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('[project]', pyproject)
        self.assertIn('requires-python = ">=3.11"', pyproject)
        self.assertIn('"GitPython>=3.1.46"', pyproject)
        self.assertIn('[project.scripts]', pyproject)
        self.assertIn('autocommit = "auto_commit:main"', pyproject)
        self.assertFalse(Path("requirements.txt").exists())

    def test_local_binary_uses_uv_run(self) -> None:
        wrapper = Path.home().joinpath(".local/bin/autocommit")
        if not wrapper.exists():
            self.skipTest(f"{wrapper} is not installed")

        content = wrapper.read_text(encoding="utf-8")
        self.assertIn("uv run autocommit", content)
        self.assertNotIn(".venv/bin/activate", content)
        self.assertNotIn("auto-commit.py", content)

    def test_cli_help_smoke_test(self) -> None:
        result = subprocess.run(
            [sys.executable, "auto_commit.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Auto-Commit", result.stdout)

    def test_dependency_versions_are_refreshed(self) -> None:
        self.assertGreaterEqual(parse_version(version("google-genai")), (1, 73, 0))
        self.assertGreaterEqual(parse_version(version("pydantic")), (2, 13, 0))

    def test_pydantic_core_matches_pydantic_requirement(self) -> None:
        pydantic_requirements = distribution("pydantic").requires or []
        pydantic_core_requirement = next(
            requirement
            for requirement in pydantic_requirements
            if requirement.startswith("pydantic-core==")
        )

        required_version = pydantic_core_requirement.split("==", 1)[1]
        self.assertEqual(version("pydantic_core"), required_version)


if __name__ == "__main__":
    unittest.main()
