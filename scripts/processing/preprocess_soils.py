"""HWSD soil derivation entry point.

Superseded by derive_hwsd_iran.py, which performs the SCHEMA_LOCKED-gated
dominant WRB-2022 Reference Soil Group derivation for Iran. This wrapper keeps
the historical filename working and delegates to it.
"""
from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).with_name("derive_hwsd_iran.py")
    runpy.run_path(str(target), run_name="__main__")
