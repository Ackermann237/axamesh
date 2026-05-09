"""
AXAMesh - Générateur de données Customer synthétiques
Génère des datasets Customer réalistes pour 3 entités fictives AXA.
Injecte volontairement des erreurs de qualité pour tester le framework DQ.
"""

import pandas as pd
import numpy as np
import yaml
import uuid
import random
from faker import Faker
from datetime import datetime, date, timedelta
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "entities.yaml"
OUTPUT_BASE = ROOT / "data" / "bronze"

with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def random_date(start: date, end: date) -> date:
    """Génère une date aléatoire entre start et end."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def inject_nulls(series: pd.Series, rate: float) -> pd.Series:
    """Injecte des valeurs NULL dans une série à un taux donné."""
    mask = np.random.random(len(series)) < rate
    result = series.copy().astype(object)
    result[mask] = None
    return result


def inject_invalid_emails(series: pd.Series, rate: float) -> pd.Series:
    """Injecte des emails invalides (sans @) à un taux donné."""
    mask = np.random.random(len(series)) < rate
    result = series.copy()
    for i in result[mask].index:
        result[i] = result[i].replace("@", "") if result[i] else result[i]
    return result


def inject_duplicates(df: pd.DataFrame, rate: float) -> pd.DataFrame:
    """Injecte des doublons dans le DataFrame."""
    n_dupes = int(len(df) * rate)
    if n_dupes == 0:
        return df
    dupes = df.sample(n=n_dupes, random_state=RANDOM_SEED).copy()
    # Reset UUID pour simuler un doublon "logique"
    # mais avec un nouvel ID technique
    dupes["customer_id"] = [str(uuid.uuid4()) for _ in range(n_dupes)]
    result = pd.concat([df, dupes], ignore_index=True)
    print(f"  💉 {n_dupes} doublons injectés ({rate*100:.0f}%)")
    return result


# ============================================================
# GÉNÉRATEUR PRINCIPAL
# ============================================================

def generate_customers(entity_id: str, entity_config: dict) -> pd.DataFrame:
    """
    Génère un dataset Customer réaliste pour une entité AXA.

    Args:
        entity_id: ex 'axa_france'
        entity_config: configuration de l'entité depuis entities.yaml

    Returns:
        pd.DataFrame avec les données customer + erreurs injectées
    """
    locale = entity_config["locale"]
    country = entity_config["country"]
    n = entity_config["nb_customers"]
    fake = Faker(locale)
    Faker.seed(RANDOM_SEED)

    print(f"\n🏢 Génération Customer — {entity_config['name']} ({n} clients)")

    # ---- Génération des données propres ----
    today = date.today()
    records = []

    for _ in range(n):
        dob = random_date(date(1940, 1, 1), date(2005, 12, 31))
        customer_since = random_date(date(2005, 1, 1), today)

        # Segments pondérés (réaliste pour un assureur)
        segment = random.choices(
            ["INDIVIDUAL", "PROFESSIONAL", "CORPORATE"],
            weights=[0.70, 0.20, 0.10]
        )[0]

        kyc_status = random.choices(
            ["VERIFIED", "PENDING", "EXPIRED"],
            weights=[0.75, 0.10, 0.15]
        )[0]

        nb_contracts = random.choices(
            [0, 1, 2, 3, 4, 5],
            weights=[0.05, 0.35, 0.30, 0.15, 0.10, 0.05]
        )[0]

        annual_premium = round(
            nb_contracts * random.uniform(200, 3000), 2
        ) if nb_contracts > 0 else 0.0

        # Conversion en EUR si nécessaire
        fx = CONFIG["fx_rates"].get(entity_config["currency"], 1.0)
        annual_premium_eur = round(annual_premium * fx, 2)

        records.append({
            "customer_id": str(uuid.uuid4()),
            "entity": entity_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "date_of_birth": dob,
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.street_address(),
            "city": fake.city(),
            "country": country,
            "postal_code": fake.postcode(),
            "customer_since": customer_since,
            "kyc_status": kyc_status,
            "segment": segment,
            "nb_active_contracts": nb_contracts,
            "annual_premium_local": annual_premium,
            "annual_premium_eur": annual_premium_eur,
            "currency": entity_config["currency"],
            "_ingested_at": datetime.utcnow(),
        })

    df = pd.DataFrame(records)
    print(f"  ✅ {len(df)} clients générés (données propres)")

    # ---- Injection des erreurs qualité ----
    print("  💉 Injection des erreurs qualité...")

    # 1. NULLs sur email (3%)
    df["email"] = inject_nulls(df["email"], rate=0.03)
    print(f"  💉 NULLs email : ~{int(0.03 * n)} lignes")

    # 2. Emails invalides (5% des emails non-NULL)
    df["email"] = inject_invalid_emails(df["email"], rate=0.05)
    print(f"  💉 Emails invalides : ~{int(0.05 * n)} lignes")

    # 3. Dates de naissance aberrantes (1%)
    aberrant_idx = df.sample(frac=0.01, random_state=RANDOM_SEED).index
    df.loc[aberrant_idx, "date_of_birth"] = date(2035, 1, 1)
    print(f"  💉 DOB aberrantes : {len(aberrant_idx)} lignes")

    # 4. Incohérences pays (2%)
    wrong_country_idx = df.sample(frac=0.02, random_state=RANDOM_SEED).index
    wrong_countries = [c for c in ["France", "United Kingdom", "Italy", "Germany", "Spain"]
                       if c != country]
    df.loc[wrong_country_idx, "country"] = random.choice(wrong_countries)
    print(f"  💉 Pays incohérents : {len(wrong_country_idx)} lignes")

    # 5. Doublons (2%)
    df = inject_duplicates(df, rate=0.02)

    print(f"  📊 Dataset final : {len(df)} lignes")
    return df


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("AXAMesh — Génération des données Customer")
    print("=" * 60)

    all_dfs = []

    for entity_id, entity_config in CONFIG["entities"].items():
        # Génération
        df = generate_customers(entity_id, entity_config)

        # Sauvegarde en CSV (Bronze)
        output_dir = OUTPUT_BASE / entity_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "customer.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"  💾 Sauvegardé : {output_path}")

        all_dfs.append(df)

    # Stats globales
    total = pd.concat(all_dfs, ignore_index=True)
    print(f"\n{'=' * 60}")
    print(f"✅ Génération terminée !")
    print(f"   Total lignes : {len(total):,}")
    print(f"   Entités      : {total['entity'].nunique()}")
    print(f"   Segments     : {dict(total['segment'].value_counts())}")
    print(f"   KYC statuts  : {dict(total['kyc_status'].value_counts())}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()