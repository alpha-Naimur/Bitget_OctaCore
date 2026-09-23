"""Bitget OctaCore - Institutional Multi-Agent Autonomous AI Trading Operating System."""

import sys

# Ensure AppLocker/Application Control DLL blocking on pyarrow does not crash pandas
try:
    import pyarrow  # noqa: F401
except (ImportError, Exception):
    sys.modules["pyarrow"] = None

__version__ = "2.0.0"
__author__ = "Bitget AI Base Camp Hackathon S2 Team"

