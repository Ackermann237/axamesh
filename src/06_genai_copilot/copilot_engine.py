"""
AXAMesh - GenAI Copilot Engine (v2 — Architecture Hybride)
==========================================================

Copilot conversationnel pour les CDAOs, Data Managers et le Management
Committee d'AXA. Aligné sur l'offre Data Analyst Apprentice (GDAI).

Architecture hybride :

    Question
        │
        ▼
    [Router]  ── keywords + LLM fallback
        │
   ┌────┼────┐
   ▼    ▼    ▼
  SQL  RAG  HYBRID         ← récupère le contexte
   │    │    │
   └────┼────┘
        ▼
    [LLM]   ── reformule en français naturel
        │
        ▼
     Réponse

Providers LLM supportés (Strategy Pattern) :
  - GroqProvider  (gratuit, rapide — démo)
  - AzureProvider (production AXA — SecureGPT)
  - LocalProvider (offline — fallback)
"""

import os
import sys
import pandas as pd
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional

# Permet d'importer les modules du même dossier
sys.path.insert(0, str(Path(__file__).parent))

from sql_provider import SQLProvider
from rag_provider import RAGProvider
from router import IntelligentRouter

ROOT      = Path(__file__).parent.parent.parent
GOLD_BASE = ROOT / "data" / "gold"


# ══════════════════════════════════════════════════════════════
# LLM PROVIDERS (Strategy Pattern)
# ══════════════════════════════════════════════════════════════

class LLMProvider(ABC):
    @abstractmethod
    def chat(self, system_prompt: str, user_message: str) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class GroqProvider(LLMProvider):
    """Groq — LPU dédiée aux LLM, gratuit, ~500 tokens/sec."""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model

    @property
    def name(self) -> str:
        return f"Groq ({self.model})"

    def chat(self, system_prompt: str, user_message: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content


class AzureProvider(LLMProvider):
    """Azure OpenAI — utilisé par AXA SecureGPT en production."""

    def __init__(self, api_key: str, endpoint: str, deployment: str):
        from openai import AzureOpenAI
        self.client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=endpoint,
        )
        self.deployment = deployment

    @property
    def name(self) -> str:
        return f"Azure OpenAI ({self.deployment})"

    def chat(self, system_prompt: str, user_message: str) -> str:
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content


class LocalProvider(LLMProvider):
    """Fallback offline — sans LLM."""

    @property
    def name(self) -> str:
        return "Local (sans LLM, mode dégradé)"

    def chat(self, system_prompt: str, user_message: str) -> str:
        return (
            "🔧 Mode local actif (aucune clé API détectée).\n\n"
            "Pour activer le copilot conversationnel :\n"
            "  - Démo : configurez GROQ_API_KEY (gratuit sur console.groq.com)\n"
            "  - Production AXA : AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT\n\n"
            "Contexte data récupéré :\n\n" + user_message[:800] + "..."
        )


def get_llm_provider() -> LLMProvider:
    """Sélectionne automatiquement le bon provider LLM."""
    if os.getenv("GROQ_API_KEY"):
        return GroqProvider(api_key=os.getenv("GROQ_API_KEY"))
    if os.getenv("AZURE_OPENAI_API_KEY"):
        return AzureProvider(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
        )
    return LocalProvider()


# ══════════════════════════════════════════════════════════════
# COPILOT ENGINE (orchestrateur principal)
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Tu es le Copilot Data Quality d'AXA Group, conçu pour
les CDAOs, Data Managers et membres du Management Committee.

Contexte AXA :
- AXA déploie des solutions IA à grande échelle (Contact Center, Claims, Underwriting)
- 3 domaines métier prioritaires : Customer, Claim, Underwriting
- 3 entités fictives : axa_france, axa_uk, axa_italy
- Approche Data Mesh : autonomie des entités + standards Group

