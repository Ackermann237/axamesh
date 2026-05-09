"""
AXAMesh - Générateur de données Claims (Sinistres) synthétiques
"""

import pandas as pd
import numpy as np
import yaml
import uuid
import random
from faker import Faker
from datetime import datetime, date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "entities.yaml"
OUTPUT_BASE = ROOT / "data" / "bronze"

with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

PRODUCT_TYPES = ["AUTO", "HOME", "HEALTH", "LIFE", "TRAVEL", "LIABILITY"]
CLAIM_STATUSES = ["OPEN", "IN_REVIEW", "CLOSED", "REJECTED", "PAID"]
CLAIM_TYPES = {
    "AUTO":       ["Collision", "Theft", "Windshield", "Fire", "Natural_Disaster"],
    "HOME":       ["Water_Damage", "Fire", "Burglary", "Natural_Disaster", "Vandalism"],
    "HEALTH":     ["Hospitalization", "Surgery", "Medication", "Dental", "Vision"],
    "LIFE":       ["Death_Benefit", "Disability", "Critical_Illness"],
    "TRAVEL":     ["Trip_Cancellation", "Medical_Abroad", "Luggage_Loss", "Flight_Delay"],
    "LIABILITY":  ["Third_Party_Injury", "Property_Damage", "Professional_Liability"],
}

def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)))


def generate_claims(entity_id: str, entity_config: dict) -> pd.DataFrame:
    locale = entity_config["locale"]
    n = entity_config["nb_claims"]
    fake = Faker(locale)
    Faker.seed(RANDOM_SEED)
    fx = CONFIG["fx_rates"].get(entity_config["currency"], 1.0)

    print(f"\n🏢 Génération Claims — {entity_config['name']} ({n} sinistres)")

    records = []
    today = date.today()

    for _ in range(n):
        product = random.choice(PRODUCT_TYPES)
        claim_type = random.choice(CLAIM_TYPES[product])

        # Date sinistre
        incident_date = random_date(date(2020, 1, 1), today)

        # Date déclaration >= date sinistre (normal)
        days_to_declare = random.randint(0, 30)
        declaration_date = incident_date + timedelta(days=days_to_declare)
        if declaration_date > today:
            declaration_date = today

        # Montant selon le type
        amount_ranges = {
            "AUTO": (500, 50000),
            "HOME": (1000, 150000),
            "HEALTH": (100, 30000),
            "LIFE": (10000, 500000),
            "TRAVEL": (50, 10000),
            "LIABILITY": (500, 200000),
        }
        low, high = amount_ranges[product]
        claim_amount = round(random.uniform(low, high), 2)
        claim_amount_eur = round(claim_amount * fx, 2)

        # Statut pondéré
        status = random.choices(
            CLAIM_STATUSES,
            weights=[0.20, 0.15, 0.40, 0.10, 0.15]
        )[0]

        records.append({
            "claim_id": str(uuid.uuid4()),
            "customer_id": str(uuid.uuid4()),  # FK simulée
            "entity": entity_id,
            "product_type": product,
            "claim_type": claim_type,
            "incident_date": incident_date,
            "declaration_date": declaration_date,
            "claim_amount": claim_amount,
            "claim_amount_eur": claim_amount_eur,
            "currency": entity_config["currency"],
            "status": status,
            "description": fake.sentence(nb_words=8),
            "_ingested_at": datetime.utcnow(),
        })

    df = pd.DataFrame(records)
    print(f"  ✅ {len(df)} sinistres générés (données propres)")

    # ---- Injection erreurs ----
    print("  💉 Injection des erreurs qualité...")

    # 1. Dates incohérentes : declaration_date < incident_date (2%)
    bad_date_idx = df.sample(frac=0.02, random_state=RANDOM_SEED).index
    df.loc[bad_date_idx, "declaration_date"] = df.loc[bad_date_idx, "incident_date"] - timedelta(days=5)
    print(f"  💉 Dates incohérentes : {len(bad_date_idx)} lignes")

    # 2. Montants négatifs (1%)
    neg_idx = df.sample(frac=0.01, random_state=RANDOM_SEED).index
    df.loc[neg_idx, "claim_amount"] = -abs(df.loc[neg_idx, "claim_amount"])
    df.loc[neg_idx, "claim_amount_eur"] = -abs(df.loc[neg_idx, "claim_amount_eur"])
    print(f"  💉 Montants négatifs : {len(neg_idx)} lignes")

    # 3. Statuts invalides (0.5%)
    bad_status_idx = df.sample(frac=0.005, random_state=RANDOM_SEED).index
    df.loc[bad_status_idx, "status"] = "UNKNOWN"
    print(f"  💉 Statuts invalides : {len(bad_status_idx)} lignes")

    # 4. NULL sur claim_id (0.2%)
    null_id_idx = df.sample(frac=0.002, random_state=RANDOM_SEED).index
    df.loc[null_id_idx, "claim_id"] = None
    print(f"  💉 NULL claim_id : {len(null_id_idx)} lignes")

    print(f"  📊 Dataset final : {len(df)} lignes")
    return df


def main():
    print("=" * 60)
    print("AXAMesh — Génération des données Claims")
    print("=" * 60)

    all_dfs = []

    for entity_id, entity_config in CONFIG["entities"].items():
        df = generate_claims(entity_id, entity_config)

        output_dir = OUTPUT_BASE / entity_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "claims.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"  💾 Sauvegardé : {output_path}")
        all_dfs.append(df)

    total = pd.concat(all_dfs, ignore_index=True)
    print(f"\n{'=' * 60}")
    print(f"✅ Génération terminée !")
    print(f"   Total lignes  : {len(total):,}")
    print(f"   Produits      : {dict(total['product_type'].value_counts())}")
    print(f"   Statuts       : {dict(total['status'].value_counts())}")
    print(f"   Montant moyen : {total['claim_amount_eur'].mean():,.0f} EUR")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()