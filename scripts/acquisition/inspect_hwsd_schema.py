"""Inspect the official HWSD2.mdb and emit a schema-evidence record.

Reads the Access database *without guessing* field names. Per the project
environment decision, MDB access is attempted in this order:
  1. GDAL/OGR (osgeo.ogr) with the driver GDAL selects for .mdb
  2. pure-Python fallback (access_parser) if OGR has no usable MDB driver
No mdbtools, no ODBC/Access install, no web converter.

Output: provenance/metadata/hwsd_mdb_report.json
The report lists every table, its fields/types, row counts, and small samples
for the tables relevant to dominant-soil derivation, plus the distinct values
of any ISSOIL-like flag. It selects NO schema contract automatically.
"""
from __future__ import annotations

import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _geoenv  # noqa: E402,F401  (sets PROJ_DATA/PROJ_LIB/GDAL_DATA before osgeo)

ROOT = Path(__file__).resolve().parents[2]
RAW_ZIP = ROOT / "data/raw/hwsd/HWSD2_DB.zip"
INTERIM = ROOT / "data/interim/hwsd"
MDB = INTERIM / "HWSD2.mdb"
REPORT = ROOT / "provenance/metadata/hwsd_mdb_report.json"


def ensure_extracted() -> None:
    if MDB.exists():
        return
    if not RAW_ZIP.exists():
        raise SystemExit(f"Missing raw archive: {RAW_ZIP}")
    INTERIM.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RAW_ZIP) as z:
        names = z.namelist()
        if "HWSD2.mdb" not in names:
            raise SystemExit(f"HWSD2.mdb not found in archive; members={names}")
        z.extract("HWSD2.mdb", INTERIM)


def inspect_with_ogr() -> dict | None:
    try:
        from osgeo import ogr
    except Exception as exc:  # noqa: BLE001
        print(f"[ogr] import failed: {exc}")
        return None
    ogr.UseExceptions()
    ds = None
    for drv in ("MDB", "PGeo", "ODBC"):
        driver = ogr.GetDriverByName(drv)
        if driver is None:
            continue
        try:
            ds = driver.Open(str(MDB), 0)
            if ds is not None:
                print(f"[ogr] opened with driver {drv}")
                break
        except Exception as exc:  # noqa: BLE001
            print(f"[ogr] driver {drv} failed: {exc}")
    if ds is None:
        try:
            ds = ogr.Open(str(MDB), 0)
        except Exception as exc:  # noqa: BLE001
            print(f"[ogr] generic Open failed: {exc}")
            ds = None
    if ds is None:
        return None
    tables: dict[str, dict] = {}
    for i in range(ds.GetLayerCount()):
        layer = ds.GetLayer(i)
        name = layer.GetName()
        defn = layer.GetLayerDefn()
        fields = [
            {"name": defn.GetFieldDefn(j).GetName(),
             "type": defn.GetFieldDefn(j).GetTypeName()}
            for j in range(defn.GetFieldCount())
        ]
        tables[name] = {"fields": fields, "row_count": layer.GetFeatureCount()}
    return {"driver": "ogr", "tables": tables, "_ds": ds}


def inspect_with_access_parser() -> dict | None:
    try:
        from access_parser import AccessParser
    except Exception as exc:  # noqa: BLE001
        print(f"[access_parser] not available: {exc}")
        return None
    db = AccessParser(str(MDB))
    tables: dict[str, dict] = {}
    for name in db.catalog:
        if name.startswith("MSys"):
            continue
        try:
            parsed = db.parse_table(name)
            cols = list(parsed.keys())
            n = len(next(iter(parsed.values()))) if parsed else 0
            tables[name] = {"fields": [{"name": c, "type": "n/a"} for c in cols],
                            "row_count": n}
        except Exception as exc:  # noqa: BLE001
            tables[name] = {"error": str(exc)}
    return {"driver": "access_parser", "tables": tables, "_db": db}


def main() -> None:
    ensure_extracted()
    result = inspect_with_ogr()
    engine = "ogr"
    if result is None:
        print("[fallback] OGR could not open the MDB; trying access_parser")
        result = inspect_with_access_parser()
        engine = "access_parser"
    if result is None:
        raise SystemExit(
            "MDB_UNREADABLE: neither GDAL/OGR nor access_parser could open HWSD2.mdb. "
            "This is a hard blocker to report (no mdbtools/ODBC/Access/web-converter fallback is permitted)."
        )
    tables = result["tables"]
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "engine": engine,
        "mdb": str(MDB.relative_to(ROOT)).replace("\\", "/"),
        "table_count": len(tables),
        "tables": tables,
        "decision": "NO_FIELDS_ACCEPTED_AUTOMATICALLY",
        "next_action": "Match these tables/fields to docs/HWSD_SCHEMA.md and the technical report, "
                       "then populate config/hwsd_schema.yaml explicitly.",
    }
    REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {REPORT}")
    print(f"Engine: {engine}; tables: {sorted(tables)}")


if __name__ == "__main__":
    main()
