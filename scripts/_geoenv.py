"""Point PROJ/GDAL at the active conda env's data dirs BEFORE importing pyproj/osgeo.

Rationale: this machine has a system PROJ_LIB pointing at a PostgreSQL/PostGIS
proj.db, which is incompatible with the conda-forge PROJ and breaks CRS lookups.
Importing this module first makes every script self-correcting and reproducible.

Usage (must be the FIRST project import, before geopandas/pyproj/osgeo):
    import _geoenv  # noqa: F401  (sets PROJ_DATA/PROJ_LIB/GDAL_DATA)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_lib = Path(sys.prefix) / "Library"
_share = _lib / "share"
_proj = _share / "proj"
_gdal = _share / "gdal"
if _proj.exists():
    os.environ["PROJ_DATA"] = str(_proj)
    os.environ["PROJ_LIB"] = str(_proj)
if _gdal.exists():
    os.environ["GDAL_DATA"] = str(_gdal)

# Ensure the conda env's native DLLs (libpng/zlib/freetype/GEOS/...) are found
# instead of stray system copies on PATH — otherwise matplotlib's PNG writer and
# some GEOS paths hard-abort when python.exe is run without activating the env.
for _dll in (_lib / "bin", _lib / "mingw-w64" / "bin", Path(sys.prefix)):
    if _dll.exists():
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(_dll))
            except OSError:
                pass
        os.environ["PATH"] = str(_dll) + os.pathsep + os.environ.get("PATH", "")

# Preferred OGR driver for the HWSD2 Access database on this system (ODBC works;
# the Java 'MDB' driver is absent in conda-forge GDAL). Scripts may override.
HWSD_MDB_OGR_DRIVER = "ODBC"
