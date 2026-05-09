"""
AXAMesh - Simulation de runs historiques pour la courbe de tendance
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime, timezone, timedelta

SERVER   = "AMOUGOU\\SQLEXPRESS"
DATABASE = "axamesh"
DRIVER   = "ODBC Driver 17 for SQL Server"

conn_str = (
    f"mssql+pyodbc://@{SERVER}/{DATABASE}"
    f"?driver={DRIVER.replace(' ', '+')}"
    f"&trusted_connection=yes"
    f"&TrustServerCertificate=yes"
)
engine = create_engine(conn_str, fast_executemany=True)

# Lecture du run actuel
df = pd.read_sql("SELECT * FROM gold.data_quality_log", engine)
print(f"✅ {len(df)} lignes lues depuis SQL Server")

# Génération de 3 runs historiques
historical_runs = [
    ("RUN_APR_01", 60),
    ("RUN_APR_15", 45),
    ("RUN_MAY_01", 30),
]

runs = []
for i, (run_id, days_ago) in enumerate(historical_runs):
    fake = df.copy()
    fake["run_id"]      = run_id
    fake["executed_at"] = (
        datetime.now(timezone.utc) - timedelta(days=days_ago)
    ).isoformat()

    # Variation aléatoire des statuts
    np.random.seed(i * 10)
    mask = np.random.random(len(fake)) < 0.15
    fake.loc[mask, "status"] = np.random.choice(
        ["PASS", "WARN", "FAIL"],
        mask.sum(),
        p=[0.3, 0.3, 0.4]
    )
    runs.append(fake)
    print(f"  📅 {run_id} : {len(fake)} lignes générées")

all_runs = pd.concat(runs, ignore_index=True)

# Insertion dans SQL Server
all_runs.to_sql(
    "data_quality_log",
    engine,
    schema="gold",
    if_exists="append",
    index=False,
    chunksize=500,
)

print(f"\n✅ {len(all_runs)} lignes ajoutées — 3 runs historiques créés")
print(f"   Runs disponibles : RUN_APR_01 · RUN_APR_15 · RUN_MAY_01 · + run actuel")