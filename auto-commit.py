import argparse
import os
import re
import subprocess
from git import Repo, InvalidGitRepositoryError
import google.generativeai as genai
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

# API-Schlüssel aus der Umgebungsvariable holen
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY ist nicht gesetzt. Bitte füge ihn in die .env-Datei ein.")

# Sprache aus `.env` laden (Fallback: "Deutsch")
DEFAULT_LANGUAGE = os.getenv("COMMIT_LANGUAGE", "Deutsch")

# CLI-Argumente parsen
parser = argparse.ArgumentParser(description="Auto-Commit mit AI-generierter Commit-Message.")
parser.add_argument("--lang", help="Sprache der Commit-Message", default=DEFAULT_LANGUAGE)
args = parser.parse_args()

# Final verwendete Sprache
COMMIT_LANGUAGE = args.lang if args.lang else DEFAULT_LANGUAGE

# Gemini API konfigurieren
genai.configure(api_key=GEMINI_API_KEY)

def find_git_root(path):
    """Findet das Root-Verzeichnis des Git-Repositories."""
    try:
        repo = Repo(path, search_parent_directories=True)
        return repo.working_tree_dir
    except InvalidGitRepositoryError:
        return None

def get_modified_files(repo):
    """Gibt eine Liste der geänderten, neuen und gelöschten Dateien zurück."""
    changed = [item for item in repo.index.diff("HEAD")]
    changed_files = [item.a_path for item in changed if item.change_type != 'D']  # Geänderte Dateien (keine gelöschten)
    deleted_files = [item.a_path for item in changed if item.change_type == 'D']  # Gelöschte Dateien
    new_files = repo.git.diff("--cached", "--name-only").splitlines()  # Neu hinzugefügte Dateien
    all_files = list(set(changed_files + new_files))  # Kombinieren und Duplikate entfernen
    return all_files, deleted_files

def get_diff_for_file(repo, file_path):
    """Gibt den Diff einer Datei zurück."""
    diff = repo.git.diff('HEAD', '--', file_path)
    #print(f"DEBUG: Diff für {file_path}:\n{diff}")  # Debug-Output
    return diff

def generate_commit_message(file_diffs):
    """Generiert eine Commit-Nachricht basierend auf den Dateidiffs."""
    prompt = f"Erstelle eine Git-Commit-Nachricht in der Sprache {COMMIT_LANGUAGE} basierend auf den folgenden Änderungen. Gebe nur die Commit-Nachricht aus, kein Markdown.\n\n"

    for file_path, diff in file_diffs.items():
        prompt += f"\nDatei: {file_path}\nÄnderungen:\n{diff}\n"

    #print(f"DEBUG: Prompt für Gemini:\n{prompt}")  # Debug-Output

    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)

    #print(f"DEBUG: Antwort von Gemini:\n{response.text}")  # Debug-Output

    return response.text if response and response.text else "Default commit message"

