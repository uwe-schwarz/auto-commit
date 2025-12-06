import argparse
import os
import re
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple

from git import InvalidGitRepositoryError, Repo
from google import genai
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_LANGUAGE = os.getenv("COMMIT_LANGUAGE", "Deutsch")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY ist nicht gesetzt. Bitte füge ihn in die .env-Datei ein.")

client = genai.Client(api_key=GEMINI_API_KEY)

parser = argparse.ArgumentParser(description="Auto-Commit mit AI-generierter Commit-Message.")
parser.add_argument("--lang", help="Sprache der Commit-Message", default=None)
parser.add_argument("--model", help="Gemini Modellname", default=None)
args = parser.parse_args()

COMMIT_LANGUAGE = args.lang or DEFAULT_LANGUAGE
MODEL_NAME = args.model or DEFAULT_MODEL


def find_git_root(path: str) -> Optional[str]:
    """Findet das Root-Verzeichnis des Git-Repositories."""
    try:
        repo = Repo(path, search_parent_directories=True)
        return repo.working_tree_dir
    except InvalidGitRepositoryError:
        return None


def get_staged_and_deleted_files(repo: Repo) -> Tuple[List[str], List[str]]:
    """Liefert gestagte Dateien sowie gelöschte Dateien getrennt."""
    staged = repo.git.diff("--cached", "--name-only").splitlines()
    deleted = repo.git.diff("--cached", "--diff-filter=D", "--name-only").splitlines()
    staged_non_deleted = [path for path in staged if path not in deleted]
    return staged_non_deleted, deleted


def get_diff_for_file(repo: Repo, file_path: str) -> str:
    """Diff der gestagten Änderungen für eine Datei."""
    return repo.git.diff("--cached", "--", file_path)


def generate_commit_message(file_diffs: Dict[str, str]) -> str:
    """Generiert eine Commit-Nachricht basierend auf den Dateidiffs."""
    prompt_parts: List[str] = [
        (
            f"Erstelle eine prägnante Git-Commit-Nachricht in der Sprache {COMMIT_LANGUAGE}. "
            "Nutze eine kurze Summary-Zeile (max 72 Zeichen) und optional einen Body mit kurzen Bullet Points. "
            "Verwende kein Markdown-Formatting wie ``` oder Überschriften."
        )
    ]

    for file_path, diff in file_diffs.items():
        prompt_parts.append(f"Datei: {file_path}\nÄnderungen:\n{diff}")

    prompt = "\n\n".join(prompt_parts)

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"Fehler bei der Commit-Generierung: {exc}")
        return "chore: update changes"

    message = getattr(response, "text", "") or ""
    message = message.strip()
    if not message:
        return "chore: update changes"

    # Mehrere Leerzeilen reduzieren, sonst nichts verändern
    message = re.sub(r"\n{3,}", "\n\n", message)
    return message


def prompt_to_stage(repo: Repo, files: List[str], label: str, add_all: bool = False) -> None:
    """Fragt, ob Dateien gestagt werden sollen, und führt das Staging aus."""
    if not files:
        return

    print(f"\n{label} gefunden:")
    for file in files:
        print(f" - {file}")

    user_input = input(f"\nMöchtest du alle {label.lower()} hinzufügen? (y/n): ").strip().lower()
    if user_input == "y":
        if add_all:
            repo.git.add(all=True)
        else:
            repo.git.add(files)
        print(f"{label} wurden hinzugefügt.")
    else:
        print(f"{label} wurden nicht hinzugefügt.")


def write_commit_template(
    file_path: str,
    commit_message: str,
    modified_files: List[str],
    deleted_files: List[str],
    file_diffs: Dict[str, str],
) -> None:
    """Schreibt die Commit-Nachricht plus Kontext in eine temporäre Datei."""
    with open(file_path, "w") as f:
        f.write(commit_message)
        f.write("\n\n# Bitte gib die Commit-Nachricht für deine Änderungen ein. Zeilen, die\n")
        f.write("# mit # beginnen, werden ignoriert, und eine leere Nachricht bricht den Commit ab.\n")
        f.write("#\n# Zu übernehmende Änderungen:\n")

        for file in modified_files:
            f.write(f"#\t{file}\n")
        if deleted_files:
            f.write("#\n# Gelöschte Dateien:\n")
            for file in deleted_files:
                f.write(f"#\t{file} (gelöscht)\n")

        f.write("#\n")
        for file, diff in file_diffs.items():
            f.write(f"# Changes in {file}:\n")
            for line in diff.splitlines():
                f.write(f"# {line}\n")
            f.write("#\n")


def main() -> None:
    git_root = find_git_root(os.getcwd())
    if git_root is None:
        print("Fehler: Kein Git-Repository gefunden.")
        return

    repo = Repo(git_root)

    # Check auf jegliche Änderungen
    if not repo.is_dirty(untracked_files=True):
        print("Keine Änderungen zum Committen.")
        return

    untracked_files = repo.untracked_files
    unstaged_files = [item.a_path for item in repo.index.diff(None)]

    prompt_to_stage(repo, untracked_files, "Untracked Files", add_all=True)
    prompt_to_stage(repo, unstaged_files, "unstaged Dateien")

    staged_files, deleted_files = get_staged_and_deleted_files(repo)
    if not staged_files and not deleted_files:
        print("Keine gestagten Änderungen gefunden. Bitte Dateien zum Committen hinzufügen.")
        return

    file_diffs = {file: get_diff_for_file(repo, file) for file in staged_files + deleted_files}
    commit_message = generate_commit_message(file_diffs)
    commit_message = commit_message or "chore: update changes"

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    tmp_path = tmp_file.name
    tmp_file.close()

    try:
        write_commit_template(tmp_path, commit_message, staged_files, deleted_files, file_diffs)

        editor = os.getenv("EDITOR", "vim")
        subprocess.call([editor, tmp_path])

        with open(tmp_path, "r") as f:
            lines = f.readlines()
            final_commit_message = "".join(line for line in lines if not line.startswith("#")).strip()

        if not final_commit_message:
            print("Commit-Nachricht leer. Abbruch.")
            return

        with open(tmp_path, "w") as f:
            f.write(final_commit_message)

        print("\n===== Änderungen für den Commit =====")
        print(repo.git.status())
        print("\n===== Vorgeschlagene bzw. angepasste Commit-Nachricht =====")
        print(final_commit_message)

        user_input = input("\nMöchtest du diese Änderungen committen? (y/n): ").strip().lower()
        if user_input != "y":
            print("Commit abgebrochen.")
            return

        subprocess.run(["git", "commit", "-F", tmp_path], check=False)

        if "origin" in [remote.name for remote in repo.remotes]:
            repo.remote("origin").push()
        else:
            print("Kein 'origin' Remote gefunden. Überspringe 'git push'.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    main()
