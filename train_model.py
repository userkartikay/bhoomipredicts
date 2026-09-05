import sqlite3
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from seed_data import DB_PATH, build_seed_data

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "risk_model.pkl"
FEATURES = ["project_type", "current_stage", "days_in_current_stage", "affected_families", "land_area_hectares", "historical_delay_days", "stay_status", "compensation_ratio", "rr_progress", "grievance_count"]


def load_training_data() -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as connection:
        data = pd.read_sql_query("""SELECT l.*, r.stay_status, p.sanctioned_amt, p.disbursed_amt, rr.families_resettled, rr.grievance_count FROM la_cases l JOIN rccms_cases r ON l.case_no = r.case_no_ref JOIN pfms_compensation p ON l.case_no = p.case_no_ref JOIN rr_records rr ON l.case_no = rr.case_no_ref""", connection)
    data["compensation_ratio"] = data["disbursed_amt"] / data["sanctioned_amt"].clip(lower=1)
    data["rr_progress"] = data["families_resettled"] / data["affected_families"].clip(lower=1)
    noise = np.random.default_rng(42).normal(0, 8, len(data))
    data["delay_days"] = (data["days_in_current_stage"] * 1.2 + data["historical_delay_days"] * 0.35 + (data["stay_status"] == "Stay Order") * 90 + data["grievance_count"] * 4 + (1 - data["compensation_ratio"]) * 65 + noise).clip(0)
    data["delayed"] = (data["delay_days"] > 100).astype(int)
    return data


def train() -> None:
    if not DB_PATH.exists():
        build_seed_data()
    data = load_training_data()
    categorical = ["project_type", "current_stage", "stay_status"]
    numerical = [feature for feature in FEATURES if feature not in categorical]
    preprocessor = ColumnTransformer(transformers=[
        ("num", StandardScaler(), numerical),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical)
    ])
    model_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", xgb.XGBClassifier(n_estimators=120, max_depth=3, learning_rate=0.08, random_state=42, eval_metric="logloss"))
    ])

    model_pipeline.fit(data[FEATURES], data["delayed"])
    joblib.dump({"pipeline": model_pipeline, "features": FEATURES, "training_rows": len(data)}, MODEL_PATH)
    print(f"Trained stage-aware XGBoost classifier on {len(data)} cases -> {MODEL_PATH}")


if __name__ == "__main__":
    train()