"""Inspect the official HWSD archive and emit an evidence record; never select fields by guesswork."""
from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/hwsd/HWSD2_DB.zip"
INTERIM = ROOT / "data/interim/hwsd_database"
REPORT = ROOT / "provenance/metadata/hwsd_schema_report.json"


def run(*args: str) -> str:
    executable = shutil.which(args[0])
    if executable is None:
        raise SystemExit(f"Required executable not found: {args[0]}. Create environment.yml first.")
    return subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")


def main() -> None:
    if not RAW.exists():
        raise SystemExit(f"Official database archive missing: {RAW}. Run acquire_hwsd.py first.")
    if INTERIM.exists():
        raise SystemExit(f"Refusing to overwrite interim extraction: {INTERIM}. Remove only after preserving its metadata.")
    with zipfile.ZipFile(RAW) as archive:
        archive.extractall(INTERIM)
        members = archive.namelist()
    databases = list(INTERIM.rglob("*.mdb"))
    if len(databases) != 1:
        raise SystemExit(f"Expected exactly one .mdb after extraction; found {len(databases)}.")
    database = databases[0]
    tables = [value.strip() for value in run("mdb-tables", "-1", str(database)).splitlines() if value.strip()]
    table_fields: dict[str, list[str]] = {}
    for table in tables:
        schema = run("mdb-schema", str(database), "access", table)
        table_fields[table] = [line.strip() for line in schema.splitlines() if line.strip()]
    candidates = {
        table: [line for line in fields if any(token in line.upper() for token in ("SMU", "SHARE", "SEQ", "ISSOIL", "WRB", "SU_SYM"))]
        for table, fields in table_fields.items()
    }
    REPORT.write_text(json.dumps({
        "dataset_id": "fao_iiasa_hwsd_v201_database",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "raw_archive": str(RAW.relative_to(ROOT)).replace("\\", "/"),
        "extracted_database": str(database.relative_to(ROOT)).replace("\\", "/"),
        "archive_members": members,
        "tables": tables,
        "table_schema_ddl": table_fields,
        "candidate_semantic_fields": candidates,
        "decision": "NO_FIELDS_ACCEPTED_AUTOMATICALLY",
        "next_action": "Populate config/hwsd_schema.yaml only after matching these fields to the official technical report.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Schema evidence written to {REPORT}")


if __name__ == "__main__":
    main()
