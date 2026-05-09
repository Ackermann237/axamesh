# Data Mesh — Les 4 Principes Fondateurs

> Synthèse du livre "Data Mesh: Delivering Data-Driven Value at Scale"
> de Zhamak Dehghani (O'Reilly, 2022).
> Mise en application au sein du programme AXAMesh.

## Contexte : pourquoi le data mesh ?

Les architectures data traditionnelles reposent sur un **data lake centralisé**
géré par une équipe IT centrale. Ce modèle atteint ses limites dès que
l'organisation grandit :

- Goulot d'étranglement de l'équipe centrale
- Méconnaissance du métier par les data engineers centraux
- Friction permanente entre métiers et IT
- Difficulté à innover et à délivrer de la valeur rapidement

Pour une organisation comme **AXA** (54 pays, 17 entités, 105M clients),
la centralisation forcée des données est techniquement **impossible** et
**indésirable**. Le data mesh propose une alternative basée sur la
**décentralisation gouvernée**.

## Principe 1 — Domain-Oriented Decentralized Data Ownership

> *"Les données appartiennent aux domaines métier, pas à l'IT central."*

Chaque **domaine métier** (Customer, Claim, Underwriting, Distribution,
Compliance) est **propriétaire de ses données**. Le domaine définit les
schémas, les règles de qualité, les SLA et expose ses données comme un
produit consommable par les autres domaines.

**Application AXAMesh :**
- AXA France, AXA UK et AXA Italy gèrent leurs propres données customer/claim/underwriting
- Le Group Data Office définit les **standards** mais n'opère pas les pipelines
- Chaque entité a son propre Data Steward par domaine

## Principe 2 — Data as a Product

> *"Les données ne sont plus un sous-produit des applications : elles
> sont le produit."*

Chaque domaine expose ses données comme un **produit** avec :

- **Discoverability** : indexé dans le Data Marketplace
- **Addressability** : un identifiant unique pour y accéder
- **Trustworthiness** : SLA explicites de qualité et fraîcheur
- **Self-describing semantics** : schéma et documentation accessibles
- **Interoperability** : conforme aux standards Group
- **Native security** : permissions granulaires intégrées

**Application AXAMesh :**
- Chaque entité publie ses data products dans la Group Data Platform
- Le AI Readiness Score est exposé comme métadonnée du data product
- La Marketplace permet aux usages transversaux (Customer 360, Compliance)
  de consommer ces data products en self-service

## Principe 3 — Self-Serve Data Infrastructure as a Platform

> *"La plateforme abstrait la complexité technique pour libérer les domaines."*

Une équipe **plateforme** centrale fournit les outils et l'infrastructure
**partagés** par tous les domaines :

- Stockage scalable (Bronze / Silver / Gold)
- Outils de pipeline (Databricks, Spark)
- Catalogue et lineage (Purview, DataHub)
- Monitoring qualité (frameworks DQ)
- Accès LLM gouverné (SecureGPT)
- CI/CD pour data products

**Application AXAMesh :**
- La Group Data Platform fournit ces services aux 17 entités
- Le framework AXAMesh (config-driven YAML) est un exemple d'outil
  self-service pour la qualité
- ChromaDB / Azure AI Search est la brique self-service pour le RAG

## Principe 4 — Federated Computational Governance

> *"Une gouvernance fédérée : standards globaux, exécution locale."*

La gouvernance n'est ni totalement centralisée, ni totalement décentralisée.
Un **comité fédéré** (composé du Group Data Office et des CDAOs locaux)
définit :

- Les **standards d'interopérabilité** (formats, identifiants, vocabulaires)
- Les **règles globales** (sécurité, conformité GDPR, Solvency II)
- Les **KPIs Group** (data quality, AI readiness, taux d'adoption)

L'**exécution** de ces standards est portée par chaque entité de manière
autonome, et **monitorée** au niveau Group via des dashboards.

**Application AXAMesh :**
- Le YAML `quality_rules.yaml` distingue `group_mandatory` vs `domain_specific`
  vs `entity_local` — c'est précisément la gouvernance fédérée mise en code
- Le dashboard PowerBI Group-level reporte la maturité de chaque entité
  au Management Committee
- Les CDAOs participent à la définition des règles `group_mandatory`

## Pourquoi le data mesh est-il critique pour l'IA chez AXA ?

L'IA en assurance nécessite des données **transversales** (un client peut
avoir une auto en France et une santé en UK) mais sans casser
l'**autonomie locale**. Le data mesh permet :

1. **Faster time-to-value** : chaque domaine livre indépendamment
2. **Quality at the source** : la qualité est gérée par ceux qui connaissent
   le métier
3. **Scalable AI** : les modèles consomment des data products gouvernés,
   pas des datasets ad-hoc
4. **Compliance by design** : la gouvernance fédérée intègre GDPR, Solvency II
5. **Interoperability** : les data products parlent le même langage Group

## Anti-patterns à éviter

- **Mesh-washing** : appeler "data mesh" un data lake centralisé non décentralisé
- **No platform** : décentraliser sans plateforme partagée = chaos
- **No governance** : autonomie totale sans standards = silos
- **Tech-only** : ignorer la dimension organisationnelle (Data Stewards, CDAOs)