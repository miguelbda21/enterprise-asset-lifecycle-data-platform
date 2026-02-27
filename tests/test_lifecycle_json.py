# tests/test_lifecycle_json.py
import json
import numpy as np
import pandas as pd

from src.api.routes import lifecycle


def test_df_to_json_records_handles_inf_and_nan():
    df = pd.DataFrame({
        "device_id": [1, 2, 3],
        "value": [np.inf, np.nan, -np.inf],
        "name": ["a", "b", "c"]
    })

    records = lifecycle._df_to_json_records(df)
    # Should be a list of dicts
    assert isinstance(records, list)
    assert len(records) == 3

    # None should appear for problematic float values
    assert records[0]["value"] is None
    assert records[1]["value"] is None
    assert records[2]["value"] is None

    # JSON-serializable
    json_str = json.dumps(records)
    assert isinstance(json_str, str)