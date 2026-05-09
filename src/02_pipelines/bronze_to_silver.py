"""
AXAMesh - Pipeline Bronze → Silver
Nettoyage, typage, standardisation EUR, validation de base.
"""

import pandas as pd
import numpy as np
import yaml
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "entities.yaml"
BRONZE_BASE = ROOT / "data" / "bronze"
SILVER_BASE = ROOT / "data" / "silver"

with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

SILVER_BASE.mkdir(parents=True, exist_ok=True)


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def log(msg: str):
    print(f"  {msg}")


def clean_string_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Strip espaces et uniformise la casse sur les colonnes texte."""
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("None", None).replace("nan", None)
    return df


def add_silver_metadata(df: pd.DataFrame, entity_id: str, domain: str) -> pd.DataFrame:
    """Ajoute les colonnes d'audit Silver."""
    df["_silver_entity"]       = entity_id
    df["_silver_domain"]       = domain
    df["_silver_processed_at"] = datetime.utcnow()
    return df


# ============================================================
# SILVER CUSTOMER
# ============================================================

def process_customer(entity_id: str, entity_config: dict) -> pd.DataFrame:
    path = BRONZE_BASE / entity_id / "customer.csv"
    df = pd.read_csv(path)
    n_raw = len(df)
    log(f"Bronze : {n_raw} lignes lues")

    # 1. Typage
    df["date_of_birth"]   = pd.to_datetime(df["date_of_birth"],   errors="coerce").dt.date
    df["customer_since"]  = pd.to_datetime(df["customer_since"],  errors="coerce").dt.date
    df["_ingested_at"]    = pd.to_datetime(df["_ingested_at"],    errors="coerce")

    # 2. Nettoyage colonnes texte
    df = clean_string_cols(df, ["email", "first_name", "last_name",
                                 "city", "country", "kyc_status", "segment"])

    # 3. Email : lowercase + flag invalide
    df["email"] = df["email"].str.lower()
    df["email_is_valid"] = df["email"].apply(
        lambda x: isinstance(x, str) and "@" in x and "." in x.split("@")[-1]
        if pd.notna(x) else False
    )

    # 4. Date de naissance : flag aberrant
    today = date.today()
    df["dob_is_valid"] = df["date_of_birth"].apply(
        lambda d: date(1900, 1, 1) <= d <= today if isinstance(d, date) else False
    )

    # 5. Flag doublon (même first+last+dob+entity)
    df["_is_duplicate"] = df.duplicated(
        subset=["first_name", "last_name", "date_of_birth", "entity"],
        keep="first"
    )

    # 6. Standardisation KYC et segment
    df["kyc_status"] = df["kyc_status"].str.upper()
    df["segment"]    = df["segment"].str.upper()

    # 7. Colonnes numériques
    df["nb_active_contracts"] = pd.to_numeric(df["nb_active_contracts"], errors="coerce").fillna(0).astype(int)
    df["annual_premium_eur"]  = pd.to_numeric(df["annual_premium_eur"], errors="coerce").round(2)

    # 8. Métadonnées Silver
    df = add_silver_metadata(df, entity_id, "customer")

    n_silver = len(df)
    n_dupes  = df["_is_duplicate"].sum()
    n_bad_email = (~df["email_is_valid"]).sum()
    n_bad_dob   = (~df["dob_is_valid"]).sum()

    log(f"Silver : {n_silver} lignes")
    log(f"  ⚠️  Doublons flaggés     : {n_dupes}")
    log(f"  ⚠️  Emails invalides     : {n_bad_email}")
    log(f"  ⚠️  DOB aberrantes       : {n_bad_dob}")

    return df


# ============================================================
# SILVER CLAIMS
# ============================================================

def process_claims(entity_id: str, entity_config: dict) -> pd.DataFrame:
    path = BRONZE_BASE / entity_id / "claims.csv"
    df = pd.read_csv(path)
    n_raw = len(df)
    log(f"Bronze : {n_raw} lignes lues")

    # 1. Typage
    df["incident_date"]    = pd.to_datetime(df["incident_date"],    errors="coerce").dt.date
    df["declaration_date"] = pd.to_datetime(df["declaration_date"], errors="coerce").dt.date
    df["_ingested_at"]     = pd.to_datetime(df["_ingested_at"],     errors="coerce")

    # 2. Nettoyage
    df = clean_string_cols(df, ["product_type", "claim_type", "status", "entity"])
    df["status"]       = df["status"].str.upper()
    df["product_type"] = df["product_type"].str.upper()

    # 3. Montants
    df["claim_amount"]     = pd.to_numeric(df["claim_amount"],     errors="coerce")
    df["claim_amount_eur"] = pd.to_numeric(df["claim_amount_eur"], errors="coerce").round(2)

    # 4. Flags qualité
    df["amount_is_valid"] = df["claim_amount"] > 0

    df["dates_are_coherent"] = df.apply(
        lambda r: (
            isinstance(r["declaration_date"], date) and
            isinstance(r["incident_date"],    date) and
            r["declaration_date"] >= r["incident_date"]
        ), axis=1
    )

    valid_statuses = {"OPEN", "IN_REVIEW", "CLOSED", "REJECTED", "PAID"}
    df["status_is_valid"] = df["status"].isin(valid_statuses)

    # 5. Métadonnées Silver
    df = add_silver_metadata(df, entity_id, "claims")

    log(f"Silver : {len(df)} lignes")
    log(f"  ⚠️  Montants invalides   : {(~df['amount_is_valid']).sum()}")
    log(f"  ⚠️  Dates incohérentes   : {(~df['dates_are_coherent']).sum()}")
    log(f"  ⚠️  Statuts invalides    : {(~df['status_is_valid']).sum()}")

    return df


