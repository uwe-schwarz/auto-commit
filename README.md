# AutoCommit

## Beschreibung

`autocommit` ist ein Python-Skript, das automatisch geänderte Dateien in einem Git-Repository erkennt, deren Änderungen ausliest und mit Hilfe der Google Gemini API eine Commit-Nachricht generiert. Anschließend wird der Commit in einem Editor zur Bearbeitung geöffnet und bei Bedarf automatisch gepusht.

Das Skript unterstützt:
- Erkennung von **untracked** und **modifizierten, aber nicht gestagten** Dateien
- Manuelle Bestätigung zum **Hinzufügen neuer oder geänderter Dateien**
- Automatische Generierung einer Commit-Nachricht mit Google Gemini
- Bearbeitung der Commit-Nachricht im bevorzugten Editor (`$EDITOR` oder `vim`)
- Automatisches **Committen und Pushen**, falls ein `origin`-Remote vorhanden ist

## Installation

### Voraussetzungen

- Python 3.x
- `git` installiert
- Google Gemini API-Zugang (API-Key erforderlich)
- `pip` für Paketverwaltung

### 1. **Repository klonen und Abhängigkeiten installieren**

```bash
git clone https://github.com/dein-user/autocommit.git ~/dev/auto-commit
cd ~/dev/auto-commit
pip install -r requirements.txt
```

### Gemini API-Key einrichten

Speichere deinen API-Key in einer .env-Datei im Hauptverzeichnis des Projekts. Ein Beispiel für das Format findest du in der Datei env.example.

1. Erstelle die .env-Datei basierend auf dem Beispiel:

```bash
cp env.example .env
```

2. Öffne die .env-Datei und füge deinen API-Schlüssel ein:

```
GEMINI_API_KEY=dein_api_schlüssel_hier
```

### Skript als ausführbare Datei einrichten

1. Stelle sicher, dass du dich im auto-commit-Verzeichnis befindest und eine virtuelle Umgebung (venv) nutzt:

```bash
cd ~/dev/auto-commit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Erstelle ein Wrapper-Skript in ~/.local/bin, um auto-commit.py mit der virtuellen Umgebung auszuführen:

```bash
mkdir -p ~/.local/bin
echo '#!/bin/bash
source ~/dev/auto-commit/.venv/bin/activate
python3 ~/dev/auto-commit/auto-commit.py "$@"' > ~/.local/bin/autocommit
chmod +x ~/.local/bin/autocommit
```

3. Falls ~/.local/bin nicht im PATH ist, füge es deiner Shell-Config hinzu:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # für Bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc   # für Zsh
source ~/.bashrc  # oder `source ~/.zshrc`
```

Jetzt kannst du autocommit von überall ausführen! 🚀

## Verwendung

### Automatischen Commit mit AI-Generierung ausführen

```bash
autocommit
```

Das Skript wird:

1. Alle geänderten, aber nicht gestagten und neuen Dateien erkennen.
2. Fragen, ob sie hinzugefügt werden sollen.
3. Die Änderungen mit der Google Gemini API analysieren.
4. Eine Commit-Nachricht vorschlagen.
5. Den Editor zur Bearbeitung der Nachricht öffnen.
6. Nach Bestätigung den Commit ausführen.
7. Falls ein origin-Remote vorhanden ist, den Push ausführen.

Sprache der Commit-Nachricht anpassen

Die Commit-Nachricht kann in einer beliebigen Sprache generiert werden.
Dazu kann die Sprache entweder in der .env-Datei gesetzt werden:

```
COMMIT_LANGUAGE=Deutsch
```

Oder direkt beim Aufruf des Skripts als Parameter übergeben werden:

```bash
autocommit --lang Englisch
autocommit --lang Französisch
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

Generiere Commit-Nachricht mit Gemini...
Commit-Nachricht:
feat: Automatische Erkennung und AI-generierte Commit-Messages hinzugefügt

Dieses Commit fügt ein Skript hinzu, das geänderte und neue Dateien erkennt und eine AI-generierte Commit-Nachricht vorschlägt.

Öffne Editor für die Commit-Nachricht...
Commit abgeschlossen.

Kein 'origin' Remote gefunden. Überspringe 'git push'.
```

## Fehlerbehebung

Falls das Skript nicht gefunden wird:

```bash
hash -r  # Cache für executables erneuern
```

Falls autocommit einen Import-Fehler meldet:

```bash
pip install --force-reinstall -r requirements.txt
```

Falls ~/.local/bin nicht im PATH ist:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Lizenz

MIT License – Open Source & für eigene Zwecke anpassbar. 🚀

### **Zusammenfassung**

✅ **Installationsanleitung** für lokale Nutzung  
✅ **Globale Nutzung mit `autocommit`**  
✅ **Beispielausgabe für Klarheit**  
✅ **Fehlerbehebungstipps**  
✅ **AI-generierte Commit-Messages in deiner bevorzugten Sprache**  

Jetzt kannst du das Skript einfach per `autocommit` von überall starten! 🚀
