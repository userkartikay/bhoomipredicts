from __future__ import annotations

import sqlite3
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from seed_data import DB_PATH, build_seed_data

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "risk_model.pkl"
app = FastAPI(title="BhooMiPredict Land Case API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATASETS = {
    "land records": "dilrmp_parcels",
    "acquisition cases": "la_cases",
    "court records": "rccms_cases",
    "payment records": "pfms_compensation",
    "rehabilitation records": "rr_records",
    "joined case view": "joined",
}


def connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        build_seed_data()
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def model_bundle() -> dict:
    if not MODEL_PATH.exists():
        from train_model import train
        train()
    return joblib.load(MODEL_PATH)


def case_frame(db: sqlite3.Connection, ulcid: str | None = None) -> pd.DataFrame:
    query = """SELECT u.ulcid, u.match_method, u.confidence_score, l.*, r.stay_status,
                     p.sanctioned_amt, p.disbursed_amt, rr.families_resettled, rr.grievance_count,
                     d.owner_type, d.classification
              FROM ulcid_registry u JOIN la_cases l ON u.case_no=l.case_no
              JOIN rccms_cases r ON l.case_no=r.case_no_ref
              JOIN pfms_compensation p ON l.case_no=p.case_no_ref
              JOIN rr_records rr ON l.case_no=rr.case_no_ref
              JOIN dilrmp_parcels d ON l.ulpin=d.ulpin"""
    params = ()
    if ulcid:
        query += " WHERE u.ulcid = ?"
        params = (ulcid,)
    data = pd.read_sql_query(query, db, params=params)
    if data.empty:
        return data
    data["compensation_ratio"] = data["disbursed_amt"] / data["sanctioned_amt"].clip(lower=1)
    data["rr_progress"] = data["families_resettled"] / data["affected_families"].clip(lower=1)
    return data


@app.get("/datasets")
def datasets() -> list[dict]:
    with connection() as db:
        result = []
        for label, table in DATASETS.items():
            count = len(case_frame(db)) if table == "joined" else db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            result.append({"key": label, "table": table, "records": int(count)})
        return result


@app.get("/datasets/{dataset_key}")
def dataset_rows(dataset_key: str) -> dict:
    if dataset_key not in DATASETS:
        raise HTTPException(status_code=404, detail="Dataset not found")
    with connection() as db:
        data = case_frame(db) if DATASETS[dataset_key] == "joined" else pd.read_sql_query(f"SELECT * FROM {DATASETS[dataset_key]}", db)
    return {"name": dataset_key, "records": int(len(data)), "columns": list(data.columns), "rows": data.to_dict(orient="records")}


def prediction(row: pd.Series) -> dict:
    bundle = model_bundle()
    features = bundle["features"]
    values = row[features].to_frame().T
    probability = float(bundle["pipeline"].predict_proba(values)[0][1])
    hard_flag = row["stay_status"] == "Stay Order"
    grievance_flag = int(row["grievance_count"]) >= 10
    risk_score = min(1.0, probability * 0.7 + hard_flag * 0.2 + grievance_flag * 0.1)
    tier = "High" if hard_flag or risk_score >= 0.66 else "Medium" if risk_score >= 0.36 else "Low"
    drivers = []
    if hard_flag:
        drivers.append({"feature": "Active stay order", "impact": 0.20, "direction": "increases"})
    if row["days_in_current_stage"] > 70:
        drivers.append({"feature": "Days in current stage", "impact": 0.12, "direction": "increases"})
    if row["compensation_ratio"] < 0.5:
        drivers.append({"feature": "Compensation pending", "impact": 0.10, "direction": "increases"})
    if row["rr_progress"] < 0.5:
        drivers.append({"feature": "Low R&R progress", "impact": 0.08, "direction": "increases"})
    if grievance_flag:
        drivers.append({"feature": "Grievance backlog", "impact": 0.10, "direction": "increases"})
    if not drivers:
        drivers.append({"feature": "Historical district performance", "impact": 0.04, "direction": "increases"})
    recommendation = "Legal cell review and stay-order escalation" if hard_flag else "Verify PFMS release queue" if row["compensation_ratio"] < 0.5 else "R&R officer intervention" if row["rr_progress"] < 0.5 else "Schedule next stage review"
    return {"delay_probability": round(probability, 3), "risk_score": round(risk_score, 3), "risk_tier": tier, "drivers": drivers[:5], "recommendation": recommendation}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "database": DB_PATH.name, "model": MODEL_PATH.name}


