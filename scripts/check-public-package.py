#!/usr/bin/env python3
"""Audita o pacote público contra dados de estação e segredos acidentais."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "venv", ".venv", "__pycache__", "static/vendor"}
MAX_BYTES = 2_000_000

PATTERNS = [
    (
        "SSID específico da estação de desenvolvimento",
        re.compile(r"\bPP5CI-\d{1,2}\b", re.IGNORECASE),
    ),
    (
        "passcode APRS-IS literal",
        re.compile(r"(?im)^\s*IGLOGIN\s+\S+\s+(?!00000\b)\d{1,5}\b"),
    ),
    (
        "passcode APRS-IS em variável de ambiente",
        re.compile(r"(?im)^\s*APRS_PASSCODE\s*=\s*\d{1,5}\s*$"),
    ),
    (
        "coordenadas literais em filtro APRS-IS",
        re.compile(
            r"(?im)^\s*IGFILTER\s+r/(?!0(?:\.0+)?/0(?:\.0+)?/)"
            r"[-+]?\d+(?:\.\d+)?/[-+]?\d+(?:\.\d+)?/\d+(?:\.\d+)?\s*$"
        ),
    ),
    (
        "coordenadas literais em beacon Direwolf",
        re.compile(
            r"(?im)^\s*#?(?:PBEACON|OBEACON)\b"
            r"(?=[^\n]*\b(?:LAT|LONG)=(?!0(?:\.0+)?\b)[-+]?\d+(?:\.\d+)?)[^\n]*$"
        ),
    ),
    (
        "token GitHub clássico",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "token GitHub fine-grained",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    ),
    (
        "chave OpenAI",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "chave privada",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
]


def skipped(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel == item or rel.startswith(item + "/") for item in SKIP_DIRS)


def main() -> int:
    findings: list[tuple[str, int, str, str]] = []

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or skipped(path):
            continue

        try:
            raw = path.read_bytes()
        except OSError:
            continue

        if len(raw) > MAX_BYTES or b"\0" in raw:
            continue

        text = raw.decode("utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()

        for label, pattern in PATTERNS:
            for match in pattern.finditer(text):
                lineno = text.count("\n", 0, match.start()) + 1
                line = text.splitlines()[lineno - 1].strip()
                findings.append((rel, lineno, label, line))

    if findings:
        print("ERRO: o pacote público contém dados/segredos que não devem ser publicados:")
        for rel, lineno, label, line in findings:
            print(f"  {rel}:{lineno}: {label}: {line}")
        return 1

    print("Auditoria pública: nenhum hardcode/segredo detectado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
