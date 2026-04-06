# AutoCommit

## Beschreibung

`autocommit` ist ein Python-Skript, das geänderte Dateien in einem Git-Repository erkennt, ihre Diffs einsammelt und automatisch eine Commit-Nachricht erzeugt. Du kannst entweder den eingebauten Provider-Modus mit **Google Gemini** (über `google-genai`), **Z.AI GLM Coding Plan** (OpenAI-kompatibel, z. B. `GLM-4.6`) und **OpenAI** verwenden oder auf macOS einen **Shortcuts-Modus** nutzen. Danach öffnet sich dein Editor zur Feinjustierung, und auf Wunsch wird automatisch gepusht.

Das Skript unterstützt:
- Erkennung von **untracked** und **modifizierten, aber nicht gestagten** Dateien
- Manuelle Bestätigung zum **Hinzufügen neuer oder geänderter Dateien**
- Automatische Commit-Generierung über Gemini, Z.AI GLM (Coding API), OpenAI **oder** macOS Shortcuts
- Bearbeitung der Commit-Nachricht im bevorzugten Editor (`$EDITOR` oder `vim`)
- Automatisches **Committen und Pushen**, falls ein `origin`-Remote vorhanden ist

## Installation

### Voraussetzungen

- Python 3.x
- `git`
- API-Key für **Google Gemini**, **Z.AI GLM Coding Plan** oder **OpenAI**; alternativ macOS mit installiertem Shortcut
- `pip`

### 1. Repository klonen und Abhängigkeiten installieren

```bash
git clone https://github.com/dein-user/autocommit.git ~/dev/auto-commit
cd ~/dev/auto-commit
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/pip install --upgrade --upgrade-strategy eager -r requirements.txt
```

### 2. .env anlegen und Provider konfigurieren

Beispiel siehe `env.example`. Kopiere die Datei und trage deine Keys ein:

```bash
cp env.example .env
```

Wichtige Variablen:
- `COMMIT_MODE`: `provider` (Standard) oder `shortcuts`
- `AI_PROVIDER`: `gemini` (Standard), `zai` oder `openai`
- Gemini: `GEMINI_API_KEY`, optional `GEMINI_MODEL`
- Z.AI: `ZAI_API_KEY`, optional `ZAI_MODEL`, `ZAI_BASE_URL` (Standard: `https://api.z.ai/api/coding/paas/v4` – **Coding API**, nicht die General API)
- OpenAI: `OPENAI_API_KEY`, optional `OPENAI_MODEL`, optional `OPENAI_BASE_URL`
- macOS Shortcuts: `MACOS_SHORTCUT_NAME` (Standard: `auto-commit-chatgpt`)
- `COMMIT_LANGUAGE`: Sprache der Commit-Nachricht
- `NO_PUSH`: `true` oder `false` (Standard: `false`) – Überspringt den `git push` nach dem Commit

## macOS Shortcuts-Modus

Wenn du lieber die lokale macOS-Shortcuts-Integration verwenden willst, setze:

```bash
COMMIT_MODE=shortcuts
MACOS_SHORTCUT_NAME=auto-commit-chatgpt
```

Der Shortcut bekommt exakt denselben Prompt wie der eingebaute Modellpfad. Die Übergabe erfolgt als echter Texteingang über AppleScript und `Shortcuts Events`, nicht als Datei-Upload:

```bash
osascript - auto-commit-chatgpt /tmp/prompt.txt <<'APPLESCRIPT'
on run argv
    set shortcutName to item 1 of argv
    set inputPath to item 2 of argv
    set promptText to read POSIX file inputPath
    tell application "Shortcuts Events"
        return run shortcut shortcutName with input promptText
    end tell
end run
APPLESCRIPT
```

Der Modus prüft beim Start:
- dass das System auf macOS läuft
- dass die `shortcuts`-CLI verfügbar ist
- dass der konfigurierte Shortcut tatsächlich existiert

Shortcut-Link für `auto-commit-chatgpt`:
- https://www.icloud.com/shortcuts/5f66f53029b04ab699fbd8b53bd3d1da

### 3. Skript als ausführbare Datei einrichten (optional)

