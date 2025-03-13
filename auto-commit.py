import os
import subprocess
from git import Repo
import google.generativeai as genai

# Konfigurieren Sie Ihren Gemini API-Schlüssel
with open(os.path.expanduser("~/private/api/gemini"), "r") as f:
    GEMINI_API_KEY = f.read().strip()

# Gemini API konfigurieren
genai.configure(api_key=GEMINI_API_KEY)

def get_modified_files(repo):
    """Gibt eine Liste der geänderten Dateien zurück."""
    changed_files = [item.a_path for item in repo.index.diff(None)]
    print(f"DEBUG: Geänderte Dateien: {changed_files}")  # Debug-Output
    return changed_files

def get_diff_for_file(repo, file_path):
    """Gibt den Diff einer Datei zurück."""
    diff = repo.git.diff('HEAD', '--', file_path)
    print(f"DEBUG: Diff für {file_path}:\n{diff}")  # Debug-Output
    return diff

def generate_commit_message(file_diffs):
    """Generiert eine Commit-Nachricht basierend auf den Dateidiffs."""
    prompt = "Erstelle eine Git-Commit-Nachricht basierend auf den folgenden Änderungen:\n"
    for file_path, diff in file_diffs.items():
        prompt += f"\nDatei: {file_path}\nÄnderungen:\n{diff}\n"

    print(f"DEBUG: Prompt für Gemini:\n{prompt}")  # Debug-Output

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    print(f"DEBUG: Antwort von Gemini:\n{response.text}")  # Debug-Output

    return response.text if response and response.text else "Default commit message"

def main():
    repo = Repo(os.getcwd())

    # Überprüfe, ob das Repository Änderungen oder untracked Files enthält
    has_changes = repo.is_dirty(untracked_files=True)
    untracked_files = repo.untracked_files  # Liste der untracked Files

    if has_changes or untracked_files:
        if untracked_files:
            print("\nUntracked Files gefunden:")
            for file in untracked_files:
                print(f" - {file}")

            # Nutzer fragen, ob die Dateien hinzugefügt werden sollen
            user_input = input("\nMöchtest du alle untracked Dateien hinzufügen? (y/n): ").strip().lower()
            if user_input == 'y':
                repo.git.add(all=True)  # Untracked Files hinzufügen
                print("Untracked Files wurden hinzugefügt.")

        modified_files = get_modified_files(repo)

        if not modified_files:
            print("Keine modifizierten Dateien gefunden. Abbruch.")
            return

        file_diffs = {file: get_diff_for_file(repo, file) for file in modified_files}

        commit_message = generate_commit_message(file_diffs)

        # Schreiben der Commit-Nachricht in eine temporäre Datei
        with open('COMMIT_MSG.txt', 'w') as f:
            f.write(commit_message)

        # Öffnen des Editors für die Commit-Nachricht
        editor = os.getenv('EDITOR', 'vim')
        subprocess.call([editor, 'COMMIT_MSG.txt'])

        # Lesen der bearbeiteten Commit-Nachricht
        with open('COMMIT_MSG.txt', 'r') as f:
            final_commit_message = f.read().strip()

        # Entfernen der temporären Datei
        os.remove('COMMIT_MSG.txt')

        # Änderungen committen
        repo.index.commit(final_commit_message)

        # Überprüfen, ob ein 'origin' Remote gesetzt ist und Push durchführen
        if 'origin' in [remote.name for remote in repo.remotes]:
            origin = repo.remote('origin')
            origin.push()
        else:
            print("Kein 'origin' Remote gefunden. Überspringe 'git push'.")
    else:
        print("Keine Änderungen zum Committen.")

if __name__ == "__main__":
    main()
