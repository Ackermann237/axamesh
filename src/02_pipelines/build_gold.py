"""
AXAMesh - Construction de la couche Gold
KPIs consolidés Group-level pour Power BI
"""

import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

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


def create_gold_tables(engine):
    """Crée les tables Gold analytiques dans SQL Server."""

    gold_queries = {

        # ── 1. KPIs Customer par entité ──────────────────────
        "gold_customer_kpis": """
            IF OBJECT_ID('gold.customer_kpis', 'U') IS NOT NULL
                DROP TABLE gold.customer_kpis;

            SELECT
                entity,
                COUNT(*)                                            AS total_customers,
                SUM(CASE WHEN email_is_valid = 1 THEN 1 ELSE 0 END) AS valid_emails,
                SUM(CASE WHEN email_is_valid = 0 THEN 1 ELSE 0 END) AS invalid_emails,
                SUM(CASE WHEN dob_is_valid   = 1 THEN 1 ELSE 0 END) AS valid_dob,
                SUM(CASE WHEN _is_duplicate  = 1 THEN 1 ELSE 0 END) AS duplicates,
                SUM(CASE WHEN kyc_status = 'VERIFIED' THEN 1 ELSE 0 END) AS kyc_verified,
                SUM(CASE WHEN kyc_status = 'EXPIRED'  THEN 1 ELSE 0 END) AS kyc_expired,
                SUM(CASE WHEN kyc_status = 'PENDING'  THEN 1 ELSE 0 END) AS kyc_pending,
                SUM(CASE WHEN segment = 'INDIVIDUAL'  THEN 1 ELSE 0 END) AS seg_individual,
                SUM(CASE WHEN segment = 'PROFESSIONAL'THEN 1 ELSE 0 END) AS seg_professional,
                SUM(CASE WHEN segment = 'CORPORATE'   THEN 1 ELSE 0 END) AS seg_corporate,
                ROUND(AVG(CAST(nb_active_contracts AS FLOAT)), 2)  AS avg_contracts,
                ROUND(SUM(CAST(annual_premium_eur  AS FLOAT)), 2)  AS total_premium_eur,
                ROUND(AVG(CAST(annual_premium_eur  AS FLOAT)), 2)  AS avg_premium_eur,
                ROUND(
                    100.0 * SUM(CASE WHEN email_is_valid = 1 THEN 1 ELSE 0 END)
                    / COUNT(*), 2
                )                                                   AS email_quality_pct,
                ROUND(
                    100.0 * SUM(CASE WHEN kyc_status = 'VERIFIED' THEN 1 ELSE 0 END)
                    / COUNT(*), 2
                )                                                   AS kyc_verified_pct
            INTO gold.customer_kpis
            FROM gold.v_customer_all
            GROUP BY entity
        """,

        # ── 2. KPIs Claims par entité ─────────────────────────
        "gold_claims_kpis": """
            IF OBJECT_ID('gold.claims_kpis', 'U') IS NOT NULL
                DROP TABLE gold.claims_kpis;

            SELECT
                entity,
                COUNT(*)                                               AS total_claims,
                SUM(CASE WHEN amount_is_valid     = 1 THEN 1 ELSE 0 END) AS valid_amounts,
                SUM(CASE WHEN dates_are_coherent  = 1 THEN 1 ELSE 0 END) AS coherent_dates,
                SUM(CASE WHEN status_is_valid     = 1 THEN 1 ELSE 0 END) AS valid_statuses,
                SUM(CASE WHEN status = 'OPEN'      THEN 1 ELSE 0 END) AS status_open,
                SUM(CASE WHEN status = 'CLOSED'    THEN 1 ELSE 0 END) AS status_closed,
                SUM(CASE WHEN status = 'PAID'      THEN 1 ELSE 0 END) AS status_paid,
                SUM(CASE WHEN status = 'REJECTED'  THEN 1 ELSE 0 END) AS status_rejected,
                SUM(CASE WHEN status = 'IN_REVIEW' THEN 1 ELSE 0 END) AS status_in_review,
                ROUND(SUM(CAST(claim_amount_eur AS FLOAT)), 2)         AS total_claims_eur,
                ROUND(AVG(CAST(claim_amount_eur AS FLOAT)), 2)         AS avg_claim_eur,
                ROUND(MAX(CAST(claim_amount_eur AS FLOAT)), 2)         AS max_claim_eur,
                ROUND(
                    100.0 * SUM(CASE WHEN dates_are_coherent = 1 THEN 1 ELSE 0 END)
                    / COUNT(*), 2
                )                                                      AS date_quality_pct
            INTO gold.claims_kpis
            FROM gold.v_claims_all
            GROUP BY entity
        """,

        # ── 3. KPIs Policies par entité ───────────────────────
        "gold_policies_kpis": """
            IF OBJECT_ID('gold.policies_kpis', 'U') IS NOT NULL
                DROP TABLE gold.policies_kpis;

            SELECT
                entity,
                COUNT(*)                                                   AS total_policies,
                SUM(CASE WHEN premium_is_valid   = 1 THEN 1 ELSE 0 END)   AS valid_premiums,
                SUM(CASE WHEN dates_are_coherent = 1 THEN 1 ELSE 0 END)   AS coherent_dates,
                SUM(CASE WHEN product_is_valid   = 1 THEN 1 ELSE 0 END)   AS valid_products,
                SUM(CASE WHEN status = 'ACTIVE'    THEN 1 ELSE 0 END)     AS status_active,
                SUM(CASE WHEN status = 'EXPIRED'   THEN 1 ELSE 0 END)     AS status_expired,
                SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END)     AS status_cancelled,
                SUM(CASE WHEN status = 'SUSPENDED' THEN 1 ELSE 0 END)     AS status_suspended,
                SUM(CASE WHEN product_type = 'AUTO'   THEN 1 ELSE 0 END)  AS product_auto,
                SUM(CASE WHEN product_type = 'HOME'   THEN 1 ELSE 0 END)  AS product_home,
                SUM(CASE WHEN product_type = 'HEALTH' THEN 1 ELSE 0 END)  AS product_health,
                SUM(CASE WHEN product_type = 'LIFE'   THEN 1 ELSE 0 END)  AS product_life,
                SUM(CASE WHEN product_type = 'TRAVEL' THEN 1 ELSE 0 END)  AS product_travel,
                ROUND(SUM(CAST(annual_premium_eur AS FLOAT)), 2)           AS total_premium_eur,
                ROUND(AVG(CAST(annual_premium_eur AS FLOAT)), 2)           AS avg_premium_eur,
                ROUND(
                    100.0 * SUM(CASE WHEN premium_is_valid = 1 THEN 1 ELSE 0 END)
                    / COUNT(*), 2
                )                                                          AS premium_quality_pct
            INTO gold.policies_kpis
            FROM gold.v_policies_all
            GROUP BY entity
        """,

        # ── 4. Tableau de bord Group-level ────────────────────
        "gold_group_dashboard": """
            IF OBJECT_ID('gold.group_dashboard', 'U') IS NOT NULL
                DROP TABLE gold.group_dashboard;

            SELECT
                c.entity,
                c.total_customers,
                c.email_quality_pct,
                c.kyc_verified_pct,
                c.total_premium_eur         AS customer_premium_eur,
                cl.total_claims,
                cl.total_claims_eur,
                cl.avg_claim_eur,
                cl.date_quality_pct         AS claims_date_quality_pct,
                p.total_policies,
                p.status_active             AS active_policies,
                p.total_premium_eur         AS policies_premium_eur,
                p.premium_quality_pct,
                q.nb_pass,
                q.nb_warn,
                q.nb_fail,
                q.score_pct                 AS quality_score_pct,
                q.global_status
            INTO gold.group_dashboard
            FROM gold.v_quality_score_by_entity q
            LEFT JOIN gold.customer_kpis c  ON q.entity = c.entity
            LEFT JOIN gold.claims_kpis   cl ON q.entity = cl.entity
            LEFT JOIN gold.policies_kpis p  ON q.entity = p.entity
        """,
    }

    with engine.connect() as conn:
        for name, query in gold_queries.items():
            try:
                conn.execute(text(query))
                conn.commit()
                print(f"  ✅ {name} créée")
            except Exception as e:
                print(f"  ❌ Erreur {name} : {e}")


def print_summary(engine):
    """Affiche un résumé du dashboard Group-level."""
    print("\n📊 Dashboard Group-level :")
    print("-" * 70)

    with engine.connect() as conn:
        df = pd.read_sql(
            "SELECT entity, total_customers, total_claims, total_policies, "
            "quality_score_pct, global_status FROM gold.group_dashboard "
            "ORDER BY entity",
            conn
        )
        print(df.to_string(index=False))


def main():
    print("=" * 60)
    print("AXAMesh — Construction couche Gold")
    print("=" * 60)

    engine = get_engine()

    print("\n🥇 Création des tables Gold KPIs...")
    create_gold_tables(engine)
    print_summary(engine)

    print(f"\n{'=' * 60}")
    print("✅ Couche Gold terminée !")
    print("\n📋 Tables créées dans SQL Server :")
    print("   gold.customer_kpis")
    print("   gold.claims_kpis")
    print("   gold.policies_kpis")
    print("   gold.group_dashboard  ← base du dashboard Power BI")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()