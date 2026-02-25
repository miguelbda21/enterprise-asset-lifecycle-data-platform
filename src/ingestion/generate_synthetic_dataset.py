# src/ingestion/generate_synthetic_dataset.py
"""
Enterprise Asset Lifecycle (Synthetic) Dataset Generator
--------------------------------------------------------

Generates a realistic, portfolio-safe dataset that simulates an enterprise CMDB / ITAM lifecycle:

- Reference tables: models, departments, locations, users
- Core entity: devices
- Operational table: incidents
- Lifecycle history: lifecycle_events (Active → In Repair → Active → Retired, etc.)

Outputs CSVs to: data/raw/

Run:
  python -m src.ingestion.generate_synthetic_dataset
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Tuple, Optional, Dict

import numpy as np
import pandas as pd
from faker import Faker


# -----------------------------
# Configuration
# -----------------------------
@dataclass(frozen=True)
class Config:
    num_devices: int = 10_000
    num_users: int = 500
    num_incidents: int = 5_000
    years_history_assets: int = 5
    years_history_incidents: int = 3
    seed: int = 42

    # Lifecycle behavior
    p_never_repair: float = 0.55  # devices that never enter "In Repair"
    p_one_repair: float = 0.30  # devices with exactly one repair cycle
    p_two_repairs: float = 0.12  # devices with two repair cycles
    p_three_repairs: float = 0.03  # devices with three repair cycles

    p_retired_by_age: float = 0.18  # probability device is retired by end of history window
    min_repair_days: int = 2
    max_repair_days: int = 21

    # Warranty distribution (years)
    warranty_years_choices: Tuple[int, ...] = (2, 3, 4)

    # Status choices (current)
    status_active: str = "Active"
    status_in_repair: str = "In Repair"
    status_retired: str = "Retired"


# -----------------------------
# Helpers
# -----------------------------
def _base_dir() -> Path:
    # src/ingestion/ -> repo root
    return Path(__file__).resolve().parents[2]


def _raw_dir() -> Path:
    d = _base_dir() / "data" / "raw"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _random_date(fake: Faker, start_days_ago: int, end_days_ago: int = 0) -> date:
    """Return a random date between (today - start_days_ago) and (today - end_days_ago)."""
    start = date.today() - timedelta(days=start_days_ago)
    end = date.today() - timedelta(days=end_days_ago)
    return fake.date_between(start_date=start, end_date=end)


def _clamp(d: date, lo: date, hi: date) -> date:
    return max(lo, min(hi, d))


def _pick_repair_count(cfg: Config, rng: np.random.Generator) -> int:
    probs = [cfg.p_never_repair, cfg.p_one_repair, cfg.p_two_repairs, cfg.p_three_repairs]
    probs = np.array(probs, dtype=float)
    probs = probs / probs.sum()
    return int(rng.choice([0, 1, 2, 3], p=probs))


# -----------------------------
# Generator
# -----------------------------
def generate_dataset(cfg: Config) -> Dict[str, pd.DataFrame]:
    fake = Faker()
    fake.seed_instance(cfg.seed)
    rng = np.random.default_rng(cfg.seed)

    # -----------------------------
    # Reference: Models
    # -----------------------------
    models = [
        {"model_id": 1, "model_name": "Dell Latitude 7420", "category": "Laptop"},
        {"model_id": 2, "model_name": "HP EliteBook 840", "category": "Laptop"},
        {"model_id": 3, "model_name": "Lenovo ThinkPad X1", "category": "Laptop"},
        {"model_id": 4, "model_name": "Apple iPhone 14", "category": "Mobile"},
        {"model_id": 5, "model_name": "Cisco Catalyst 9300", "category": "Network"},
        {"model_id": 6, "model_name": "Dell OptiPlex 7090", "category": "Desktop"},
        {"model_id": 7, "model_name": "Apple MacBook Pro 14", "category": "Laptop"},
        {"model_id": 8, "model_name": "Microsoft Surface Pro 9", "category": "Laptop"},
    ]
    models_df = pd.DataFrame(models)

    # -----------------------------
    # Reference: Departments
    # -----------------------------
    departments = [
        "Finance",
        "HR",
        "IT",
        "Security",
        "Operations",
        "Clinical",
        "Supply Chain",
        "Facilities",
    ]
    dept_df = pd.DataFrame(
        {"department_id": range(1, len(departments) + 1), "department_name": departments}
    )

    # -----------------------------
    # Reference: Locations
    # -----------------------------
    locations = [
        ("Arlington, TX", "Central"),
        ("Dallas, TX", "North"),
        ("Fort Worth, TX", "West"),
        ("Irving, TX", "North"),
        ("Plano, TX", "North"),
        ("Houston, TX", "South"),
        ("Austin, TX", "South"),
        ("San Antonio, TX", "South"),
    ]
    loc_df = pd.DataFrame(
        [{"location_id": i + 1, "location_name": nm, "region": rg} for i, (nm, rg) in enumerate(locations)]
    )

    # -----------------------------
    # Reference: Users
    # -----------------------------
    users = []
    for i in range(1, cfg.num_users + 1):
        users.append(
            {
                "user_id": i,
                "full_name": fake.name(),
                "email": fake.email(),
                "department_id": int(rng.integers(1, len(departments) + 1)),
                "location_id": int(rng.integers(1, len(locations) + 1)),
                "job_title": fake.job(),
            }
        )
    users_df = pd.DataFrame(users)

    # -----------------------------
    # Core: Devices + Lifecycle Events
    # -----------------------------
    devices = []
    lifecycle_events = []

    today = date.today()
    history_start = today - timedelta(days=365 * cfg.years_history_assets)

    # local event type strings (lowercase local names avoid linter uppercase-in-function)
    evt_install = "Installed"
    evt_repair_open = "Repair Opened"
    evt_repair_close = "Repair Closed"
    evt_retire = "Retired"

    def add_event(dev_id: int, evt_date: date, evt_type: str, from_status: Optional[str], to_status: Optional[str], notes: str):
        lifecycle_events.append(
            {
                "event_id": None,  # filled later
                "device_id": dev_id,
                "event_date": evt_date.isoformat(),
                "event_type": evt_type,
                "from_status": from_status,
                "to_status": to_status,
                "notes": notes,
            }
        )

    for device_id in range(1, cfg.num_devices + 1):
        install_date = fake.date_between(start_date=history_start, end_date=today)
        warranty_years = int(rng.choice(cfg.warranty_years_choices))
        warranty_exp = install_date + timedelta(days=365 * warranty_years)

        model_id = int(rng.integers(1, len(models) + 1))
        assigned_user_id = int(rng.integers(1, cfg.num_users + 1))

        asset_tag = f"AST-{device_id:06d}"
        serial_number = fake.unique.bothify(text="SN-##########")

        purchase_price = float(np.round(rng.uniform(700, 5200), 2))
        purchase_date = _clamp(install_date - timedelta(days=int(rng.integers(1, 90))), history_start, today)

        # Start in Active after installation
        current_status = cfg.status_active
        add_event(device_id, install_date, evt_install, None, cfg.status_active, "Device installed and activated")

        # Decide how many repair cycles occur
        repair_cycles = _pick_repair_count(cfg, rng)

        # Create timeline points
        cursor_date = install_date

        # Generate repair cycles
        for cycle_idx in range(repair_cycles):
            # Choose a future date for repair open (some time after cursor)
            open_offset_days = int(rng.integers(30, 420))  # 1–14 months-ish
            repair_open = cursor_date + timedelta(days=open_offset_days)
            if repair_open > today:
                break

            # Status change to In Repair
            add_event(device_id, repair_open, evt_repair_open, current_status, cfg.status_in_repair, f"Repair cycle {cycle_idx + 1} opened")
            current_status = cfg.status_in_repair

            # Repair duration
            duration_days = int(rng.integers(cfg.min_repair_days, cfg.max_repair_days + 1))
            repair_close = repair_open + timedelta(days=duration_days)
            if repair_close > today:
                # If repair would end in the future, keep it open -> current status stays In Repair
                cursor_date = repair_open
                break

            # Status change back to Active
            add_event(device_id, repair_close, evt_repair_close, current_status, cfg.status_active, f"Repair cycle {cycle_idx + 1} closed")
            current_status = cfg.status_active
            cursor_date = repair_close

        # Optionally retire the device (based on age / probability)
        age_years = (today - install_date).days / 365.0
        # Higher chance to retire when older
        retire_prob = cfg.p_retired_by_age + min(0.35, max(0.0, (age_years - 3.0) * 0.12))
        if rng.random() < retire_prob:
            # retire date after last cursor and before today
            retire_after_days = int(rng.integers(60, 420))
            retire_date = cursor_date + timedelta(days=retire_after_days)
            if retire_date <= today:
                add_event(device_id, retire_date, evt_retire, current_status, cfg.status_retired, "Device retired / decommissioned")
                current_status = cfg.status_retired

        devices.append(
            {
                "device_id": device_id,
                "asset_tag": asset_tag,
                "serial_number": serial_number,
                "model_id": model_id,
                "assigned_user_id": assigned_user_id,
                "purchase_date": purchase_date.isoformat(),
                "install_date": install_date.isoformat(),
                "warranty_expiration": warranty_exp.isoformat(),
                "purchase_price": purchase_price,
                "current_status": current_status,
            }
        )

    devices_df = pd.DataFrame(devices)
    lifecycle_df = pd.DataFrame(lifecycle_events)

    # Fill event_id and sort events
    lifecycle_df["event_date"] = pd.to_datetime(lifecycle_df["event_date"], errors="coerce")
    lifecycle_df = lifecycle_df.sort_values(["device_id", "event_date", "event_type"]).reset_index(drop=True)
    lifecycle_df["event_id"] = range(1, len(lifecycle_df) + 1)
    # optional: move it to the first column
    cols = ["event_id"] + [c for c in lifecycle_df.columns if c != "event_id"]
    lifecycle_df = lifecycle_df[cols]
    lifecycle_df["event_date"] = lifecycle_df["event_date"].dt.date.astype(str)

    # -----------------------------
    # Operational: Incidents
    # -----------------------------
    # Distribute incidents preferentially to devices with repair events
    device_has_repairs = (
        lifecycle_df[lifecycle_df["event_type"].isin([evt_repair_open, evt_repair_close])]
        .groupby("device_id")
        .size()
        .reindex(range(1, cfg.num_devices + 1), fill_value=0)
    )

    # Weight devices: base weight + extra if repairs occurred
    weights = 1.0 + (device_has_repairs.values * 0.8)
    weights = weights / weights.sum()

    incident_rows = []
    inc_start = today - timedelta(days=365 * cfg.years_history_incidents)
    priorities = ["Low", "Medium", "High", "Critical"]
    categories = ["Hardware", "Software", "Network", "Security", "Access", "Other"]

    for inc_id in range(1, cfg.num_incidents + 1):
        inc_device_id = int(rng.choice(np.arange(1, cfg.num_devices + 1), p=weights))
        opened = fake.date_between(start_date=inc_start, end_date=today)
        short_desc = fake.sentence(nb_words=8)
        work_notes = " ".join(fake.sentences(nb=3))

        # use rng.choice with explicit probabilities (convert lists -> numpy for rng.choice)
        priority = str(rng.choice(np.array(priorities), p=np.array([0.45, 0.35, 0.15, 0.05])))
        category = str(rng.choice(np.array(categories), p=np.array([0.25, 0.30, 0.15, 0.10, 0.10, 0.10])))
        status = str(rng.choice(np.array(["Open", "In Progress", "Resolved", "Closed"]), p=np.array([0.15, 0.25, 0.35, 0.25])))

        incident_rows.append(
            {
                "incident_id": inc_id,
                "device_id": inc_device_id,
                "opened_date": opened.isoformat(),
                "priority": priority,
                "category": category,
                "short_description": short_desc,
                "work_notes": work_notes,
                "status": status,
            }
        )

    incidents_df = pd.DataFrame(incident_rows)

    return {
        "models": models_df,
        "departments": dept_df,
        "locations": loc_df,
        "users": users_df,
        "devices": devices_df,
        "lifecycle_events": lifecycle_df,
        "incidents": incidents_df,
    }


def save_to_raw(dfs: Dict[str, pd.DataFrame]) -> None:
    out = _raw_dir()
    for name, df in dfs.items():
        df.to_csv(out / f"{name}.csv", index=False)
    print(f"✅ Synthetic dataset generated: {len(dfs)} files written to {out}")


def main() -> None:
    cfg = Config()
    dfs = generate_dataset(cfg)
    save_to_raw(dfs)

    # Tiny sanity printout
    print(f"Devices: {len(dfs['devices']):,}")
    print(f"Lifecycle events: {len(dfs['lifecycle_events']):,}")
    print(f"Incidents: {len(dfs['incidents']):,}")


if __name__ == "__main__":
    main()