"""
AXAMesh - Framework de Data Quality (v2)
========================================
Pattern config-driven : les règles sont dans quality_rules.yaml

Corrections v2 :
  - Sauvegarde dans SQL Server (axamesh) en plus de SQLite
  - TRUNCATE avant chaque run → plus de doublons
  - Un seul run_id par exécution → cohérence avec PowerBI
"""

import os
import pandas as pd
import numpy as np
import yaml
import uuid
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT        = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "quality_rules.yaml"
SILVER_BASE = ROOT / "data" / "silver"
GOLD_BASE   = ROOT / "data" / "gold"

GOLD_BASE.mkdir(parents=True, exist_ok=True)

DB_PATH = GOLD_BASE / "quality_logs.db"

# ── Config SQL Server ──────────────────────────────────────────
SQL_SERVER   = os.getenv("AXAMESH_SQL_SERVER", "AMOUGOU\\SQLEXPRESS")
SQL_DATABASE = os.getenv("AXAMESH_SQL_DATABASE", "axamesh")
SQL_DRIVER   = "ODBC Driver 17 for SQL Server"

with open(CONFIG_PATH) as f:
    RULES = yaml.safe_load(f)


# ============================================================
# CONNEXION SQL SERVER
# ============================================================

def get_sql_engine():
    """Retourne un engine SQLAlchemy vers SQL Server, ou None si indisponible."""
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import URL

        connection_url = URL.create(
            "mssql+pyodbc",
            query={
                "odbc_connect": (
                    f"DRIVER={{{SQL_DRIVER}}};"
                    f"SERVER={SQL_SERVER};"
                    f"DATABASE={SQL_DATABASE};"
                    f"Trusted_Connection=yes;"
                    f"TrustServerCertificate=yes;"
                )
            }
        )
        engine = create_engine(connection_url, fast_executemany=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ SQL Server connecté")
        return engine
    except Exception as e:
        print(f"⚠️  SQL Server indisponible ({e}), SQLite uniquement.")
        return None


# ============================================================
# BASE DE DONNÉES LOGS
# ============================================================

def init_db():
    """Crée la table SQLite si elle n'existe pas."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          TEXT NOT NULL,
            executed_at     TEXT NOT NULL,
            entity          TEXT NOT NULL,
            domain          TEXT NOT NULL,
            check_level     TEXT NOT NULL,
            check_name      TEXT NOT NULL,
            check_category  TEXT NOT NULL,
            description     TEXT,
            rows_total      INTEGER,
            rows_failed     INTEGER,
            failed_pct      REAL,
            status          TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_results(results: list, sql_engine=None):
    """
    Persiste les résultats dans :
      1. SQLite (local, toujours)
      2. SQL Server (si disponible) — TRUNCATE avant insert pour unicité
    """
    df = pd.DataFrame(results)

    # ── SQLite ────────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    # Vider avant d'insérer pour garder uniquement le dernier run
    conn.execute("DELETE FROM data_quality_log")
    df.to_sql("data_quality_log", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    print(f"  💾 SQLite mis à jour : {DB_PATH}")

    # ── SQL Server ────────────────────────────────────────────
    if sql_engine is not None:
        try:
            from sqlalchemy import text
            with sql_engine.begin() as conn:
                # TRUNCATE pour éviter les doublons → PowerBI et Copilot
                # lisent toujours exactement 60 lignes (dernier run)
                conn.execute(text("TRUNCATE TABLE gold.data_quality_log"))
                df.to_sql(
                    "data_quality_log",
                    con=conn,
                    schema="gold",
                    if_exists="append",
                    index=False,
                    method="multi",
                )
            print(f"  💾 SQL Server mis à jour : {len(df)} lignes dans gold.data_quality_log")
        except Exception as e:
            print(f"  ⚠️  Erreur SQL Server lors de la sauvegarde : {e}")


# ============================================================
# MOTEUR D'EXÉCUTION
# ============================================================

def run_check(
    df: pd.DataFrame,
    rule: dict,
    run_id: str,
    entity: str,
    domain: str,
    level: str,
    extra_params: dict = None,
) -> dict:
    check_name      = rule["name"]
    description     = rule.get("description", "")
    warn_threshold  = rule.get("warn_threshold", 0.0)
    fail_threshold  = rule.get("fail_threshold", 0.05)
    rows_total      = len(df)

    try:
        rows_failed = _execute_rule(df, rule, extra_params or {})
        failed_pct  = rows_failed / rows_total if rows_total > 0 else 0.0

        if failed_pct > fail_threshold:
            status = "FAIL"
        elif failed_pct > warn_threshold:
            status = "WARN"
        else:
            status = "PASS"

    except Exception as e:
        rows_failed = -1
        failed_pct  = -1.0
        status      = "ERROR"
        description = f"ERREUR: {str(e)}"

    emoji = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌", "ERROR": "💥"}[status]
    print(f"    {emoji} [{status}] {check_name:<45} | "
          f"failed: {rows_failed:>5} / {rows_total:>6} "
          f"({failed_pct*100:.2f}%)")

    return {
        "run_id":         run_id,
        "executed_at":    datetime.now(timezone.utc).isoformat(),
        "entity":         entity,
        "domain":         domain,
        "check_level":    level,
        "check_name":     check_name,
        "check_category": rule.get("category", "Unknown"),
        "description":    description,
        "rows_total":     rows_total,
        "rows_failed":    int(rows_failed) if rows_failed >= 0 else -1,
        "failed_pct":     round(failed_pct * 100, 4) if failed_pct >= 0 else -1,
        "status":         status,
    }


def _execute_rule(df: pd.DataFrame, rule: dict, params: dict) -> int:
    name = rule["name"]

    # ---- CUSTOMER ----
    if name == "customer_completeness_id":
        return df["customer_id"].isna().sum()
    elif name == "customer_completeness_email":
        return df["email"].isna().sum()
    elif name == "customer_uniqueness_id":
        return df.duplicated(subset=["customer_id"], keep=False).sum() // 2
    elif name == "customer_freshness":
        max_date = pd.to_datetime(df["_ingested_at"]).max()
        delta = (datetime.now(timezone.utc) -
                 max_date.to_pydatetime().replace(tzinfo=timezone.utc)).days
        return 1 if delta > 7 else 0
    elif name == "customer_email_format":
        mask = df["email"].notna() & ~df["email"].str.contains("@", na=False)
        return mask.sum()
    elif name == "customer_dob_range":
        from datetime import date
        today = date.today()
        dob = pd.to_datetime(df["date_of_birth"], errors="coerce").dt.date
        return ((dob < date(1900, 1, 1)) | (dob > today)).sum()
    elif name == "customer_kyc_expired":
        return (df["kyc_status"] == "EXPIRED").sum()
    elif name == "customer_country_coherence":
        expected = params.get("expected_country", "")
        return (df["country"] != expected).sum()

    # ---- CLAIMS ----
    elif name == "claims_completeness_id":
        return df["claim_id"].isna().sum()
    elif name == "claims_uniqueness_id":
        return df.dropna(subset=["claim_id"]).duplicated(
            subset=["claim_id"], keep=False).sum() // 2
    elif name == "claims_date_coherence":
        decl = pd.to_datetime(df["declaration_date"], errors="coerce")
        inc  = pd.to_datetime(df["incident_date"],    errors="coerce")
        return (decl < inc).sum()
    elif name == "claims_amount_positive":
        return (df["claim_amount"] <= 0).sum()
    elif name == "claims_amount_extreme":
        return (df["claim_amount_eur"] > 500_000).sum()
    elif name == "claims_status_valid":
        valid = {"OPEN", "IN_REVIEW", "CLOSED", "REJECTED", "PAID"}
        return (~df["status"].isin(valid)).sum()

    # ---- POLICIES ----
    elif name == "policies_completeness_id":
        return df["policy_id"].isna().sum()
    elif name == "policies_uniqueness_id":
        return df.dropna(subset=["policy_id"]).duplicated(
            subset=["policy_id"], keep=False).sum() // 2
    elif name == "policies_premium_positive":
        return (df["annual_premium"] <= 0).sum()
    elif name == "policies_date_coherence":
        end   = pd.to_datetime(df["end_date"],   errors="coerce")
        start = pd.to_datetime(df["start_date"], errors="coerce")
        return (end <= start).sum()
    elif name == "policies_product_type_valid":
        valid = {"AUTO", "HOME", "HEALTH", "LIFE", "TRAVEL", "LIABILITY"}
        return (~df["product_type"].isin(valid)).sum()
    elif name == "policies_active_customer":
        return df["customer_id"].isna().sum()
    else:
        raise ValueError(f"Règle inconnue : {name}")


# ============================================================
# RUNNER PRINCIPAL
# ============================================================

DOMAIN_MAP = {
    "customer": "customer",
    "claims":   "claims",
    "policies": "policies",
}

ENTITY_COUNTRIES = {
    "axa_france": "France",
    "axa_uk":     "United Kingdom",
    "axa_italy":  "Italy",
}


def run_entity_domain(entity_id, domain, run_id):
    path = SILVER_BASE / entity_id / f"{domain}.parquet"
    if not path.exists():
        print(f"  ⚠️  Fichier manquant : {path}")
        return []

    df = pd.read_parquet(path)
    rules_config = RULES.get(DOMAIN_MAP[domain], {})
    results = []

    extra_params = {}
    if domain == "customer":
        extra_params["expected_country"] = ENTITY_COUNTRIES.get(entity_id, "")

    for rule in rules_config.get("group_mandatory", []):
        results.append(run_check(df, rule, run_id, entity_id, domain,
                                 "group_mandatory", extra_params))
    for rule in rules_config.get("domain_specific", []):
        results.append(run_check(df, rule, run_id, entity_id, domain,
                                 "domain_specific", extra_params))
    return results


def main():
    print("=" * 70)
    print("AXAMesh — Framework Data Quality v2")
    print("=" * 70)

    init_db()
    sql_engine = get_sql_engine()

    run_id      = str(uuid.uuid4())[:8].upper()
    all_results = []

    entities = ["axa_france", "axa_uk", "axa_italy"]
    domains  = ["customer", "claims", "policies"]

    for entity_id in entities:
        print(f"\n🏢 {entity_id.replace('_', ' ').title()}")
        print("-" * 50)
        for domain in domains:
            print(f"\n  📂 {domain.upper()}")
            results = run_entity_domain(entity_id, domain, run_id)
            all_results.extend(results)

    # ── Sauvegarde (SQLite + SQL Server) ──────────────────────
    print(f"\n{'=' * 70}")
    print("💾 Sauvegarde des résultats...")
    save_results(all_results, sql_engine)

    # ── Export CSV pour PowerBI (fallback) ────────────────────
    df_results = pd.DataFrame(all_results)
    csv_path   = GOLD_BASE / "quality_report.csv"
    df_results.to_csv(csv_path, index=False)
    print(f"  💾 CSV exporté : {csv_path}")

    # ── Résumé global ─────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"📊 RUN ID : {run_id}  |  {len(all_results)} contrôles exécutés")
    print(f"{'=' * 70}")

    summary = df_results.groupby(["entity", "domain", "status"]).size().unstack(
        fill_value=0)
    print(f"\n{summary.to_string()}")

    nb_pass = (df_results["status"] == "PASS").sum()
    nb_warn = (df_results["status"] == "WARN").sum()
    nb_fail = (df_results["status"] == "FAIL").sum()
    total   = len(df_results)

    print(f"\n  ✅ PASS : {nb_pass}/{total}")
    print(f"  ⚠️  WARN : {nb_warn}/{total}")
    print(f"  ❌ FAIL : {nb_fail}/{total}")
    print(f"  📈 Pass Rate : {round(100*nb_pass/total, 1)}%")

    if nb_fail > 0:
        print(f"\n🚨 Statut global : FAIL")
    elif nb_warn > 0:
        print(f"\n⚠️  Statut global : WARN")
    else:
        print(f"\n🎉 Statut global : PASS")

    print(f"\n{'=' * 70}")
    print("✅ PowerBI et Copilot liront exactement les mêmes données.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()