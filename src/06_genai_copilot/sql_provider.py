"""
AXAMesh - SQL Provider
======================
Text-to-SQL : le LLM génère du SQL pour interroger la base axamesh
(SQL Server, même base que celle consommée par PowerBI).

Si SQL Server n'est pas disponible (démo sur autre machine), bascule
automatiquement sur le CSV quality_report.csv en local.

Cette dualité garantit la robustesse de la démo et démontre une
architecture data agnostique de la source.
"""

import os
import re
import pandas as pd
from pathlib import Path
from typing import Optional

ROOT      = Path(__file__).parent.parent.parent
GOLD_BASE = ROOT / "data" / "gold"

# ──────────────────────────────────────────────────────────────
# CONFIG SQL SERVER (axamesh)
# ──────────────────────────────────────────────────────────────
DEFAULT_SERVER   = os.getenv("AXAMESH_SQL_SERVER", "AMOUGOU\\SQLEXPRESS")
DEFAULT_DATABASE = os.getenv("AXAMESH_SQL_DATABASE", "axamesh")
DEFAULT_DRIVER   = "ODBC Driver 17 for SQL Server"

# ──────────────────────────────────────────────────────────────
# SCHEMA DESCRIPTION pour le LLM
# ──────────────────────────────────────────────────────────────
SQL_SCHEMA_DESCRIPTION = """
Tu as accès à la base SQL Server `axamesh` (architecture Medallion).
Voici les tables disponibles dans le schéma `gold` :

1. `gold.data_quality_log` : journal complet des contrôles de qualité
   - run_id (TEXT)
   - executed_at (DATETIME)
   - entity (TEXT) : 'axa_france', 'axa_uk', 'axa_italy'
   - domain (TEXT) : 'customer', 'claims', 'policies'
   - check_level (TEXT) : 'group_mandatory', 'domain_specific', 'entity_local'
   - check_name (TEXT) : nom unique du contrôle
   - check_category (TEXT) : 'Completeness', 'Uniqueness', 'Freshness',
                              'BusinessLogic', 'Range', 'Referential'
   - description (TEXT) : description du contrôle
   - rows_total (INT)
   - rows_failed (INT)
   - failed_pct (FLOAT)
   - status (TEXT) : 'PASS', 'WARN', 'FAIL'

IMPORTANT — UNICITÉ DES DONNÉES :
La table contient plusieurs runs historiques. Pour avoir exactement 60 contrôles
(comme PowerBI), toujours filtrer sur le dernier run avec :
   WHERE run_id = (SELECT TOP 1 run_id FROM gold.data_quality_log ORDER BY executed_at DESC)
Ne JAMAIS oublier ce filtre sinon les résultats seront multipliés.

2. `gold.customer_kpis` : KPIs Customer agrégés par entité
   - entity, total_customers, valid_emails, kyc_verified, kyc_expired,
     seg_individual, seg_professional, seg_corporate, total_premium_eur,
     email_quality_pct, kyc_verified_pct

3. `gold.claims_kpis` : KPIs Claims agrégés par entité
   - entity, total_claims, valid_amounts, status_open, status_closed,
     status_paid, total_claims_eur, avg_claim_eur, max_claim_eur,
     date_quality_pct

4. `gold.policies_kpis` : KPIs Policies (= underwriting) par entité
   - entity, total_policies, status_active, status_expired,
     product_auto, product_home, product_health, product_life,
     total_premium_eur, premium_quality_pct

5. `gold.group_dashboard` : tableau consolidé Group-level
   - entity, total_customers, total_claims, total_policies,
     quality_score_pct, global_status, et tous les KPIs des tables ci-dessus

Règles à respecter quand tu génères une requête SQL :
- Utilise UNIQUEMENT du SQL Server (T-SQL)
- Préfixe toujours les tables avec `gold.`
- Renvoie UNIQUEMENT la requête SQL, sans explication
- Pas de DROP, DELETE, UPDATE, INSERT — uniquement SELECT
- Limite les résultats à TOP 20 si la requête peut être volumineuse
- Utilise des alias clairs pour les colonnes calculées
"""

TEXT_TO_SQL_PROMPT = """Tu es un expert SQL Server T-SQL spécialisé en data quality.
Génère UNIQUEMENT la requête SQL (sans explication, sans markdown, sans backticks).

RÈGLES CRITIQUES :
- Pour compter les FAIL/PASS/WARN : COUNT les lignes où status = 'FAIL' dans gold.data_quality_log
- NE PAS utiliser rows_failed pour compter les statuts — c'est une métrique différente (lignes de données)
- Pour "combien de FAIL" → COUNT(*) WHERE status = 'FAIL'
- Pour "pass rate" → COUNT WHERE status='PASS' / COUNT(*) * 100
- Toujours préfixer les tables avec gold.
- Limiter à TOP 20 si volumineuse

{schema}

Question : {question}

SQL :"""