Règles de réponse :
1. Réponds en français, ton professionnel et concis (2-5 phrases max)
2. Appuie-toi UNIQUEMENT sur les données et documents fournis dans le contexte
3. Quand tu donnes un chiffre, précise toujours l'entité/domaine concerné
4. Si tu cites une source du RAG, mentionne-la (ex: "Selon DAMA-DMBOK...")
5. Termine par 1-3 recommandations actionnables si pertinent
6. Si l'information n'est pas dans le contexte, dis-le clairement
7. Utilise des emojis avec parcimonie (🟢 🟡 🔴 pour les statuts)
"""


class DataQualityCopilot:
    """Copilot conversationnel hybride SQL + RAG."""

    def __init__(self, llm: Optional[LLMProvider] = None,
                 enable_sql: bool = True, enable_rag: bool = True):
        self.llm = llm or get_llm_provider()
        self.router = IntelligentRouter(self.llm)
        self.sql = SQLProvider(self.llm) if enable_sql else None
        self.rag = RAGProvider() if enable_rag else None

    @property
    def info(self) -> dict:
        return {
            "llm": self.llm.name,
            "sql": self.sql.name if self.sql else "disabled",
            "rag": self.rag.name if self.rag else "disabled",
        }

    # ──────────────────────────────────────────────────────────
    # PIPELINE PRINCIPAL
    # ──────────────────────────────────────────────────────────

    def ask(self, question: str) -> dict:
        """Pipeline complet : route → fetch context → reformulate."""
        # 1. Routage
        routing = self.router.route(question)
        strategy = routing["strategy"]

        # 2. Récupération du contexte
        context_parts = []
        sources = []
        sql_query = None
        sql_data = None

        if strategy in ("sql", "hybrid") and self.sql:
            sql_result = self.sql.query(question)
            sql_query = sql_result.get("sql")
            sql_data = sql_result.get("data")

            # Priorité aux données si disponibles
            if sql_data is not None and not sql_data.empty:
                q_lower = question.lower()

                # Filtre sur le dernier run uniquement (unicité comme PowerBI)
                if "run_id" in sql_data.columns and "executed_at" in sql_data.columns:
                    last_run = sql_data.loc[sql_data["executed_at"].idxmax(), "run_id"]
                    sql_data = sql_data[sql_data["run_id"] == last_run].copy()

                # Calculs agrégés pré-faits pour éviter les hallucinations
                aggregates = ""
                if "status" in sql_data.columns:
                    total   = len(sql_data)
                    n_pass  = (sql_data["status"] == "PASS").sum()
                    n_fail  = (sql_data["status"] == "FAIL").sum()
                    n_warn  = (sql_data["status"] == "WARN").sum()
                    pass_rt = round(100 * n_pass / total, 1) if total > 0 else 0
                    aggregates = (
                        f"STATISTIQUES CALCULÉES (source directe) :\n"
                        f"  - Total contrôles : {total}\n"
                        f"  - PASS : {n_pass} ({pass_rt}%)\n"
                        f"  - FAIL : {n_fail} ({round(100*n_fail/total,1)}%)\n"
                        f"  - WARN : {n_warn} ({round(100*n_warn/total,1)}%)\n"
                        f"  - Pass Rate Global : {pass_rt}%\n"
                    )
                    if "entity" in sql_data.columns:
                        aggregates += "\nPAR ENTITÉ :\n"
                        for entity, grp in sql_data.groupby("entity"):
                            t = len(grp)
                            p = (grp["status"]=="PASS").sum()
                            f_ = (grp["status"]=="FAIL").sum()
                            w = (grp["status"]=="WARN").sum()
                            aggregates += f"  - {entity}: {f_} FAIL, {p} PASS, {w} WARN (pass rate: {round(100*p/t,1)}%)\n"

                # Filtre intelligent sur le détail (seulement si question ciblée)
                df_filtered = sql_data.copy()
                is_aggregate_question = any(w in q_lower for w in [
                    "rate", "taux", "pourcentage", "%", "ratio", "global",
                    "total", "combien", "comparer", "compare"
                ])

                if not is_aggregate_question:
                    if "entity" in df_filtered.columns:
                        for entity in ["axa_france", "axa_uk", "axa_italy"]:
                            if entity in q_lower:
                                df_filtered = df_filtered[df_filtered["entity"] == entity]
                                break
                    if "status" in df_filtered.columns:
                        if "fail" in q_lower:
                            df_filtered = df_filtered[df_filtered["status"] == "FAIL"]
                        elif "warn" in q_lower:
                            df_filtered = df_filtered[df_filtered["status"] == "WARN"]
                    if "domain" in df_filtered.columns:
                        for domain in ["customer", "claims", "policies"]:
                            if domain in q_lower or (domain == "policies" and "underwriting" in q_lower):
                                df_filtered = df_filtered[df_filtered["domain"] == domain]
                                break

                preview = df_filtered.head(15).to_string(index=False)
                source_label = "SQL Server axamesh"
                context_parts.append(
                    f"=== DONNÉES DATA QUALITY ===\n"
                    f"{aggregates}\n"
                    f"DÉTAIL ({len(df_filtered)} lignes) :\n{preview}"
                )
                sources.append(source_label)
            elif sql_result.get("error"):
                context_parts.append(
                    f"=== DONNÉES SQL ===\nErreur : {sql_result['error']}"
                )

        if strategy in ("rag", "hybrid") and self.rag:
            rag_result = self.rag.query(question, n_results=4)
            if rag_result["context"]:
                context_parts.append(
                    f"=== KNOWLEDGE BASE (RAG) ===\n{rag_result['context']}"
                )
                sources.extend(rag_result["sources"])

        if not context_parts:
            context_parts.append(
                "Aucun contexte data récupéré pour cette question."
            )

        # 3. Reformulation par le LLM
        full_context = "\n\n".join(context_parts)
        user_message = (
            f"{full_context}\n\n"
            f"=== QUESTION DE L'UTILISATEUR ===\n{question}"
        )

        try:
            answer = self.llm.chat(SYSTEM_PROMPT, user_message)
            status = "success"
        except Exception as e:
            answer = f"Erreur LLM : {e}"
            status = "error"

        return {
            "question": question,
            "answer": answer,
            "strategy": strategy,
            "routing_method": routing["method"],
            "routing_confidence": routing["confidence"],
            "sql_query": sql_query,
            "sql_data": sql_data,
            "sources": sorted(set(sources)),
            "provider": self.llm.name,
            "status": status,
        }


# ══════════════════════════════════════════════════════════════
# DEMO CLI
# ══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("AXAMesh — GenAI Copilot v2 (Architecture Hybride SQL + RAG)")
    print("=" * 70)

    copilot = DataQualityCopilot()
    print(f"\n🤖 LLM       : {copilot.info['llm']}")
    print(f"💾 SQL       : {copilot.info['sql']}")
    print(f"📚 RAG       : {copilot.info['rag']}\n")

    demo_questions = [
        # SQL pur
        "Combien de FAIL critiques sur l'entité axa_france ?",
        # RAG pur
        "Qu'est-ce qu'un data product chez AXA ?",
        # Hybride
        "Compare le pass rate des 3 entités et explique le framework qualité utilisé",
        # RAG conceptuel
        "Quels sont les 4 principes du data mesh ?",
    ]

    for q in demo_questions:
        print("─" * 70)
        print(f"💬 Q : {q}")
        result = copilot.ask(q)
        print(f"\n🧭 Stratégie : {result['strategy']} "
              f"(via {result['routing_method']}, "
              f"conf={result['routing_confidence']})")
        if result["sql_query"]:
            print(f"📝 SQL : {result['sql_query'][:100]}...")
        if result["sources"]:
            print(f"📚 Sources : {', '.join(result['sources'])}")
        print(f"\n🤖 Réponse :\n{result['answer']}\n")


if __name__ == "__main__":
    main()