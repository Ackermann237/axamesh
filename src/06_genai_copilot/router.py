"""
AXAMesh - Intelligent Router
============================
Décide quelle stratégie utiliser pour répondre à une question :
  - SQL    : pour les questions sur les KPIs, scores, comptages, FAIL
  - RAG    : pour les questions sur les concepts, frameworks, définitions
  - HYBRID : pour les questions qui combinent les deux

Implémentation hybride : keywords d'abord (rapide, gratuit), fallback LLM
si la classification est ambiguë.
"""

import re
from typing import Literal

Strategy = Literal["sql", "rag", "hybrid"]

# ──────────────────────────────────────────────────────────────
# RÈGLES PAR MOTS-CLÉS
# ──────────────────────────────────────────────────────────────

# Termes qui indiquent une question quantitative (→ SQL)
SQL_KEYWORDS = [
    # Comptage
    "combien", "nombre de", "count", "total", "quantité",
    # Comparaison quantitative
    "top ", "meilleur", "pire", "plus haut", "plus bas",
    "compare", "comparer", "comparaison", "versus", "vs ",
    # Métriques nommées
    "score", "kpi", "métriques", "metrics",
    "pass rate", "fail rate", "taux", "pourcentage", "%",
    "blockers", "blocker", "fail", "warn", "pass",
    # Entités spécifiques
    "axa_france", "axa_uk", "axa_italy",
    # Domaines spécifiques
    "customer", "claim", "claims", "underwriting", "policies",
    # Verbes d'agrégation
    "liste les", "donne-moi les", "trouve les", "show me",
]

# Termes qui indiquent une question conceptuelle (→ RAG)
RAG_KEYWORDS = [
    # Définitions
    "qu'est-ce", "qu'est-ce que", "c'est quoi", "définition", "définis",
    "what is", "définir", "expliquer", "explique",
    # Concepts data
    "data mesh", "data product", "data marketplace", "customer 360",
    "data steward", "cdao", "dama", "dmbok", "data governance",
    "secure gpt", "securegpt", "data architecture",
    # Frameworks
    "framework", "principe", "principes", "concept", "concepts",
    "méthodologie", "methodology", "best practice", "bonne pratique",
    # Théorie
    "pourquoi", "comment ça marche", "à quoi sert",
    "philosophie", "approche",
]

# Termes qui indiquent une question hybride (les deux)
HYBRID_INDICATORS = [
    "et explique", "et donne le contexte", "avec le framework",
    "selon dama", "selon le framework", "et la théorie",
]


def keyword_classify(question: str) -> tuple[Strategy, float]:
    """Classification par mots-clés. Retourne (strategy, confiance)."""
    q = question.lower()

    sql_hits = sum(1 for kw in SQL_KEYWORDS if kw in q)
    rag_hits = sum(1 for kw in RAG_KEYWORDS if kw in q)
    hybrid_hits = sum(1 for kw in HYBRID_INDICATORS if kw in q)

    # Hybride si indicateurs explicites OU les deux types présents
    if hybrid_hits > 0 or (sql_hits >= 1 and rag_hits >= 1):
        return "hybrid", 0.9

    if sql_hits > rag_hits:
        confidence = min(0.5 + (sql_hits * 0.15), 1.0)
        return "sql", confidence

    if rag_hits > sql_hits:
        confidence = min(0.5 + (rag_hits * 0.15), 1.0)
        return "rag", confidence

    # Aucun indice clair : confiance faible, on déclenchera le fallback LLM
    return "rag", 0.3


# ──────────────────────────────────────────────────────────────
# FALLBACK LLM (si la confiance keywords est trop faible)
# ──────────────────────────────────────────────────────────────

LLM_ROUTER_PROMPT = """Tu es un classificateur de questions pour un copilot
data quality d'AXA. Tu dois classifier la question en exactement UN des
3 modes suivants :

- "sql"    : question quantitative, sur les KPIs, scores, comptages,
             données chiffrées (ex: "combien de FAIL ?", "score de axa_uk ?")
- "rag"    : question conceptuelle, théorique, sur les frameworks, définitions
             (ex: "c'est quoi data mesh ?", "que dit DAMA ?")
- "hybrid" : combine les deux (ex: "compare les entités et explique le framework")

Réponds UNIQUEMENT par un seul mot : "sql", "rag" ou "hybrid".

Question : {question}

Mode :"""


class IntelligentRouter:
    """Routeur hybride : keywords d'abord, fallback LLM si ambigu."""

    def __init__(self, llm_provider, confidence_threshold: float = 0.5):
        self.llm = llm_provider
        self.threshold = confidence_threshold

    def route(self, question: str) -> dict:
        """Classifie la question et retourne la stratégie."""
        # Étape 1 : tentative par mots-clés (gratuit, rapide)
        strategy, confidence = keyword_classify(question)

        method = "keywords"

        # Étape 2 : fallback LLM si la confiance est faible
        if confidence < self.threshold:
            try:
                llm_response = self.llm.chat(
                    system_prompt="Tu es un classificateur de questions.",
                    user_message=LLM_ROUTER_PROMPT.format(question=question),
                ).strip().lower()
                # Extraction du mot-clé dans la réponse
                if "hybrid" in llm_response:
                    strategy = "hybrid"
                elif "sql" in llm_response:
                    strategy = "sql"
                elif "rag" in llm_response:
                    strategy = "rag"
                method = "llm"
                confidence = 0.85  # confiance arbitraire pour le LLM
            except Exception as e:
                # En cas d'erreur, on garde le résultat des keywords
                method = f"keywords (LLM fallback failed: {e})"

        return {
            "strategy": strategy,
            "confidence": round(confidence, 2),
            "method": method,
        }