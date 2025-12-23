import argparse
import os
import re
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple, cast

from git import InvalidGitRepositoryError, Repo
from google import genai
from openai import OpenAI
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

# Defaults und Konfiguration
DEFAULT_LANGUAGE = os.getenv("COMMIT_LANGUAGE", "Deutsch")
DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_ZAI_MODEL = os.getenv("ZAI_MODEL", "GLM-4.7")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")

DEFAULT_ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
DEFAULT_OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ZAI_API_KEY = os.getenv("ZAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

parser = argparse.ArgumentParser(
    description="Auto-Commit mit AI-generierter Commit-Message."
)
parser.add_argument("--lang", help="Sprache der Commit-Message", default=None)
parser.add_argument("--model", help="Modellname (abhängig vom Provider)", default=None)
parser.add_argument(
    "--provider", help="AI-Provider: gemini, zai oder openai", default=None
)
parser.add_argument(
    "--zai-base-url",
    help="Optional: eigenes Base-URL für Z.AI Coding Plan (OpenAI-kompatibel)",
    default=None,
)
parser.add_argument(
    "--openai-base-url",
    help="Optional: eigenes Base-URL für OpenAI (OpenAI-kompatibel)",
    default=None,
)
parser.add_argument(
    "--style",
    help="Commit-Stil: sarcastic, humorous oder standard (default)",
    default="standard",
)
args = parser.parse_args()

COMMIT_LANGUAGE = args.lang or DEFAULT_LANGUAGE
AI_PROVIDER = (args.provider or DEFAULT_PROVIDER).lower()
COMMIT_STYLE = (args.style or "standard").lower()

if AI_PROVIDER == "gemini":
    default_model = DEFAULT_GEMINI_MODEL
elif AI_PROVIDER == "zai":
    default_model = DEFAULT_ZAI_MODEL
elif AI_PROVIDER == "openai":
    default_model = DEFAULT_OPENAI_MODEL
else:
    default_model = DEFAULT_GEMINI_MODEL

MODEL_NAME = args.model or default_model
ZAI_BASE_URL = args.zai_base_url or DEFAULT_ZAI_BASE_URL
OPENAI_BASE_URL = args.openai_base_url or DEFAULT_OPENAI_BASE_URL


class CommitGenerationError(RuntimeError):
    """Signalisiert Fehler bei der KI-Commit-Generierung, bei denen das Tool abbrechen sollte."""


def find_git_root(path: str) -> Optional[str]:
    """Findet das Root-Verzeichnis des Git-Repositories."""
    try:
        repo = Repo(path, search_parent_directories=True)
        if not repo.working_tree_dir:
            return None
        return str(repo.working_tree_dir)
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


def create_ai_clients(
    provider: str, zai_base_url: str
) -> Tuple[Optional[genai.Client], Optional[OpenAI]]:
    """Initialisiert die AI-Clients abhängig vom Provider."""
    if provider == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY ist nicht gesetzt. Bitte füge ihn in die .env-Datei ein."
            )
        return genai.Client(api_key=GEMINI_API_KEY), None
    if provider == "zai":
        if not ZAI_API_KEY:
            raise ValueError(
                "ZAI_API_KEY ist nicht gesetzt. Bitte füge ihn in die .env-Datei ein."
            )
        return None, OpenAI(api_key=ZAI_API_KEY, base_url=zai_base_url)

    if provider == "openai":
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY ist nicht gesetzt. Bitte füge ihn in die .env-Datei ein."
            )
        if OPENAI_BASE_URL:
            return None, OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        return None, OpenAI(api_key=OPENAI_API_KEY)

    raise ValueError(f"Unbekannter Provider: {provider}")