```bash
cd ~/dev/auto-commit
./scripts/refresh-venv.sh

mkdir -p ~/.local/bin
echo '#!/bin/bash
source ~/dev/auto-commit/.venv/bin/activate
python3 ~/dev/auto-commit/auto-commit.py "$@"' > ~/.local/bin/autocommit
chmod +x ~/.local/bin/autocommit
```

Falls `~/.local/bin` nicht im PATH ist:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc   # oder ~/.bashrc
source ~/.zshrc
```

## Provider-spezifische Hinweise

- **Google Gemini**: Nutzt die `google-genai` API. Modell per `.env` (`GEMINI_MODEL`) oder CLI `--model`.
- **Z.AI GLM Coding Plan**: OpenAI-kompatibel. Verwende die Coding-Endpoint `https://api.z.ai/api/coding/paas/v4` und setze das Modell (`GLM-4.7`, `GLM-4.6`, `GLM-4.5`, `GLM-4.5-air`).
- **OpenAI**: Nutzt die `openai` Python SDK (`chat.completions`). Standardmodell ist `gpt-5.4-mini` (per `.env` `OPENAI_MODEL` oder via `--model`). Eine aktuelle Modell-Liste (Model-IDs für `--model`/`OPENAI_MODEL`) findest du hier: https://platform.openai.com/docs/models

## Verwendung

```bash
autocommit
```

CLI-Optionen:
- `--lang`: Sprache der Commit-Nachricht
- `--mode`: `provider` oder `shortcuts`
- `--provider`: `gemini`, `zai` oder `openai` (überschreibt `.env`)
- `--model`: Modellname für den gewählten Provider
- `--shortcut-name`: Name des macOS-Shortcuts für `--mode shortcuts`
- `--zai-base-url`: eigenes Base-URL für die Z.AI Coding API (Standard ist bereits gesetzt)
- `--openai-base-url`: optional eigenes Base-URL für OpenAI
- `--style`: Commit-Stil: `sarcastic`, `humorous` oder `standard` (default)
- `--no-push`: Überspringt den `git push` nach dem Commit (kann auch via `.env` mit `NO_PUSH=true` gesetzt werden)

Beispiele:

- Gemini nutzen (Standard):
  ```bash
  autocommit --lang Englisch --model gemini-2.5-flash
  ```

- Z.AI GLM Coding Plan:
  ```bash
  autocommit --provider zai --model GLM-4.7 --zai-base-url https://api.z.ai/api/coding/paas/v4
  ```

- OpenAI:
  ```bash
  autocommit --provider openai --model gpt-5.4-mini
  ```

- macOS Shortcuts:
  ```bash
  autocommit --mode shortcuts --shortcut-name auto-commit-chatgpt
  ```

- Sarcastic Commit-Style:
  ```bash
  autocommit --style sarcastic
  ```

## Beispielausgabe

```
Untracked Files gefunden:
 - new_script.py
 - config.json

Möchtest du alle untracked Dateien hinzufügen? (y/n): y
Untracked Files wurden hinzugefügt.

Modifizierte, aber nicht gestagte Dateien gefunden:
 - main.py
 - utils.py

Möchtest du alle unstaged Dateien hinzufügen? (y/n): y
Unstaged Files wurden hinzugefügt.

Commit-Nachricht:
feat: Automatische Erkennung und AI-generierte Commit-Messages hinzugefügt

Dieses Commit fügt ein Skript hinzu, das geänderte und neue Dateien erkennt und eine AI-generierte Commit-Nachricht vorschlägt.

Öffne Editor für die Commit-Nachricht...
Commit abgeschlossen.

Kein 'origin' Remote gefunden. Überspringe 'git push'.
```

## Fehlerbehebung

- `hash -r` falls das Skript nach Installation nicht gefunden wird.
- `./scripts/refresh-venv.sh` nach Updates oder bei Import-Problemen.
- Wenn du bewusst immer die neuesten auflösbaren Versionen willst: keine bestehende `.venv` reparieren, sondern immer die venv frisch mit `./scripts/refresh-venv.sh` neu bauen.
- `--mode shortcuts` funktioniert nur auf macOS und bricht sauber ab, wenn der konfigurierte Shortcut fehlt.
- PATH prüfen: `export PATH="$HOME/.local/bin:$PATH"`.

## Lizenz

MIT License – Open Source & für eigene Zwecke anpassbar. 🚀
