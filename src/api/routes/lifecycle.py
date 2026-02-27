# src/api/routes/lifecycle.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/lifecycle-events", tags=["Lifecycle"])

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_PATH = BASE_DIR / "data" / "raw" / "lifecycle_events.csv"

# -----------------------------
# Lazy cache (loaded on first request)
# -----------------------------
_LIFECYCLE_DF: Optional[pd.DataFrame] = None
_LIFECYCLE_MTIME: Optional[float] = None


def _load_lifecycle_df(force_reload: bool = False) -> pd.DataFrame:
    """
    Load lifecycle_events.csv lazily and cache it.
    If file changes (mtime changes), reload automatically.
    """
    global _LIFECYCLE_DF, _LIFECYCLE_MTIME

    if not DATA_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Lifecycle CSV not found: {DATA_PATH}",
        )

    current_mtime = DATA_PATH.stat().st_mtime

    if force_reload or _LIFECYCLE_DF is None or _LIFECYCLE_MTIME != current_mtime:
        df = pd.read_csv(str(DATA_PATH))

        # Optional safety: ensure device_id is numeric if it came as string
        if "device_id" in df.columns:
            df["device_id"] = pd.to_numeric(df["device_id"], errors="coerce")

        _LIFECYCLE_DF = df
        _LIFECYCLE_MTIME = current_mtime

    return _LIFECYCLE_DF


def _df_to_json_records(df: pd.DataFrame) -> list[dict]:
    """
    Convert a DataFrame to JSON-safe records:
    - Replace +/-inf with NaN
    - Convert NaN to None (so FastAPI/JSON can serialize it)
    """
    cleaned = df.replace([np.inf, -np.inf], np.nan)
    cleaned = cleaned.astype(object).where(pd.notna(cleaned), None)
    return cleaned.to_dict(orient="records")


@router.get("/")
def get_lifecycle_events(
    device_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    reload: bool = Query(False, description="Force reload lifecycle CSV from disk"),
):
    df = _load_lifecycle_df(force_reload=reload)

    if device_id is not None:
        # handle NaN device_id values safely
        df = df[df["device_id"] == device_id]

    total = int(len(df))
    page = df.iloc[offset: offset + limit]

    return {
        "total_records": total,
        "returned_records": int(len(page)),
        "data": _df_to_json_records(page),
    }