def generate_commit_message(
    file_diffs: Dict[str, str],
    provider: str,
    model_name: str,
    commit_language: str,
    commit_style: str,
    gemini_client: Optional[genai.Client],
    zai_client: Optional[OpenAI],
) -> str:
    """Generiert eine Commit-Nachricht basierend auf den Dateidiffs."""
    prompt_parts: List[str] = [
        (
            f"Erstelle eine prägnante Git-Commit-Nachricht in der Sprache {commit_language}. "
            "Nutze eine kurze Summary-Zeile (max 72 Zeichen) und optional einen Body mit kurzen Bullet Points. "
            "Verwende kein Markdown-Formatting wie ``` oder Überschriften. "
        )
    ]

    if commit_style in ("humorous", "sarcastic"):
        prompt_parts[0] += (
            f"Der Commit-Stil ist '{commit_style}'. "
            "Verwende trockenen, subtilen Sarkasmus oder Humor, "
            "bleibe fachlich korrekt, verständlich und git-konform. "
            "Keine Albernheit, keine Memes."
        )

    for file_path, diff in file_diffs.items():
        prompt_parts.append(f"Datei: {file_path}\nÄnderungen:\n{diff}")

    prompt = "\n\n".join(prompt_parts)

    try:
        if provider == "gemini":
            if gemini_client is None:
                raise CommitGenerationError("Gemini-Client fehlt.")
            response = gemini_client.models.generate_content(
                model=model_name, contents=prompt
            )
            message = getattr(response, "text", "") or ""
        elif provider in {"zai", "openai"}:
            if zai_client is None:
                raise CommitGenerationError("OpenAI-kompatibler Client fehlt.")
            response = zai_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            message = (
                response.choices[0].message.content
                if response and response.choices
                else ""
            )
        else:
            raise CommitGenerationError(f"Unbekannter Provider: {provider}")
    except Exception as exc:  # pragma: no cover - defensive fallback
        # Bei 429/RESOURCE_EXHAUSTED sofort abbrechen, statt mit altem Template fortzufahren.
        if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc):
            raise CommitGenerationError(
                "KI-Commit-Generierung fehlgeschlagen (429 RESOURCE_EXHAUSTED). "
                "Bitte später erneut versuchen oder das Kontingent anpassen."
            ) from exc
        print(f"Fehler bei der Commit-Generierung: {exc}")
        return "chore: update changes"

    message = (message or "").strip()
    if not message:
        return "chore: update changes"

    # Mehrere Leerzeilen reduzieren, sonst nichts verändern
    message = re.sub(r"\n{3,}", "\n\n", message)
    return message


def prompt_to_stage(
    repo: Repo, files: List[str], label: str, add_all: bool = False
) -> None:
    """Fragt, ob Dateien gestagt werden sollen, und führt das Staging aus."""
    if not files:
        return

    print(f"\n{label} gefunden:")
    for file in files:
        print(f" - {file}")

    user_input = (
        input(f"\nMöchtest du alle {label.lower()} hinzufügen? (y/n): ").strip().lower()
    )
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
        f.write(
            "\n\n# Bitte gib die Commit-Nachricht für deine Änderungen ein. Zeilen, die\n"
        )
        f.write(
            "# mit # beginnen, werden ignoriert, und eine leere Nachricht bricht den Commit ab.\n"
        )
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
    unstaged_files = [
        cast(str, item.a_path) for item in repo.index.diff(None) if item.a_path
    ]

    prompt_to_stage(repo, untracked_files, "Untracked Files", add_all=True)
    prompt_to_stage(repo, unstaged_files, "unstaged Dateien")

    staged_files, deleted_files = get_staged_and_deleted_files(repo)
    if not staged_files and not deleted_files:
        print(
            "Keine gestagten Änderungen gefunden. Bitte Dateien zum Committen hinzufügen."
        )
        return

    if AI_PROVIDER not in {"gemini", "zai", "openai"}:
        print(
            "Ungültiger Provider. Bitte 'gemini', 'zai' oder 'openai' wählen (Umgebungsvariable AI_PROVIDER oder CLI-Flag --provider)."
        )
        return

    try:
        gemini_client, zai_client = create_ai_clients(AI_PROVIDER, ZAI_BASE_URL)
    except ValueError as exc:
        print(exc)
        return

    file_diffs = {
        file: get_diff_for_file(repo, file) for file in staged_files + deleted_files
    }
    try:
        commit_message = generate_commit_message(
            file_diffs=file_diffs,
            provider=AI_PROVIDER,
            model_name=MODEL_NAME,
            commit_language=COMMIT_LANGUAGE,
            commit_style=COMMIT_STYLE,
            gemini_client=gemini_client,
            zai_client=zai_client,
        )
    except CommitGenerationError as exc:
        print(exc)
        return
    commit_message = commit_message or "chore: update changes"

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    tmp_path = tmp_file.name
    tmp_file.close()

    try:
        write_commit_template(
            tmp_path, commit_message, staged_files, deleted_files, file_diffs
        )

        editor = os.getenv("EDITOR", "vim")
        subprocess.call([editor, tmp_path])

        with open(tmp_path, "r") as f:
            lines = f.readlines()
            final_commit_message = "".join(
                line for line in lines if not line.startswith("#")
            ).strip()

        if not final_commit_message:
            print("Commit-Nachricht leer. Abbruch.")
            return

        with open(tmp_path, "w") as f:
            f.write(final_commit_message)

        print("\n===== Änderungen für den Commit =====")
        print(repo.git.status())
        print("\n===== Vorgeschlagene bzw. angepasste Commit-Nachricht =====")
        print(final_commit_message)

        user_input = (
            input("\nMöchtest du diese Änderungen committen? (y/n): ").strip().lower()
        )
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
