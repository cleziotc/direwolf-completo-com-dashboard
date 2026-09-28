#!/usr/bin/env bash

set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
DEFAULT_REPO="$(cd "$(dirname "$SCRIPT_PATH")/.." && pwd)"
REPO="${APRS_DASHBOARD_DIR:-$DEFAULT_REPO}"
PYTHON="$REPO/venv/bin/python"
SERVICE="aprs-dashboard.service"

cd "$REPO"

if [[ "${EUID}" -eq 0 ]]; then
    echo "Execute como o usuario de servico APRS, sem sudo."
    exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Existem alteracoes locais. Instalacao cancelada:"
    git status --short
    exit 1
fi

export REPO
"$PYTHON" - <<'PY'
import os
from pathlib import Path

repo = Path(os.environ.get("APRS_DASHBOARD_DIR", os.environ["REPO"]))
app_path = repo / "app.py"
index_path = repo / "static" / "index.html"

app = app_path.read_text()
index = index_path.read_text()

app_hook = """

# ============================================================
# EXTENSOES DO DASHBOARD
# ============================================================

try:
    from dashboard_extensions import register_routes

    register_routes(
        app
    )

except Exception as exc:

    print(
        f"[dashboard_extensions] {exc}",
        flush=True
    )
"""

if "from dashboard_extensions import register_routes" not in app:
    app = app.rstrip() + app_hook + "\n"

css_hook = """
    <link
        rel="stylesheet"
        href="/static/dashboard-v2.css"
    >
"""

if "/static/dashboard-v2.css" not in index:
    index = index.replace(
        "</head>",
        css_hook + "\n</head>",
        1
    )

js_hook = """
<script src="/static/dashboard-v2.js"></script>
"""

if "/static/dashboard-v2.js" not in index:
    index = index.replace(
        "</body>",
        js_hook + "\n</body>",
        1
    )

app_path.write_text(app)
index_path.write_text(index)
PY

"$PYTHON" -m py_compile     app.py     database.py     dashboard_extensions.py

git add     app.py     static/index.html

if ! git diff --cached --quiet; then
    git commit -m "Instala hooks do dashboard v0.2"
    git push origin main
else
    echo "Hooks ja estavam instalados."
fi

sudo ln -sfn     "$REPO/scripts/aprs-update.sh"     /usr/local/bin/aprs-update

sudo systemctl restart "$SERVICE"

for attempt in $(seq 1 15); do
    if curl -fsS         --max-time 3         http://127.0.0.1:8088/api/overview         >/dev/null 2>&1; then

        echo "Dashboard v0.2 instalado e API /api/overview operacional."
        exit 0
    fi

    sleep 1
done

echo "Falha: /api/overview nao respondeu apos a instalacao."
exit 1
