"""
AXAMesh - Chargement des données vers SQL Server
Bronze (CSV) + Silver (Parquet) + Quality Logs → SQL Server axamesh
"""

import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text
import yaml
from pathlib import Path
from datetime import datetime

ROOT        = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "entities.yaml"
BRONZE_BASE = ROOT / "data" / "bronze"
SILVER_BASE = ROOT / "data" / "silver"
GOLD_BASE   = ROOT / "data" / "gold"

with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

# ============================================================
# CONNEXION SQL SERVER
# ============================================================

SERVER   = "AMOUGOU\\SQLEXPRESS"
DATABASE = "axamesh"
DRIVER   = "ODBC Driver 17 for SQL Server"

def get_engine():
    conn_str = (
        f"mssql+pyodbc://@{SERVER}/{DATABASE}"
        f"?driver={DRIVER.replace(' ', '+')}"
        f"&trusted_connection=yes"
        f"&TrustServerCertificate=yes"
    )
    return create_engine(conn_str, fast_executemany=True)


def test_connection(engine):
    """Vérifie que la connexion fonctionne."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT @@VERSION")).fetchone()
        print(f"  ✅ Connecté à : {result[0][:50]}...")


# ============================================================
# CHARGEMENT BRONZE
# ============================================================

def load_bronze(engine):
    """Charge les CSV Bronze dans SQL Server."""
    print("\n🥉 Chargement BRONZE → SQL Server")
    print("-" * 50)

    domains = ["customer", "claims", "policies"]

    for entity_id in CONFIG["entities"]:
        schema = f"bronze_{entity_id}"
        for domain in domains:
            path = BRONZE_BASE / entity_id / f"{domain}.csv"
            if not path.exists():
                print(f"  ⚠️  Manquant : {path.name}")
                continue

            df = pd.read_csv(path)

            # Nettoyage types pour SQL Server
            df = _clean_for_sqlserver(df)

            df.to_sql(
                name=domain,
                con=engine,
                schema=schema,
                if_exists="replace",
                index=False,
                chunksize=500,
            )
            print(f"  ✅ {schema}.{domain:<10} → {len(df):>6,} lignes")


# ============================================================
# CHARGEMENT SILVER
# ============================================================

def load_silver(engine):
    """Charge les Parquet Silver dans SQL Server."""
    print("\n🥈 Chargement SILVER → SQL Server")
    print("-" * 50)

    domains = ["customer", "claims", "policies"]

    for entity_id in CONFIG["entities"]:
        schema = f"silver_{entity_id}"
        for domain in domains:
            path = SILVER_BASE / entity_id / f"{domain}.parquet"
            if not path.exists():
                print(f"  ⚠️  Manquant : {path.name}")
                continue

            df = pd.read_parquet(path)
            df = _clean_for_sqlserver(df)

            df.to_sql(
                name=domain,
                con=engine,
                schema=schema,
                if_exists="replace",
                index=False,
                chunksize=500,
            )
            print(f"  ✅ {schema}.{domain:<10} → {len(df):>6,} lignes")


# ============================================================
# CHARGEMENT QUALITY LOGS
# ============================================================

def load_quality_logs(engine):
    """Charge les logs de qualité dans gold.data_quality_log."""
    print("\n🥇 Chargement QUALITY LOGS → SQL Server")
    print("-" * 50)

    csv_path = GOLD_BASE / "quality_report.csv"
    if not csv_path.exists():
        print("  ⚠️  quality_report.csv non trouvé")
        print("  👉 Lance d'abord : python src/03_quality_framework/quality_runner.py")
        return

    df = pd.read_csv(csv_path)
    df = _clean_for_sqlserver(df)

    df.to_sql(
        name="data_quality_log",
        con=engine,
        schema="gold",
        if_exists="replace",
        index=False,
        chunksize=500,
    )
    print(f"  ✅ gold.data_quality_log → {len(df):>6,} lignes")


# ============================================================
# CRÉATION DES VUES GOLD (Group-level)
# ============================================================

def create_gold_views(engine):
    """Crée les vues Gold consolidées toutes entités."""
    print("\n🥇 Création des vues Gold consolidées")
    print("-" * 50)

    views = {
        "v_customer_all": """
            SELECT * FROM silver_axa_france.customer
            UNION ALL
            SELECT * FROM silver_axa_uk.customer
            UNION ALL
            SELECT * FROM silver_axa_italy.customer
        """,
        "v_claims_all": """
            SELECT * FROM silver_axa_france.claims
            UNION ALL
            SELECT * FROM silver_axa_uk.claims
            UNION ALL
            SELECT * FROM silver_axa_italy.claims
        """,
        "v_policies_all": """
            SELECT * FROM silver_axa_france.policies
            UNION ALL
            SELECT * FROM silver_axa_uk.policies
            UNION ALL
            SELECT * FROM silver_axa_italy.policies
        """,
        "v_quality_summary": """
            SELECT
                entity,
                domain,
                check_level,
                check_category,
                status,
                COUNT(*)                        AS nb_checks,
                SUM(rows_failed)                AS total_rows_failed,
                AVG(CAST(failed_pct AS FLOAT))  AS avg_failed_pct,
                MAX(executed_at)                AS last_run_at
            FROM gold.data_quality_log
            GROUP BY entity, domain, check_level, check_category, status
        """,
        "v_quality_score_by_entity": """
            SELECT
                entity,
                COUNT(*)                                        AS total_checks,
                SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS nb_pass,
                SUM(CASE WHEN status = 'WARN' THEN 1 ELSE 0 END) AS nb_warn,
                SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) AS nb_fail,
                ROUND(
                    100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END)
                    / COUNT(*), 2
                )                                               AS score_pct,
                CASE
                    WHEN SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) > 0
                        THEN 'FAIL'
                    WHEN SUM(CASE WHEN status = 'WARN' THEN 1 ELSE 0 END) > 0
                        THEN 'WARN'
                    ELSE 'PASS'
                END                                             AS global_status
            FROM gold.data_quality_log
            GROUP BY entity
        """,
        "v_quality_score_by_domain": """
            SELECT
                entity,
                domain,
                COUNT(*)                                        AS total_checks,
                SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS nb_pass,
                SUM(CASE WHEN status = 'WARN' THEN 1 ELSE 0 END) AS nb_warn,
                SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) AS nb_fail,
                ROUND(
                    100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END)
                    / COUNT(*), 2
                )                                               AS score_pct
            FROM gold.data_quality_log
            GROUP BY entity, domain
        """,
    }

    with engine.connect() as conn:
        for view_name, view_sql in views.items():
            try:
                # DROP si existe déjà
                conn.execute(text(
                    f"IF OBJECT_ID('gold.{view_name}', 'V') IS NOT NULL "
                    f"DROP VIEW gold.{view_name}"
                ))
                conn.execute(text(
                    f"CREATE VIEW gold.{view_name} AS {view_sql}"
                ))
                conn.commit()
                print(f"  ✅ gold.{view_name} créée")
            except Exception as e:
                print(f"  ❌ Erreur sur {view_name} : {e}")


# ============================================================
# UTILITAIRES
# ============================================================

def _clean_for_sqlserver(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les types pandas incompatibles avec SQL Server."""
    for col in df.columns:
        # Dates → string (SQL Server gère ensuite)
        if df[col].dtype == "object":
            df[col] = df[col].astype(str).replace("None", None).replace("nan", None)
        # Bool → int
        elif df[col].dtype == "bool":
            df[col] = df[col].astype(int)
        # numpy types → python natifs
        elif hasattr(df[col], "dt"):
            df[col] = df[col].astype(str).replace("NaT", None)
    return df


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("AXAMesh — Chargement vers SQL Server")
    print(f"Serveur  : {SERVER}")
    print(f"Base     : {DATABASE}")
    print("=" * 60)

    print("\n🔌 Test de connexion...")
    engine = get_engine()
    test_connection(engine)

    # 1. Bronze
    load_bronze(engine)

    # 2. Silver
    load_silver(engine)

    # 3. Quality Logs
    load_quality_logs(engine)

    # 4. Vues Gold
    create_gold_views(engine)

    # Résumé final
    print(f"\n{'=' * 60}")
    print("✅ Chargement terminé !")
    print(f"\n📊 Vérification dans SSMS :")
    print(f"   USE axamesh;")
    print(f"   SELECT * FROM gold.v_quality_score_by_entity;")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()