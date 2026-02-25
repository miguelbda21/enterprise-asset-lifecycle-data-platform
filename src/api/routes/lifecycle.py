from fastapi import APIRouter, Query
import pandas as pd
from pathlib import Path

router = APIRouter(prefix="/lifecycle-events", tags=["Lifecycle"])

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_PATH = BASE_DIR / "data" / "raw" / "lifecycle_events.csv"

lifecycle_df = pd.read_csv(DATA_PATH)


@router.get("/")
def get_lifecycle_events(
    device_id: int | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0
):
    df = lifecycle_df.copy()

    if device_id:
        df = df[df["device_id"] == device_id]

    total = len(df)
    df = df.iloc[offset: offset + limit]

    return {
        "total_records": total,
        "returned_records": len(df),
        "data": df.to_dict(orient="records")
    }