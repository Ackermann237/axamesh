# 🎯 AXAMesh — Data Quality & AI Readiness Hub

> Projet personnel aligné sur l'offre **Data Analyst Apprentice**
> AXA Group Operations · Group Data, AI and Innovation (GDAI)
> Data Products & Platforms · Paris

---

## 📋 Le contexte de l'offre AXA

> *"As a Data Analyst Apprentice, you will work closely with our Data Quality
> Lead, to support various business initiatives of AXA, notably Compliance,
> Growth, and the scaling of AI solutions across the Group (Contact Center,
> **Claims, Underwriting**). You will contribute to the definition and the
> delivery of the **dashboard to be reported at a Group level**, to report on
> the **data quality & readiness of Entities**."*

L'offre demande explicitement :
- ✅ Un **dashboard data quality & readiness** au niveau Group
- ✅ Couverture des 3 domaines : **Customer, Claim, Underwriting**
- ✅ Compréhension de **GenAI**, **unstructured data**, **data products**,
  **data mesh**, **data quality frameworks**
- ✅ Compétences **PowerBI**, **SQL**, **Python**, **data modelling**

---

## 🏗️ Architecture du projet

AXAMesh est une **simulation complète de l'écosystème data AXA**, conçue
pour démontrer la maîtrise de toutes les compétences attendues sur ce poste.

```
┌─────────────────────────────────────────────────────────────────┐
│                      DASHBOARD POWER BI                          │
│   Group Overview │ Data Quality │ AI & Data Readiness            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SQL SERVER — base axamesh                       │
│  schéma gold (vues consolidées Group-level)                      │
│  schéma silver (données nettoyées)                               │
│  schéma bronze (CSV bruts par entité)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINES PYTHON                              │
│   bronze → silver → gold + Quality Framework (config-driven)     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              GENAI COPILOT (Architecture Hybride)                │
│                                                                  │
│   Question utilisateur                                           │
│        ↓                                                         │
│   [Router]  ── keywords + LLM fallback                           │
│        ↓                                                         │
│   ┌────┼────┐                                                    │
│   ↓    ↓    ↓                                                    │
│  SQL  RAG  HYBRID                                                │
│   │    │    │                                                    │
│   └────┼────┘                                                    │
│        ↓                                                         │
│   [LLM] ── Groq / Azure / Local                                  │
│        ↓                                                         │
│   Réponse finale                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 Structure du projet

```
axamesh/
├── config/
│   ├── entities.yaml              # Config des entités AXA fictives
│   └── quality_rules.yaml         # Règles qualité (config-driven)
├── data/
│   ├── bronze/                    # CSV bruts par entité
│   ├── silver/                    # Parquet nettoyés
│   ├── gold/                      # Quality reports + AI readiness
│   └── vector_db/                 # ChromaDB (embeddings)
├── src/
│   ├── 01_ingestion/              # Génération données fictives + ingestion
│   ├── 02_pipelines/              # Bronze → Silver → Gold
│   ├── 03_quality_framework/      # Runner DAMA + persistence
│   ├── 04_marketplace/            # (placeholder)
│   ├── 05_customer_360/           # (placeholder)
│   └── 06_genai_copilot/          # ⭐ Copilot hybride SQL + RAG
│       ├── ai_readiness_scorer.py
│       ├── copilot_engine.py      # Orchestrateur principal
│       ├── sql_provider.py        # Text-to-SQL
│       ├── rag_provider.py        # RAG ChromaDB
│       ├── router.py              # Router intelligent
│       ├── app.py                 # Streamlit UI
│       └── knowledge_base/        # Docs unstructured pour le RAG
│           ├── dama_dmbok.md
│           ├── axa_data_glossary.md
│           └── data_mesh_principles.md
└── powerbi/
    └── axamesh_dashboard.pbix     # Dashboard Power BI
