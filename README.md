# AutoCommit

## Beschreibung

`autocommit` ist ein Python-Skript, das geänderte Dateien in einem Git-Repository erkennt, ihre Diffs einsammelt und automatisch eine Commit-Nachricht erzeugt. Du kannst zwischen **Google Gemini** (über `google-genai`), **Z.AI GLM Coding Plan** (OpenAI-kompatibel, z. B. `GLM-4.6`) und **OpenAI** wählen. Danach öffnet sich dein Editor zur Feinjustierung, und auf Wunsch wird automatisch gepusht.

Das Skript unterstützt:
- Erkennung von **untracked** und **modifizierten, aber nicht gestagten** Dateien
- Manuelle Bestätigung zum **Hinzufügen neuer oder geänderter Dateien**
- Automatische Commit-Generierung über Gemini, Z.AI GLM (Coding API) **oder** OpenAI
- Bearbeitung der Commit-Nachricht im bevorzugten Editor (`$EDITOR` oder `vim`)
- Automatisches **Committen und Pushen**, falls ein `origin`-Remote vorhanden ist

## Installation

### Voraussetzungen

- Python 3.x
- `git`
- API-Key für **Google Gemini**, **Z.AI GLM Coding Plan** oder **OpenAI**
- `pip`

### 1. Repository klonen und Abhängigkeiten installieren

```bash
git clone https://github.com/dein-user/autocommit.git ~/dev/auto-commit
cd ~/dev/auto-commit
pip install -r requirements.txt
```

### 2. .env anlegen und Provider konfigurieren

Beispiel siehe `env.example`. Kopiere die Datei und trage deine Keys ein:

```bash
cp env.example .env
```

Wichtige Variablen:
- `AI_PROVIDER`: `gemini` (Standard), `zai` oder `openai`
- Gemini: `GEMINI_API_KEY`, optional `GEMINI_MODEL`
- Z.AI: `ZAI_API_KEY`, optional `ZAI_MODEL`, `ZAI_BASE_URL` (Standard: `https://api.z.ai/api/coding/paas/v4` – **Coding API**, nicht die General API)
- OpenAI: `OPENAI_API_KEY`, optional `OPENAI_MODEL`, optional `OPENAI_BASE_URL`
- `COMMIT_LANGUAGE`: Sprache der Commit-Nachricht

### 3. Skript als ausführbare Datei einrichten (optional)

```bash
cd ~/dev/auto-commit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

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
- **Z.AI GLM Coding Plan**: OpenAI-kompatibel. Verwende die Coding-Endpoint `https://api.z.ai/api/coding/paas/v4` und setze das Modell (`GLM-4.6`, `GLM-4.5`, `GLM-4.5-air`). Ältere Accounts vor 2025-09-30 sollten auf `GLM-4.6` wechseln.
- **OpenAI**: Nutzt die `openai` Python SDK (`chat.completions`). Standardmodell ist `gpt-4o-mini` (per `.env` `OPENAI_MODEL` oder via `--model`). Eine aktuelle Modell-Liste (Model-IDs für `--model`/`OPENAI_MODEL`) findest du hier: https://platform.openai.com/docs/models

## Verwendung

```bash
autocommit
```

CLI-Optionen:
- `--lang`: Sprache der Commit-Nachricht
- `--provider`: `gemini`, `zai` oder `openai` (überschreibt `.env`)
- `--model`: Modellname für den gewählten Provider
- `--zai-base-url`: eigenes Base-URL für die Z.AI Coding API (Standard ist bereits gesetzt)
- `--openai-base-url`: optional eigenes Base-URL für OpenAI

Beispiele:

- Gemini nutzen (Standard):
  ```bash
  autocommit --lang Englisch --model gemini-2.0-flash
  ```

- Z.AI GLM Coding Plan:
  ```bash
  autocommit --provider zai --model GLM-4.6 --zai-base-url https://api.z.ai/api/coding/paas/v4
  ```

- OpenAI:
  ```bash
  autocommit --provider openai --model gpt-4o-mini
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
- `pip install --force-reinstall -r requirements.txt` bei Import-Problemen.
- PATH prüfen: `export PATH="$HOME/.local/bin:$PATH"`.

## Lizenz

MIT License – Open Source & für eigene Zwecke anpassbar. 🚀
