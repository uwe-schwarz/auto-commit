import argparse
import os
import platform
import re
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from git import InvalidGitRepositoryError, Repo
from dotenv import load_dotenv

if TYPE_CHECKING:
    from google.genai import Client as GeminiClient
    from openai import OpenAI as OpenAIClient
else:
    GeminiClient = Any
    OpenAIClient = Any

# .env-Datei laden
load_dotenv()

# Defaults und Konfiguration
DEFAULT_LANGUAGE = os.getenv("COMMIT_LANGUAGE", "Deutsch")
DEFAULT_MODE = os.getenv("COMMIT_MODE", "provider").lower()
DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
DEFAULT_NO_PUSH = os.getenv("NO_PUSH", "false").lower() == "true"
DEFAULT_MACOS_SHORTCUT_NAME = os.getenv(
    "MACOS_SHORTCUT_NAME", "auto-commit-chatgpt"
)

DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_ZAI_MODEL = os.getenv("ZAI_MODEL", "GLM-4.7")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

DEFAULT_ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
DEFAULT_OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ZAI_API_KEY = os.getenv("ZAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

parser = argparse.ArgumentParser(
    description="Auto-Commit mit AI-generierter Commit-Message."
)
parser.add_argument("--lang", help="Sprache der Commit-Message", default=None)
parser.add_argument(
    "--mode",
    help="Commit-Generierung: provider (default) oder shortcuts",
    default=None,
)
parser.add_argument("--model", help="Modellname (abhängig vom Provider)", default=None)
parser.add_argument(
    "--provider", help="AI-Provider: gemini, zai oder openai", default=None
)
parser.add_argument(
    "--shortcut-name",
    help="Name des macOS-Shortcuts für --mode shortcuts",
    default=None,
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
parser.add_argument(
    "--no-push",
    help="Kein Push nach dem Commit ausführen",
    action="store_true",
    default=None,
)
parser.add_argument(
    "--no-editor",
    help="Editor nicht öffnen, AI-Nachricht direkt verwenden",
    action="store_true",
)
parser.add_argument(
    "--auto-add",
    help="Alle untracked und modifizierte Dateien automatisch hinzufügen",
    action="store_true",
)
parser.add_argument(
    "--yolo",
    help="Kombiniert --no-editor und --auto-add - alles automatisch",
    action="store_true",
)
args = parser.parse_args()

COMMIT_LANGUAGE = args.lang or DEFAULT_LANGUAGE
COMMIT_MODE = (args.mode or DEFAULT_MODE).lower()
AI_PROVIDER = (args.provider or DEFAULT_PROVIDER).lower()
COMMIT_STYLE = (args.style or "standard").lower()
NO_PUSH = args.no_push if args.no_push is not None else DEFAULT_NO_PUSH
NO_EDITOR = args.no_editor or args.yolo
AUTO_ADD = args.auto_add or args.yolo
MACOS_SHORTCUT_NAME = args.shortcut_name or DEFAULT_MACOS_SHORTCUT_NAME

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


def dependency_repair_hint() -> str:
    """Hinweis, wie die venv konsistent auf aktuelle direkte Abhängigkeiten gebracht wird."""
    return (
        "Aktualisiere die virtuelle Umgebung mit "
        "'.venv/bin/pip install --upgrade --upgrade-strategy eager -r requirements.txt'. "
        "Wenn das nicht reicht, venv neu anlegen und den gleichen Befehl erneut ausführen."
    )


def load_gemini_client() -> "GeminiClient":
    """Importiert den Gemini-Client erst bei Bedarf."""
    try:
        from google import genai
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise ValueError(
            "Gemini-SDK konnte nicht geladen werden. "
            f"{dependency_repair_hint()} Ursprünglicher Fehler: {exc}"
        ) from exc

    return genai.Client(api_key=GEMINI_API_KEY)


def load_openai_client(api_key: str, base_url: Optional[str] = None) -> "OpenAIClient":
    """Importiert den OpenAI-kompatiblen Client erst bei Bedarf."""
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise ValueError(
            "OpenAI-SDK konnte nicht geladen werden. "
            f"{dependency_repair_hint()} Ursprünglicher Fehler: {exc}"
        ) from exc

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


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
) -> Tuple[Optional["GeminiClient"], Optional["OpenAIClient"]]:
    """Initialisiert die AI-Clients abhängig vom Provider."""
    if provider == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY ist nicht gesetzt. Bitte füge ihn in die .env-Datei ein."
            )
        return load_gemini_client(), None
    if provider == "zai":
        if not ZAI_API_KEY:
            raise ValueError(
                "ZAI_API_KEY ist nicht gesetzt. Bitte füge ihn in die .env-Datei ein."
            )
        return None, load_openai_client(api_key=ZAI_API_KEY, base_url=zai_base_url)

    if provider == "openai":
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY ist nicht gesetzt. Bitte füge ihn in die .env-Datei ein."
            )
        return None, load_openai_client(
            api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL
        )

    raise ValueError(f"Unbekannter Provider: {provider}")


def build_commit_prompt(
    file_diffs: Dict[str, str], commit_language: str, commit_style: str
) -> str:
    """Baut den Prompt für die Commit-Generierung."""
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

    return "\n\n".join(prompt_parts)


def normalize_commit_message(message: str) -> str:
    """Bereitet die generierte Commit-Nachricht für die weitere Nutzung auf."""
    message = (message or "").strip()
    if not message:
        return "chore: update changes"

    # Mehrere Leerzeilen reduzieren, sonst nichts verändern
    return re.sub(r"\n{3,}", "\n\n", message)


