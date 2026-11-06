"""Shared helpers: NaN-safe conversion and generic idempotent MERGE (upsert)."""
import math
from typing import Any

from sqlalchemy import text


def to_none(x: Any):
    """Return a float, or None for None/NaN/inf. SQL Server cannot store NaN in DECIMAL."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(v) or math.isinf(v)) else v


def merge_rows(conn, table: str, rows: list[dict], types: dict[str, str], keys: list[str]) -> int:
    """Upsert rows with SQL Server MERGE. Re-running never creates duplicates.

    types maps column -> SQL type; values are CAST so NULLs are typed correctly.
    Table/column names are internal constants (never user input).
    """
    if not rows:
        return 0
    cols = list(types)
    src = ", ".join(f"CAST(:{c} AS {types[c]}) AS {c}" for c in cols)
    on = " AND ".join(f"t.{k} = s.{k}" for k in keys)
    upd = ", ".join(f"t.{c} = s.{c}" for c in cols if c not in keys)
    ins_cols = ", ".join(cols)
    ins_vals = ", ".join(f"s.{c}" for c in cols)
    sql = (
        f"MERGE dbo.{table} AS t USING (SELECT {src}) AS s ON {on} "
        f"WHEN MATCHED THEN UPDATE SET {upd} "
        f"WHEN NOT MATCHED THEN INSERT ({ins_cols}) VALUES ({ins_vals});"
    )
    conn.execute(text(sql), rows)
    return len(rows)