def main():
    git_root = find_git_root(os.getcwd())
    if git_root is None:
        print("Fehler: Kein Git-Repository gefunden.")
        return

    repo = Repo(git_root)

    # Überprüfe, ob das Repository Änderungen oder untracked Files enthält
    has_changes = repo.is_dirty(untracked_files=True)
    untracked_files = repo.untracked_files  # Liste der untracked Files
    unstaged_files = [item.a_path for item in repo.index.diff(None)]

    if has_changes or untracked_files or unstaged_files:
        print(f"\nGeneriere Commit-Nachricht in der Sprache {COMMIT_LANGUAGE}…")

        if untracked_files:
            print("\nUntracked Files gefunden:")
            for file in untracked_files:
                print(f" - {file}")

            # Nutzer fragen, ob die Dateien hinzugefügt werden sollen
            user_input = input("\nMöchtest du alle untracked Dateien hinzufügen? (y/n): ").strip().lower()
            if user_input == 'y':
                repo.git.add(all=True)  # Untracked Files hinzufügen
                print("Untracked Files wurden hinzugefügt.")

        if unstaged_files:
            print("\nModifizierte, aber nicht gestagte Dateien gefunden:")
            for file in unstaged_files:
                print(f" - {file}")

            # Nutzer fragen, ob unstaged Dateien hinzugefügt werden sollen
            user_input = input("\nMöchtest du alle unstaged Dateien hinzufügen? (y/n): ").strip().lower()
            if user_input == 'y':
                repo.git.add(unstaged_files)
                print("Unstaged Files wurden hinzugefügt.")

        has_changes = repo.is_dirty(untracked_files=True)
        if not has_changes:
            print("Keine Änderungen zum Committen.")
            return

        modified_files, deleted_files = get_modified_files(repo)

        if not modified_files and not deleted_files:
            print("Keine modifizierten oder gelöschten Dateien gefunden. Abbruch.")
            return

        file_diffs = {file: get_diff_for_file(repo, file) for file in modified_files}
        deleted_diffs = {file: get_diff_for_file(repo, file) for file in deleted_files}
        file_diffs.update(deleted_diffs)  # Gelöschte Dateien auch in die Diff-Liste aufnehmen

        commit_message = generate_commit_message(file_diffs)
        # Doppelte Leerzeichen entfernen
        commit_message = re.sub(r' {2,}', ' ', commit_message)

        # Schreiben der Commit-Nachricht in eine temporäre Datei
        with open('/tmp/COMMIT_MSG.txt', 'w') as f:
            # Commit-Nachricht schreiben
            f.write(commit_message)
            f.write("\n\n# Bitte gib die Commit-Nachricht für deine Änderungen ein. Zeilen, die\n")
            f.write("# mit # beginnen, werden ignoriert, und eine leere Nachricht bricht den Commit ab.\n")
            f.write("#\n")
            f.write("# Zu übernehmende Änderungen:\n")
            f.write("#\n")
            
            # Geänderte Dateien anzeigen
            for file in modified_files:
                f.write(f"#\t{file}\n")
            if deleted_files:
                f.write("#\n# Gelöschte Dateien:\n")
                for file in deleted_files:
                    f.write(f"#\t{file} (gelöscht)\n")
            # Diff-Informationen anzeigen
            f.write("#\n")
            for file, diff in file_diffs.items():
                f.write(f"# Changes in {file}:\n")
                for line in diff.splitlines():
                    f.write(f"# {line}\n")
                f.write("#\n")

        # Öffnen des Editors für die Commit-Nachricht
        editor = os.getenv('EDITOR', 'vim')
        subprocess.call([editor, '/tmp/COMMIT_MSG.txt'])

        # Lesen der bearbeiteten Commit-Nachricht und Filtern der Kommentare
        with open('/tmp/COMMIT_MSG.txt', 'r') as f:
            lines = f.readlines()
            # Nur die Zeilen behalten, die nicht mit # beginnen
            final_commit_message = ''.join(line for line in lines if not line.startswith('#')).strip()

        # Schreiben der Commit-Nachricht in die Datei
        with open('/tmp/COMMIT_MSG.txt', 'w') as f:
            f.write(final_commit_message)

        # Übersicht vor Commit anzeigen
        print("\n===== Änderungen für den Commit =====")
        print(repo.git.status())
        print("\n===== Vorgeschlagene bzw. angepasste Commit-Nachricht =====")
        print(final_commit_message)

        # Letzte Bestätigung einholen
        user_input = input("\nMöchtest du diese Änderungen committen? (y/n): ").strip().lower()
        if user_input != 'y':
            print("Commit abgebrochen.")
            return

        # Änderungen committen (mit Hooks)
        subprocess.run(['git', 'commit', '-F', '/tmp/COMMIT_MSG.txt'])

        # Überprüfen, ob ein 'origin' Remote gesetzt ist und Push durchführen
        if 'origin' in [remote.name for remote in repo.remotes]:
            origin = repo.remote('origin')
            origin.push()
        else:
            print("Kein 'origin' Remote gefunden. Überspringe 'git push'.")
    else:
        print("Keine Änderungen zum Committen.")

    # Entfernen der temporären Datei
    os.remove('/tmp/COMMIT_MSG.txt')

if __name__ == "__main__":
    main()