# ============================================================
# SILVER POLICIES
# ============================================================

def process_policies(entity_id: str, entity_config: dict) -> pd.DataFrame:
    path = BRONZE_BASE / entity_id / "policies.csv"
    df = pd.read_csv(path)
    n_raw = len(df)
    log(f"Bronze : {n_raw} lignes lues")

    # 1. Typage
    df["start_date"]   = pd.to_datetime(df["start_date"],   errors="coerce").dt.date
    df["end_date"]     = pd.to_datetime(df["end_date"],     errors="coerce").dt.date
    df["_ingested_at"] = pd.to_datetime(df["_ingested_at"], errors="coerce")

    # 2. Nettoyage
    df = clean_string_cols(df, ["product_type", "status",
                                 "payment_frequency", "entity"])
    df["product_type"]      = df["product_type"].str.upper()
    df["status"]            = df["status"].str.upper()
    df["payment_frequency"] = df["payment_frequency"].str.upper()

    # 3. Montants
    df["annual_premium"]     = pd.to_numeric(df["annual_premium"],     errors="coerce")
    df["annual_premium_eur"] = pd.to_numeric(df["annual_premium_eur"], errors="coerce").round(2)

    # 4. Flags qualité
    df["premium_is_valid"] = df["annual_premium"] > 0

    df["dates_are_coherent"] = df.apply(
        lambda r: (
            isinstance(r["end_date"],   date) and
            isinstance(r["start_date"], date) and
            r["end_date"] > r["start_date"]
        ), axis=1
    )

    valid_products = {"AUTO", "HOME", "HEALTH", "LIFE", "TRAVEL", "LIABILITY"}
    df["product_is_valid"] = df["product_type"].isin(valid_products)

    # 5. Durée de la police (en jours)
    df["policy_duration_days"] = df.apply(
        lambda r: (r["end_date"] - r["start_date"]).days
        if isinstance(r["end_date"], date) and isinstance(r["start_date"], date)
        else None, axis=1
    )

    # 6. Métadonnées Silver
    df = add_silver_metadata(df, entity_id, "policies")

    log(f"Silver : {len(df)} lignes")
    log(f"  ⚠️  Primes invalides     : {(~df['premium_is_valid']).sum()}")
    log(f"  ⚠️  Dates incohérentes   : {(~df['dates_are_coherent']).sum()}")
    log(f"  ⚠️  Produits invalides   : {(~df['product_is_valid']).sum()}")

    return df


# ============================================================
# MAIN
# ============================================================

PROCESSORS = {
    "customer": process_customer,
    "claims":   process_claims,
    "policies": process_policies,
}

def main():
    print("=" * 60)
    print("AXAMesh — Pipeline Bronze → Silver")
    print("=" * 60)

    summary = []

    for entity_id, entity_config in CONFIG["entities"].items():
        print(f"\n🏢 {entity_config['name']}")
        print("-" * 40)

        entity_silver_dir = SILVER_BASE / entity_id
        entity_silver_dir.mkdir(parents=True, exist_ok=True)

        for domain, processor in PROCESSORS.items():
            print(f"\n  📂 Domaine : {domain.upper()}")
            df = processor(entity_id, entity_config)

            # Sauvegarde en Parquet (plus efficace que CSV pour Silver+)
            output_path = entity_silver_dir / f"{domain}.parquet"
            df.to_parquet(output_path, index=False)
            log(f"💾 Sauvegardé : {output_path}")

            summary.append({
                "entity":   entity_id,
                "domain":   domain,
                "nb_rows":  len(df),
            })

    # Résumé global
    summary_df = pd.DataFrame(summary)
    print(f"\n{'=' * 60}")
    print("✅ Pipeline Bronze → Silver terminé !")
    print(f"\n{summary_df.to_string(index=False)}")
    print(f"\n   Total lignes Silver : {summary_df['nb_rows'].sum():,}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()