"""Create deterministic synthetic source data for the BhooMiPredict prototype."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "riskxplain.db"

SCHEMA = """
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS data_quality_exceptions;
DROP TABLE IF EXISTS ulcid_registry;
DROP TABLE IF EXISTS rr_records;
DROP TABLE IF EXISTS pfms_compensation;
DROP TABLE IF EXISTS rccms_cases;
DROP TABLE IF EXISTS la_cases;
DROP TABLE IF EXISTS dilrmp_parcels;
CREATE TABLE dilrmp_parcels (ulpin TEXT PRIMARY KEY, owner_type TEXT, classification TEXT, area_hectares REAL, ingested_at TEXT);
CREATE TABLE la_cases (case_no TEXT PRIMARY KEY, ulpin TEXT, lgd_district TEXT, district_name TEXT, lgd_block TEXT, project_type TEXT, notification_date TEXT, current_stage TEXT, days_in_current_stage INTEGER, affected_families INTEGER, land_area_hectares REAL, historical_delay_days REAL, ingested_at TEXT);
CREATE TABLE rccms_cases (court_case_id TEXT PRIMARY KEY, case_no_ref TEXT, stay_status TEXT, filed_date TEXT, ingested_at TEXT);
CREATE TABLE pfms_compensation (utr TEXT PRIMARY KEY, case_no_ref TEXT, sanctioned_amt REAL, disbursed_amt REAL, disbursed_date TEXT, ingested_at TEXT);
CREATE TABLE rr_records (rr_id TEXT PRIMARY KEY, case_no_ref TEXT, families_total INTEGER, families_resettled INTEGER, grievance_count INTEGER, ingested_at TEXT);
CREATE TABLE ulcid_registry (ulcid TEXT PRIMARY KEY, case_no TEXT, ulpin TEXT, court_case_id TEXT, utr TEXT, rr_id TEXT, match_method TEXT, confidence_score REAL, created_at TEXT);
CREATE TABLE data_quality_exceptions (id INTEGER PRIMARY KEY, source_table TEXT, record_key TEXT, reason_code TEXT, severity TEXT, resolved INTEGER DEFAULT 0);
CREATE TABLE alerts (id INTEGER PRIMARY KEY, ulcid TEXT, alert_type TEXT, message TEXT, status TEXT, created_at TEXT);
CREATE TABLE audit_log (id INTEGER PRIMARY KEY, actor TEXT, action TEXT, ulcid TEXT, created_at TEXT);
"""


def _ulcid(case_no: str) -> str:
    return f"ULC-{hashlib.sha256(case_no.encode()).hexdigest()[:10].upper()}"


def build_seed_data() -> None:
    rng = np.random.default_rng(42)
    districts = [("WB-PB", "Paschim Burdwan", "Kanksa"), ("BR-GY", "Gaya", "Tekari"), ("AP-AN", "Anantapur", "Garladinne"), ("MH-NP", "Nagpur", "Hingna"), ("MP-IN", "Indore", "Depalpur")]
    stages = ["Notification", "Survey", "Declaration", "Award", "Compensation", "Possession", "R&R"]
    project_types = ["Road", "Irrigation", "Rail", "Industrial Corridor"]
    today = date.today()
    cases, parcels, courts, payments, rr_rows, registry = [], [], [], [], [], []

    for index in range(60):
        district_code, district_name, block_name = districts[index % len(districts)]
        case_no = f"LA-{district_code}-{2023 + index % 3}-{index + 1:04d}"
        ulpin = f"{index + 1:014d}"
        stage = stages[index % len(stages)]
        days = int(rng.integers(8, 125))
        affected = int(rng.integers(8, 180))
        area = round(float(rng.uniform(2, 85)), 2)
        stay = index % 9 == 0 or index % 13 == 0
        grievances = int(rng.integers(0, 12 if index % 4 else 28))
        sanctioned = round(float(rng.uniform(1800000, 28000000)), 2)
        ratio = 0 if stage in {"Notification", "Survey"} else float(rng.uniform(0.18, 1.0))
        disbursed = round(sanctioned * ratio, 2)
        notification = today - timedelta(days=int(rng.integers(100, 1000)))
        ingested = today.isoformat()
        cases.append((case_no, ulpin, district_code, district_name, block_name, project_types[index % 4], notification.isoformat(), stage, days, affected, area, round(float(rng.uniform(20, 180)), 1), ingested))
        parcels.append((ulpin, "Individual" if index % 3 else "Government", "Agricultural" if index % 4 else "Residential", area, ingested))
        courts.append((f"RCC-{index + 1:05d}", case_no, "Stay Order" if stay else "No Active Case", (notification + timedelta(days=40)).isoformat(), ingested))
        payments.append((f"UTR-{index + 1:08d}", case_no, sanctioned, disbursed, (today - timedelta(days=int(rng.integers(1, 200)))).isoformat() if disbursed else None, ingested))
        rr_rows.append((f"RR-{index + 1:05d}", case_no, affected, int(affected * rng.uniform(0.05, 0.95)), grievances, ingested))
        registry.append((_ulcid(case_no), case_no, ulpin, f"RCC-{index + 1:05d}", f"UTR-{index + 1:08d}", f"RR-{index + 1:05d}", "fuzzy" if index in {7, 22, 41} else "deterministic", 0.86 if index in {7, 22, 41} else 1.0, today.isoformat()))

    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(SCHEMA)
        tables = {
            "la_cases": (cases, ["case_no", "ulpin", "lgd_district", "district_name", "lgd_block", "project_type", "notification_date", "current_stage", "days_in_current_stage", "affected_families", "land_area_hectares", "historical_delay_days", "ingested_at"]),
            "dilrmp_parcels": (parcels, ["ulpin", "owner_type", "classification", "area_hectares", "ingested_at"]),
            "rccms_cases": (courts, ["court_case_id", "case_no_ref", "stay_status", "filed_date", "ingested_at"]),
            "pfms_compensation": (payments, ["utr", "case_no_ref", "sanctioned_amt", "disbursed_amt", "disbursed_date", "ingested_at"]),
            "rr_records": (rr_rows, ["rr_id", "case_no_ref", "families_total", "families_resettled", "grievance_count", "ingested_at"]),
            "ulcid_registry": (registry, ["ulcid", "case_no", "ulpin", "court_case_id", "utr", "rr_id", "match_method", "confidence_score", "created_at"]),
        }
        for table, (rows, columns) in tables.items():
            pd.DataFrame(rows, columns=columns).to_sql(table, connection, if_exists="append", index=False)
        exceptions = [(1, "ulcid_registry", registry[7][0], "FUZZY_MATCH_REVIEW", "warning", 0), (2, "la_cases", "LA-BR-GY-2024-0023", "MISSING_BLOCK_CODE", "warning", 0), (3, "pfms_compensation", "UTR-00000041", "DISBURSEMENT_MISMATCH", "error", 0)]
        pd.DataFrame(exceptions, columns=["id", "source_table", "record_key", "reason_code", "severity", "resolved"]).to_sql("data_quality_exceptions", connection, if_exists="append", index=False)
        alert_rows = [(idx + 1, row[0], "HIGH_RISK", "High delay probability requires officer review", "unread", today.isoformat()) for idx, row in enumerate(registry[:8])]
        pd.DataFrame(alert_rows, columns=["id", "ulcid", "alert_type", "message", "status", "created_at"]).to_sql("alerts", connection, if_exists="append", index=False)
        audit_rows = [(idx + 1, "seed-script", "INGEST", row[0], today.isoformat()) for idx, row in enumerate(registry[:10])]
        pd.DataFrame(audit_rows, columns=["id", "actor", "action", "ulcid", "created_at"]).to_sql("audit_log", connection, if_exists="append", index=False)
    print(f"Seeded {len(cases)} cases into {DB_PATH}")


if __name__ == "__main__":
    build_seed_data()