#!/usr/bin/env python3
"""Run the local suite and emit a success-only verification marker."""
from pathlib import Path
import sys
import unittest

root=Path(__file__).resolve().parents[1]
suite=unittest.defaultTestLoader.discover(str(root/'tests'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
print(f'DIAGRAM_LEDGER_TESTS_PASSED: {result.testsRun} tests; {len(result.skipped)} skipped')
