from fastapi import APIRouter, Query, HTTPException
import pandas as pd
from pathlib import Path

router = APIRouter(prefix="/devices", tags=["Devices"])

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_PATH = BASE_DIR / "data" / "raw" / "devices.csv"

devices_df = pd.read_csv(DATA_PATH)


@router.get("/")
def get_devices(
    status: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0
):
    df = devices_df.copy()

    if status:
        df = df[df["current_status"] == status]

    total = len(df)
    df = df.iloc[offset: offset + limit]

    return {
        "total_records": total,
        "returned_records": len(df),
        "data": df.to_dict(orient="records")
    }


@router.get("/{device_id}")
def get_device(device_id: int):
    device = devices_df[devices_df["device_id"] == device_id]

    if device.empty:
        raise HTTPException(status_code=404, detail="Device not found")

    return device.iloc[0].to_dict()