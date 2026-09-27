"""Run CPython's list tests against this coverage build.

The suites stay in the adjacent CPython tree (Lib/test). test_list also
runs the shared cases in list_tests.py and seq_tests.py.
"""

import sys
import unittest

MODULES = (
    "test.test_list",
    "test.test_sort",
    "test.test_listcomps",
    "test.test_capi.test_list",
)


def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in MODULES:
        module = __import__(name, fromlist=["_"])
        suite.addTests(loader.loadTestsFromModule(module))

    result = unittest.TextTestRunner(verbosity=1).run(suite)
    print(
        f"{result.testsRun} tests, "
        f"{len(result.failures)} failed, "
        f"{len(result.errors)} errors",
        file=sys.stderr,
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