class SQLProvider:
    """Provider Text-to-SQL pour la base axamesh.

    Architecture :
      1. Le LLM génère une requête SQL à partir de la question
      2. La requête est exécutée sur SQL Server (ou fallback CSV)
      3. Le résultat est retourné sous forme de DataFrame
    """

    def __init__(self, llm_provider, server: str = DEFAULT_SERVER,
                 database: str = DEFAULT_DATABASE):
        self.llm = llm_provider
        self.server = server
        self.database = database
        self.engine = self._init_engine()
        self.csv_fallback = not self.engine

    def _init_engine(self):
        """Tente la connexion SQL Server via pyodbc direct, sinon fallback CSV."""
        try:
            import pyodbc
            from sqlalchemy import create_engine, text
            from sqlalchemy.engine import URL

            # URL structurée — évite les problèmes d'encodage du backslash
            connection_url = URL.create(
                "mssql+pyodbc",
                query={
                    "odbc_connect": (
                        f"DRIVER={{{DEFAULT_DRIVER}}};"
                        f"SERVER={self.server};"
                        f"DATABASE={self.database};"
                        f"Trusted_Connection=yes;"
                        f"TrustServerCertificate=yes;"
                    )
                }
            )
            engine = create_engine(connection_url, fast_executemany=True)
            # Test connexion
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM gold.data_quality_log"))
                count = result.fetchone()[0]
                print(f"✅ SQL Server connecté — {count} lignes dans data_quality_log")
            return engine
        except Exception as e:
            print(f"⚠️  SQL Server indisponible ({type(e).__name__}: {e}), fallback CSV.")
            return None

    @property
    def name(self) -> str:
        backend = "SQL Server" if not self.csv_fallback else "CSV (fallback)"
        return f"SQLProvider [{backend}]"

    def generate_sql(self, question: str) -> str:
        """Le LLM génère une requête SQL à partir de la question."""
        prompt = TEXT_TO_SQL_PROMPT.format(
            schema=SQL_SCHEMA_DESCRIPTION,
            question=question,
        )
        try:
            sql = self.llm.chat(
                system_prompt="Tu es un expert SQL Server T-SQL.",
                user_message=prompt,
            )
        except Exception:
            sql = ""

        # Nettoyage backticks markdown
        sql = re.sub(r"```(?:sql)?", "", sql or "", flags=re.IGNORECASE).strip()

        # Extrait uniquement la partie SELECT/WITH
        match = re.search(r"(SELECT|WITH)\b.*", sql, re.IGNORECASE | re.DOTALL)
        sql = match.group(0).strip() if match else ""

        # Fallback si le LLM n'a pas produit de SQL valide
        if not sql:
            sql = (
                "SELECT entity, domain, status, check_name, "
                "check_category, failed_pct, description "
                "FROM gold.data_quality_log "
                "WHERE status = 'FAIL' "
                "ORDER BY failed_pct DESC"
            )
        return sql

    def is_safe_query(self, sql: str) -> bool:
        """Sécurité : on n'autorise que les SELECT."""
        if not sql:
            return False
        sql_lower = sql.lower().strip()
        forbidden = ["drop ", "delete ", "update ", "insert ", "alter ",
                     "truncate ", "exec ", "execute "]
        if any(kw in sql_lower for kw in forbidden):
            return False
        return sql_lower.startswith("select") or sql_lower.startswith("with")

    def execute(self, sql: str) -> pd.DataFrame:
        """Exécute la requête SQL et retourne un DataFrame."""
        if not self.is_safe_query(sql):
            raise ValueError("Requête non autorisée (uniquement SELECT)")
        if self.engine:
            try:
                return pd.read_sql(sql, self.engine)
            except Exception as e:
                print(f"⚠️ SQL Server erreur ({e}), fallback CSV.")
                return self._csv_fallback_query()
        else:
            return self._csv_fallback_query()

    def _csv_fallback_query(self) -> pd.DataFrame:
        """Fallback : retourne le quality_report en mode CSV."""
        path = GOLD_BASE / "quality_report.csv"
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()

    def query(self, question: str) -> dict:
        """Pipeline complet : NL → SQL → Result."""
        try:
            sql = self.generate_sql(question)
            if not sql or not self.is_safe_query(sql):
                return {"sql": sql, "data": self._csv_fallback_query(), "rows": 0, "error": "SQL invalide, fallback CSV"}
            df = self.execute(sql)
            return {"sql": sql, "data": df, "rows": len(df), "error": None}
        except Exception as e:
            return {"sql": None, "data": self._csv_fallback_query(), "error": f"{type(e).__name__}: {e}"}