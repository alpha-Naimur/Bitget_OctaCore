"""Unit and Integration Tests for Bitget OctaCore."""

import sys

# Ensure AppLocker/Application Control DLL blocking on pyarrow does not crash pandas
try:
    import pyarrow  # noqa: F401
except (ImportError, Exception):
    sys.modules["pyarrow"] = None
