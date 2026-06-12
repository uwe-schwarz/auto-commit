#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Syncing uv environment in $ROOT_DIR"
uv sync

echo "Running smoke test"
uv run autocommit --help >/dev/null

echo "Installing ~/.local/bin/autocommit wrapper"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/autocommit" <<WRAPPER
#!/usr/bin/env bash
exec uv run --project "$ROOT_DIR" autocommit "\$@"
WRAPPER
chmod +x "$HOME/.local/bin/autocommit"

echo "uv environment and autocommit wrapper are ready"