```

---

## 🎯 Alignement précis avec l'offre

| Compétence demandée | Comment AXAMesh y répond |
|---|---|
| **Dashboard Group-level** | Power BI 3 pages : Group Overview, Data Quality, AI Readiness |
| **Data quality** | Framework DAMA-DMBOK config-driven (60 contrôles, 6 dimensions) |
| **Data readiness** | AI Readiness Score pondéré par domaine et entité |
| **Customer / Claim / Underwriting** | 3 domaines couverts dans tout le pipeline |
| **PowerBI** | 3 pages, 4 KPIs, mesures DAX, colonne calculée `domain_business` |
| **Data modelling** | Schéma Medallion Bronze/Silver/Gold + star schema PowerBI |
| **SQL** | SQL Server `axamesh` + Text-to-SQL généré dynamiquement |
| **Python** | Pipelines, Quality Runner, Copilot, Streamlit |
| **GenAI** | Copilot hybride avec LLM (Groq/Azure SecureGPT) |
| **Unstructured data + GenAI** | RAG sur docs DAMA, glossaire AXA, data mesh |
| **Data products** | Vues `gold.*` packagées comme produits, glossaire dédié |
| **Data mesh** | Knowledge base + `quality_rules.yaml` (federated governance) |
| **Data quality frameworks** | DAMA-DMBOK implémenté en YAML + indexé dans le RAG |
| **Réunions CDAOs / Data Managers** | Le copilot est leur interface naturelle |

---

## 🚀 Démo en 3 commandes

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Pipeline data (one-shot)

```bash
python src/01_ingestion/generate_data.py
python src/02_pipelines/bronze_to_silver.py
python src/02_pipelines/build_gold.py
python src/03_quality_framework/quality_runner.py
python src/06_genai_copilot/ai_readiness_scorer.py
```

### 3. Lancement du Copilot

```bash
# Configurer la clé Groq (gratuite)
export GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx

# Lancer l'interface
streamlit run src/06_genai_copilot/app.py
```

---

## 🎤 Le pitch (3 minutes)

> *"AXAMesh est un projet personnel que j'ai construit pour démontrer ma
> capacité à délivrer ce que demande l'offre Data Analyst Apprentice.*
>
> *J'ai simulé 3 entités AXA (France, UK, Italy) avec leurs données
> Customer/Claims/Policies sur les 3 domaines prioritaires de l'offre.
> J'ai construit une **architecture Medallion sur SQL Server**, un
> **framework de Data Quality config-driven** inspiré de DAMA-DMBOK avec
> 60 contrôles couvrant les 6 dimensions, et un **dashboard Power BI 3 pages**
> aligné sur le besoin Management Committee.*
>
> *Ma valeur ajoutée principale, c'est le **GenAI Copilot hybride** :
> j'ai conçu un assistant conversationnel pour les CDAOs et Data Managers
> qui combine **Text-to-SQL** sur la base axamesh — la même que celle qui
> alimente Power BI — et **RAG avec ChromaDB** sur une knowledge base
> couvrant DAMA, le glossaire AXA et les principes data mesh. Un **routeur
> intelligent** détermine la bonne stratégie pour chaque question.*
>
> *Cette architecture est volontairement **agnostique du fournisseur LLM** :
> en démo j'utilise Groq pour la rapidité et la gratuité, mais en production
> chez AXA ça basculerait vers **SecureGPT** sur Azure OpenAI sans toucher
> au code applicatif — c'est exactement le pattern Strategy attendu pour
> un produit data qui doit respecter la souveraineté."*

---

## 🔧 Stack technique

| Composant | Technologie |
|---|---|
| **Stockage analytique** | SQL Server (architecture Medallion) |
| **Pipelines** | Python (pandas, SQLAlchemy) |
| **Visualisation** | Power BI |
| **Quality Framework** | YAML config-driven, SQLite logs |
| **LLM (démo)** | Groq Llama 3.3 70B |
| **LLM (prod cible)** | Azure OpenAI / SecureGPT |
| **Embeddings** | sentence-transformers (multilingue) |
| **Vector DB (démo)** | ChromaDB |
| **Vector DB (prod cible)** | Azure AI Search |
| **UI Copilot** | Streamlit |

---

## 📊 Métriques actuelles (démo)

- **60 contrôles qualité** exécutés sur 3 entités × 3 domaines
- **6 dimensions** DAMA-DMBOK couvertes
- **Pass Rate** : 33.3 %
- **AI Readiness Score Group** : 47.5 %
- **23 blockers critiques** (FAIL) à remédier en priorité

---

## 🧭 Roadmap

- [x] Architecture Medallion (Bronze/Silver/Gold)
- [x] Framework Data Quality DAMA-DMBOK
- [x] Dashboard Power BI 3 pages
- [x] AI Readiness Scorer
- [x] Copilot hybride SQL + RAG
- [x] Knowledge base unstructured (DAMA, glossaire, data mesh)
- [ ] Data Marketplace (search & request access)
- [ ] Customer 360 (cross-entity)
- [ ] Tests automatisés (pytest)
- [ ] CI/CD GitHub Actions

---

**Contact** : projet personnel pour candidature AXA Data Analyst Apprentice 2026