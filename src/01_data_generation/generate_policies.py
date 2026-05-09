"""
AXAMesh - Générateur de données Policies (Polices d'assurance) synthétiques
"""

import pandas as pd
import numpy as np
import yaml
import uuid
import random
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
POLICY_STATUSES = ["ACTIVE", "EXPIRED", "CANCELLED", "SUSPENDED"]

PREMIUM_RANGES = {
    "AUTO":      (400, 3000),
    "HOME":      (300, 2500),
    "HEALTH":    (600, 5000),
    "LIFE":      (500, 8000),
    "TRAVEL":    (50, 500),
    "LIABILITY": (200, 2000),
}


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)))


def add_years(d: date, years: int) -> date:
    """Ajoute N années à une date en gérant le 29 février."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def generate_policies(entity_id: str, entity_config: dict) -> pd.DataFrame:
    n = entity_config["nb_policies"]
    fx = CONFIG["fx_rates"].get(entity_config["currency"], 1.0)

    print(f"\n🏢 Génération Policies — {entity_config['name']} ({n} polices)")

    records = []
    today = date.today()

    for _ in range(n):
        product = random.choice(PRODUCT_TYPES)
        start_date = random_date(date(2015, 1, 1), today)

        # Durée entre 1 et 5 ans — avec gestion du 29 février
        duration_years = random.choices([1, 2, 3, 5], weights=[0.5, 0.2, 0.2, 0.1])[0]
        end_date = add_years(start_date, duration_years)

        # Statut logique
        if end_date < today:
            status = random.choices(
                ["EXPIRED", "CANCELLED"],
                weights=[0.80, 0.20]
            )[0]
        else:
            status = random.choices(
                ["ACTIVE", "SUSPENDED"],
                weights=[0.92, 0.08]
            )[0]

        low, high = PREMIUM_RANGES[product]
        annual_premium = round(random.uniform(low, high), 2)
        annual_premium_eur = round(annual_premium * fx, 2)

        records.append({
            "policy_id":          str(uuid.uuid4()),
            "customer_id":        str(uuid.uuid4()),
            "entity":             entity_id,
            "product_type":       product,
            "start_date":         start_date,
            "end_date":           end_date,
            "annual_premium":     annual_premium,
            "annual_premium_eur": annual_premium_eur,
            "currency":           entity_config["currency"],
            "status":             status,
            "payment_frequency":  random.choice(["MONTHLY", "QUARTERLY", "ANNUAL"]),
            "_ingested_at":       datetime.utcnow(),
        })

    df = pd.DataFrame(records).reset_index(drop=True)
    print(f"  ✅ {len(df)} polices générées (données propres)")

    # ---- Injection erreurs ----
    print("  💉 Injection des erreurs qualité...")

    # 1. Primes négatives (1%)
    n_neg = max(1, int(len(df) * 0.01))
    neg_idx = df.sample(n=n_neg, random_state=RANDOM_SEED).index.tolist()
    df.loc[neg_idx, "annual_premium"]     = df.loc[neg_idx, "annual_premium"].apply(lambda x: -abs(x))
    df.loc[neg_idx, "annual_premium_eur"] = df.loc[neg_idx, "annual_premium_eur"].apply(lambda x: -abs(x))
    print(f"  💉 Primes négatives : {n_neg} lignes")

    # 2. Dates incohérentes : end_date <= start_date (1%)
    n_bad = max(1, int(len(df) * 0.01))
    bad_date_idx = df.sample(n=n_bad, random_state=RANDOM_SEED + 1).index.tolist()
    df.loc[bad_date_idx, "end_date"] = df.loc[bad_date_idx, "start_date"].apply(
        lambda d: d - timedelta(days=1)
    )
    print(f"  💉 Dates incohérentes : {n_bad} lignes")

    # 3. Types produits invalides (0.5%)
    n_bad_type = max(1, int(len(df) * 0.005))
    bad_type_idx = df.sample(n=n_bad_type, random_state=RANDOM_SEED + 2).index.tolist()
    df.loc[bad_type_idx, "product_type"] = "UNKNOWN_PRODUCT"
    print(f"  💉 Types invalides : {n_bad_type} lignes")

    # 4. NULL sur policy_id (0.2%)
    n_null = max(1, int(len(df) * 0.002))
    null_id_idx = df.sample(n=n_null, random_state=RANDOM_SEED + 3).index.tolist()
    df.loc[null_id_idx, "policy_id"] = None
    print(f"  💉 NULL policy_id : {n_null} lignes")

    print(f"  📊 Dataset final : {len(df)} lignes")
    return df


def main():
    print("=" * 60)
    print("AXAMesh — Génération des données Policies")
    print("=" * 60)

    all_dfs = []

    for entity_id, entity_config in CONFIG["entities"].items():
        df = generate_policies(entity_id, entity_config)

        output_dir = OUTPUT_BASE / entity_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "policies.csv"
        df.to_csv(output_path, index=False, encoding="utf-8")
        print(f"  💾 Sauvegardé : {output_path}")
        all_dfs.append(df)

    total = pd.concat(all_dfs, ignore_index=True)
    print(f"\n{'=' * 60}")
    print(f"✅ Génération terminée !")
    print(f"   Total lignes    : {len(total):,}")
    print(f"   Produits        : {dict(total['product_type'].value_counts())}")
    print(f"   Statuts         : {dict(total['status'].value_counts())}")
    print(f"   Prime moy. EUR  : {total['annual_premium_eur'].mean():,.0f} EUR")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()