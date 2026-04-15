#!/usr/bin/env python3
"""Executa a suite automatizada e grava o resultado em tests/logs/."""

from __future__ import annotations

import contextlib
import io
import sys
import time
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = PROJECT_ROOT / "tests"
LOGS_ROOT = TESTS_ROOT / "logs"
LOG_PATH = LOGS_ROOT / "latest-test-run.log"


def main() -> int:
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(TESTS_ROOT / "scripts"), pattern="test_*.py")

    stream = io.StringIO()
    side_output = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    started_at = time.strftime("%Y-%m-%d %H:%M:%S")
    with contextlib.redirect_stdout(side_output), contextlib.redirect_stderr(side_output):
        result = runner.run(suite)
    finished_at = time.strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "Suite de testes automatizados - Mapas_Escolas_ES",
        f"Inicio: {started_at}",
        f"Fim: {finished_at}",
        "",
        side_output.getvalue().rstrip(),
        "",
        stream.getvalue().rstrip(),
        "",
        f"Sucesso: {result.wasSuccessful()}",
        f"Total executado: {result.testsRun}",
        f"Falhas: {len(result.failures)}",
        f"Erros: {len(result.errors)}",
    ]
    report = "\n".join(lines) + "\n"
    LOG_PATH.write_text(report, encoding="utf-8")
    sys.stdout.write(report)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
