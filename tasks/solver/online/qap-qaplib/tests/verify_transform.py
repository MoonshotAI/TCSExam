#!/usr/bin/env python3
"""Release-time verification of the qap-qaplib form2 structure-preserving transformation.

This is a release-time entry point that does not depend on the private manifest.
All checks are implemented in tests/test_transform.py (three mathematical checks,
a set-consistency gate, and oracle recomputation); this file only preserves the
existing invocation path.

For task authors and reviewers: rerun after changing transform.py, scored
instances, references, or the oracle package.

Run with `python3 tests/verify_transform.py` from the task root or any directory."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import test_transform  # noqa: E402

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(test_transform)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
