import subprocess
import sys
import unittest
from importlib.metadata import version


def parse_version(raw: str) -> tuple[int, ...]:
    return tuple(int(part) for part in raw.split("."))


class DependencyStackTest(unittest.TestCase):
    def test_cli_help_smoke_test(self) -> None:
        result = subprocess.run(
            [sys.executable, "auto-commit.py", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Auto-Commit", result.stdout)

    def test_dependency_versions_are_refreshed(self) -> None:
        self.assertGreaterEqual(parse_version(version("google-genai")), (1, 73, 0))
        self.assertGreaterEqual(parse_version(version("pydantic")), (2, 13, 0))
        self.assertGreaterEqual(parse_version(version("pydantic_core")), (2, 46, 0))


if __name__ == "__main__":
    unittest.main()