def ensure_macos_shortcut_available(shortcut_name: str) -> None:
    """Validiert, dass macOS-Shortcuts verfügbar ist und der Shortcut existiert."""
    if platform.system() != "Darwin":
        raise ValueError(
            "Der Modus '--mode shortcuts' wird nur auf macOS unterstützt."
        )

    if shutil.which("osascript") is None:
        raise ValueError(
            "Die macOS-CLI 'osascript' wurde nicht gefunden. "
            "Bitte auf macOS ausführen oder einen anderen Modus wählen."
        )

    if shutil.which("shortcuts") is None:
        raise ValueError(
            "Die macOS-CLI 'shortcuts' wurde nicht gefunden. "
            "Bitte auf macOS ausführen oder einen anderen Modus wählen."
        )

    result = subprocess.run(
        ["shortcuts", "list"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        error_message = result.stderr.strip() or result.stdout.strip() or "Unbekannter Fehler"
        raise ValueError(
            "Die Liste der Shortcuts konnte nicht geladen werden: "
            f"{error_message}"
        )

    shortcuts = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    if shortcut_name not in shortcuts:
        raise ValueError(
            f"Der Shortcut '{shortcut_name}' wurde nicht gefunden. "
            "Bitte in der Shortcuts-App anlegen oder mit --shortcut-name anpassen."
        )


def generate_commit_message(
    file_diffs: Dict[str, str],
    provider: str,
    model_name: str,
    commit_language: str,
    commit_style: str,
    gemini_client: Optional["GeminiClient"],
    zai_client: Optional["OpenAIClient"],
) -> str:
    """Generiert eine Commit-Nachricht basierend auf den Dateidiffs."""
    prompt = build_commit_prompt(file_diffs, commit_language, commit_style)

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

    return normalize_commit_message(message)


def generate_commit_message_with_shortcut(
    file_diffs: Dict[str, str],
    commit_language: str,
    commit_style: str,
    shortcut_name: str,
) -> str:
    """Generiert die Commit-Nachricht über einen lokalen macOS-Shortcut."""
    ensure_macos_shortcut_available(shortcut_name)
    prompt = build_commit_prompt(file_diffs, commit_language, commit_style)

    applescript = """
on run argv
    set shortcutName to item 1 of argv
    set inputPath to item 2 of argv
    set promptText to read POSIX file inputPath
    tell application "Shortcuts Events"
        return run shortcut shortcutName with input promptText
    end tell
end run
""".strip()

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".txt", encoding="utf-8"
    ) as input_file:
        input_file.write(prompt)
        input_path = input_file.name

    try:
        result = subprocess.run(
            ["osascript", "-", shortcut_name, input_path],
            input=applescript,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

    if result.returncode != 0:
        error_message = result.stderr.strip() or result.stdout.strip() or "Unbekannter Fehler"
        raise CommitGenerationError(
            "Commit-Nachricht konnte nicht über macOS Shortcuts generiert werden: "
            f"{error_message}"
        )

    return normalize_commit_message(result.stdout)


def prompt_to_stage(
    repo: Repo,
    files: List[str],
    label: str,
    add_all: bool = False,
    auto_add: bool = False,
) -> None:
    """Fragt, ob Dateien gestagt werden sollen, und führt das Staging aus."""
    if not files:
        return

    print(f"\n{label} gefunden:")
    for file in files:
        print(f" - {file}")

    if auto_add:
        if add_all:
            repo.git.add(all=True)
        else:
            repo.git.add(files)
        print(f"{label} wurden automatisch hinzugefügt.")
        return

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

    prompt_to_stage(
        repo, untracked_files, "Untracked Files", add_all=True, auto_add=AUTO_ADD
    )
    prompt_to_stage(repo, unstaged_files, "unstaged Dateien", auto_add=AUTO_ADD)

    staged_files, deleted_files = get_staged_and_deleted_files(repo)
    if not staged_files and not deleted_files:
        print(
            "Keine gestagten Änderungen gefunden. Bitte Dateien zum Committen hinzufügen."
        )
        return

    if COMMIT_MODE not in {"provider", "shortcuts"}:
        print(
            "Ungültiger Modus. Bitte 'provider' oder 'shortcuts' wählen "
            "(Umgebungsvariable COMMIT_MODE oder CLI-Flag --mode)."
        )
        return

    file_diffs = {
        file: get_diff_for_file(repo, file) for file in staged_files + deleted_files
    }

    if COMMIT_MODE == "provider":
        if AI_PROVIDER not in {"gemini", "zai", "openai"}:
            print(
                "Ungültiger Provider. Bitte 'gemini', 'zai' oder 'openai' wählen "
                "(Umgebungsvariable AI_PROVIDER oder CLI-Flag --provider)."
            )
            return

        try:
            gemini_client, zai_client = create_ai_clients(AI_PROVIDER, ZAI_BASE_URL)
        except ValueError as exc:
            print(exc)
            return

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
    else:
        try:
            commit_message = generate_commit_message_with_shortcut(
                file_diffs=file_diffs,
                commit_language=COMMIT_LANGUAGE,
                commit_style=COMMIT_STYLE,
                shortcut_name=MACOS_SHORTCUT_NAME,
            )
        except (CommitGenerationError, ValueError) as exc:
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

        if NO_EDITOR:
            final_commit_message = commit_message
        else:
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

        if not args.yolo:
            user_input = (
                input("\nMöchtest du diese Änderungen committen? (y/n): ")
                .strip()
                .lower()
            )
            if user_input != "y":
                print("Commit abgebrochen.")
                return

        subprocess.run(["git", "commit", "-F", tmp_path], check=False)

        if NO_PUSH:
            print("Git Push wurde übersprungen (--no-push aktiv).")
        elif "origin" in [remote.name for remote in repo.remotes]:
            repo.remote("origin").push()
        else:
            print("Kein 'origin' Remote gefunden. Überspringe 'git push'.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    main()
