# Glossaire AXA Group — Data Products & Platforms

> Référentiel des concepts data utilisés au sein de la division GDAI
> (Group Data, AI and Innovation) chez AXA Group Operations.

## Data Product

Un **data product** est un actif data **packagé, gouverné et consommable**
en self-service par les équipes métier. Il combine :

- Les données elles-mêmes (tables, vues, fichiers)
- Les métadonnées (schéma, propriétaire, fraîcheur, qualité)
- Les contrats de service (SLA de fraîcheur, complétude minimale)
- L'API ou interface d'accès (SQL, REST, Power BI)
- La documentation et les exemples d'usage

Chez AXA, chaque data product a un **Data Product Owner** issu du métier,
et est référencé dans le **Data Marketplace** pour être réutilisable
across-entities. Les data products prioritaires couvrent les domaines
**Customer, Claim, Underwriting**.

## Data Mesh

Le **data mesh** est un paradigme d'architecture data introduit par
**Zhamak Dehghani** en 2019. Il repose sur 4 principes fondateurs :

1. **Domain-oriented decentralization** : les domaines métier (et non l'IT
   central) sont propriétaires de leurs données.
2. **Data as a product** : chaque domaine expose ses données comme un
   produit consommable, avec qualité et SLA.
3. **Self-service data platform** : une plateforme commune permet à chaque
   domaine d'être autonome dans la production de ses data products.
4. **Federated computational governance** : la gouvernance est définie au
   niveau Group (standards d'interopérabilité) mais exécutée localement.

Chez AXA, le data mesh permet d'éviter la **centralisation forcée** des
données entité par le Group, tout en garantissant l'**interopérabilité**
nécessaire aux usages transversaux (Customer 360, Claims AI, Compliance).

## Customer 360

Le **Customer 360** est un programme transversal AXA visant à construire
une **vision unifiée du client** à travers tous les contrats, sinistres et
interactions, indépendamment de l'entité ou du canal d'origine. Il s'appuie
sur une **identité fédérée** du client (AXA Customer Master ID) et sur les
data products des domaines Customer, Claim et Underwriting de chaque entité.

## CDAO — Chief Data & Analytics Officer

Le CDAO est le **responsable Data au niveau d'une entité** AXA (AXA France,
AXA Italy, AXA UK, etc.). Il définit la stratégie data locale, anime les
Data Managers et Data Stewards, et reporte au Group Data Office sur la
maturité data de son entité. Les CDAOs participent aux **comités de
gouvernance data** au niveau Group.

## Data Steward

Le **Data Steward** est le **gardien d'un domaine de données**. Il définit
les règles de qualité applicables, valide les anomalies remontées, et est
le point de contact pour toutes les questions sémantiques sur le domaine.
Chez AXA, on a typiquement un Data Steward par domaine (Customer, Claim,
Underwriting) et par entité.

## Data Architecture Lead

Le **Data Architecture Lead** est responsable de la **cohérence de
l'architecture data** au niveau Group. Il définit les standards
d'interopérabilité, les patterns d'intégration entre data products, et
participe aux communautés externes (TOGAF, CC CDQ, DAMA International).

## SecureGPT

**SecureGPT** est la plateforme d'IA générative interne d'AXA, qui offre
un accès **sécurisé et conforme** aux LLM (modèles type GPT-4) pour les
collaborateurs et les applications internes. SecureGPT garantit la
**souveraineté des données** : aucune donnée AXA ne sort de
l'environnement Azure dédié AXA. Tous les copilots et applications
GenAI internes doivent passer par SecureGPT en production.

## Group Data Platform

La **Group Data Platform** est la **plateforme self-service mutualisée**
qui héberge les data products globaux et offre les services communs
(catalogue, monitoring qualité, lineage, accès gouverné). Elle s'appuie
sur Azure Data Services et Databricks.

## Data Marketplace

Le **Data Marketplace** est un **portail interne** permettant aux
collaborateurs AXA de **rechercher, demander accès et consommer** les
data products disponibles. Il joue le rôle d'Amazon-like pour les
données : chaque data product a sa fiche, ses ratings, sa documentation
et ses cas d'usage.

## AI Readiness Score

Le **AI Readiness Score** est un indicateur AXAMesh qui mesure
l'**aptitude d'un jeu de données à supporter des modèles d'IA en
production**. Il est calculé par entité × domaine, sur une échelle 0-100,
en agrégeant les 6 dimensions DAMA (Completeness, Uniqueness, Freshness,
Business Logic, Range, Referential Integrity) avec une pondération
spécifique à l'IA.

Niveaux de readiness :
- **AI-Ready (≥ 90)** : Données prêtes pour déploiement IA en production
- **Mostly Ready (75-89)** : Quelques corrections mineures avant déploiement
- **Needs Work (60-74)** : Améliorations significatives requises
- **Not Ready (< 60)** : Données insuffisantes pour un usage IA fiable