# DAMA-DMBOK : Data Quality Framework

> Source : Data Management Body of Knowledge (DAMA International).
> Adapté au contexte AXA Group Operations — Data Products & Platforms.

## Définition de la qualité des données

La qualité des données est la **mesure dans laquelle les données sont fiables,
précises, complètes, cohérentes et utilisables** pour les usages métier auxquels
elles sont destinées. Dans le secteur de l'assurance, une mauvaise qualité de
données impacte directement la souscription (underwriting), la gestion des
sinistres (claims) et la conformité réglementaire (Solvency II, GDPR).

## Les 6 dimensions clés de la qualité des données

### 1. Completeness (Complétude)

La complétude mesure la **proportion de données présentes** par rapport aux
données attendues. Une donnée customer sans email ou sans date de naissance
est incomplète. Pour les modèles d'IA, la complétude est la dimension la plus
critique : un modèle ne peut pas inférer correctement à partir de champs
manquants. **Seuil critique recommandé : >95% de complétude pour les champs
obligatoires.**

### 2. Uniqueness (Unicité)

L'unicité garantit qu'une **entité métier n'existe qu'en un seul exemplaire**
dans le système. Les doublons clients génèrent des biais dans les modèles d'IA
(sur-apprentissage), faussent les KPIs commerciaux et dégradent l'expérience
client (envois multiples). En assurance, l'unicité est cruciale pour le
rapprochement des polices d'un même assuré.

### 3. Freshness (Fraîcheur)

La fraîcheur mesure **l'âge des données** par rapport à la réalité métier
qu'elles représentent. Des données périmées génèrent des prédictions obsolètes.
**Pour le Contact Center et la souscription temps réel, la fraîcheur exigée
est < 24h.** Pour les analyses tactiques, < 7 jours est acceptable.

### 4. Business Logic (Cohérence métier)

La cohérence métier vérifie que les données respectent les **règles de gestion**
de l'entreprise. Exemple : une date de déclaration de sinistre ne peut pas
être antérieure à la date du sinistre lui-même. Le pays du client doit
correspondre à l'entité d'origine. Ces règles sont définies par les
Data Stewards en collaboration avec les CDAOs locaux.

### 5. Range (Plages valides)

Les valeurs doivent rester dans des **plages plausibles**. Une prime annuelle
négative, un montant de sinistre supérieur à plusieurs millions d'euros sans
flag spécial, une date de naissance après aujourd'hui sont des anomalies
détectables par contrôle de plage. Les outliers sont particulièrement
problématiques pour l'entraînement de modèles ML.

### 6. Referential Integrity (Intégrité référentielle)

L'intégrité référentielle garantit que **les liens entre entités sont valides**.
Toute police d'assurance doit pointer vers un client existant. Tout sinistre
doit référencer une police active à la date du sinistre. Une rupture de
l'intégrité référentielle casse les jointures et appauvrit le contexte des
modèles IA.

## Niveaux de criticité des contrôles

DAMA distingue trois niveaux de contrôles à appliquer :

- **Group Mandatory** : règles imposées par le Group à toutes les entités
  (exemple : unicité du customer_id). Aucune dérogation possible.
- **Domain Specific** : règles propres à un domaine métier (Customer, Claim,
  Underwriting). Définies par les Data Stewards du domaine.
- **Entity Local** : règles spécifiques à une entité locale, liées aux
  réglementations nationales (ex: format SIRET pour la France, NIF pour
  l'Italie).

## Lien avec l'AI Readiness

L'AI Readiness est un concept dérivé de la data quality : il mesure dans
quelle mesure un jeu de données est **apte à supporter des modèles d'IA en
production**. Le score AI Readiness est un agrégat pondéré des 6 dimensions
ci-dessus, avec une pondération plus forte sur Completeness (30%) et
Uniqueness (20%) car ces deux dimensions ont l'impact le plus direct sur
les performances des modèles.

## Bonnes pratiques de remédiation

1. **Prioriser les FAIL** sur les domaines critiques (Customer, Claims, Underwriting)
2. **Documenter chaque règle** dans un référentiel central (Data Catalog)
3. **Automatiser les contrôles** via un framework config-driven (YAML/JSON)
4. **Tracer les exécutions** dans un log temporel pour analyse de tendances
5. **Impliquer les Data Stewards** des entités dans la définition des règles
6. **Aligner avec les frameworks externes** : DAMA-DMBOK, ISO 8000, CC CDQ