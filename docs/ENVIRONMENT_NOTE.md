# Environment note

Use `environment-geospatial.yml` as the canonical environment specification. It includes `mdbtools`, the MDB inspection executable required by `scripts/acquisition/inspect_hwsd_schema.py`, along with the GDAL/GeoPandas/Rasterio stack.

`environment.yml` is retained as the minimal initial proposal. It is superseded for runnable work by `environment-geospatial.yml`; this avoids silently assuming that an Access/MDB driver is installed on a machine.