@app.get("/overview")
def overview() -> dict:
    with connection() as db:
        data = case_frame(db)
    predictions = [prediction(row) for _, row in data.iterrows()]
    tiers = pd.Series([item["risk_tier"] for item in predictions]).value_counts().to_dict()
    district_risk = []
    for district, group in data.groupby("district_name"):
        district_risk.append({"district": district, "cases": len(group), "avg_probability": round(sum(prediction(row)["delay_probability"] for _, row in group.iterrows()) / len(group), 3)})
    return {"total_cases": len(data), "high_risk": tiers.get("High", 0), "medium_risk": tiers.get("Medium", 0), "low_risk": tiers.get("Low", 0), "fuzzy_matches": int((data["match_method"] == "fuzzy").sum()), "districts": district_risk}


@app.get("/risk-queue")
def risk_queue(district: str = "", tier: str = "") -> list[dict]:
    with connection() as db:
        data = case_frame(db)
    rows = []
    for _, row in data.iterrows():
        result = prediction(row)
        if district and row["district_name"] != district or tier and result["risk_tier"] != tier:
            continue
        rows.append({"ulcid": row["ulcid"], "case_no": row["case_no"], "district": row["district_name"], "stage": row["current_stage"], "risk_tier": result["risk_tier"], "risk_score": result["risk_score"], "delay_probability": result["delay_probability"], "stay_status": row["stay_status"]})
    return sorted(rows, key=lambda item: item["risk_score"], reverse=True)


@app.get("/cases/{ulcid}")
def get_case(ulcid: str) -> dict:
    with connection() as db:
        data = case_frame(db, ulcid)
    if data.empty:
        raise HTTPException(status_code=404, detail="ULCID not found")
    row = data.iloc[0]
    result = prediction(row)
    return {
        "identity": {"ulcid": str(row["ulcid"]), "case_no": str(row["case_no"]), "match_method": str(row["match_method"]), "confidence": float(row["confidence_score"])},
        "land": {"ulpin": str(row["ulpin"]), "owner_type": str(row["owner_type"]), "classification": str(row["classification"]), "area_hectares": float(row["land_area_hectares"])},
        "acquisition": {"district": str(row["district_name"]), "block": str(row["lgd_block"]), "project_type": str(row["project_type"]), "stage": str(row["current_stage"]), "days_in_stage": int(row["days_in_current_stage"]), "affected_families": int(row["affected_families"])},
        "legal": {"stay_status": str(row["stay_status"])},
        "compensation": {"sanctioned": float(row["sanctioned_amt"]), "disbursed": float(row["disbursed_amt"]), "ratio": float(round(row["compensation_ratio"], 3))},
        "rehabilitation": {"families_resettled": int(row["families_resettled"]), "progress": float(round(row["rr_progress"], 3)), "grievances": int(row["grievance_count"])},
        "prediction": result,
    }


@app.get("/cases/{ulcid}/prediction")
def get_prediction(ulcid: str) -> dict:
    case = get_case(ulcid)
    return case["prediction"]


@app.get("/alerts")
def alerts(status: str = "unread") -> list[dict]:
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM alerts WHERE status = ? ORDER BY id DESC", (status,)).fetchall()]


@app.get("/data-quality")
def data_quality() -> list[dict]:
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM data_quality_exceptions WHERE resolved = 0 ORDER BY severity DESC, id").fetchall()]


@app.get("/api/v1/projects/{package_id}")
def legacy_package(package_id: str) -> dict:
    with connection() as db:
        row = db.execute("SELECT ulcid, case_no, district_name, current_stage FROM ulcid_registry JOIN la_cases USING(case_no) WHERE case_no = ?", (package_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Package compatibility route expects a case number")
    return {"uiid": row["ulcid"], "package_id": package_id, "administrative": {"district": row["district_name"]}, "analytics": {"current_stage": row["current_stage"]}, "message": "Use /cases/{ulcid} for the RiskXplain Case 360 response."}