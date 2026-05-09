"""
AXAMesh - GenAI Copilot : Streamlit App (v3 — AXA Design)
==========================================================
Interface conversationnelle avec charte graphique AXA complète.
Logo : logo_axa.png dans le même dossier que ce fichier.

Lancement :
    streamlit run src/06_genai_copilot/app.py --server.fileWatcherType none
"""

import streamlit as st
import sys
import base64
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from copilot_engine import DataQualityCopilot

# ──────────────────────────────────────────────────────────────
# CONFIG PAGE
# ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AXAMesh Copilot — Data Quality Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

AXA_BLUE       = "#00008F"
AXA_BLUE_LIGHT = "#1A1AB5"
AXA_RED        = "#FF1721"
AXA_WHITE      = "#FFFFFF"
AXA_GREY_BG    = "#F4F4F4"
AXA_PASS       = "#00A651"
AXA_WARN       = "#FFC107"
AXA_FAIL       = "#E60028"

st.markdown(f"""
<style>
    .stApp {{ background-color: {AXA_GREY_BG}; font-family: 'Segoe UI', sans-serif; }}

    /* SIDEBAR */
    [data-testid="stSidebar"] {{ background-color: {AXA_BLUE} !important; }}
    [data-testid="stSidebar"] * {{ color: {AXA_WHITE} !important; }}
    [data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.2) !important; }}
    [data-testid="stSidebar"] code {{
        background-color: rgba(255,255,255,0.15) !important;
        color: #A8D8FF !important;
        border-radius: 4px; padding: 2px 6px; font-size: 0.82em;
    }}

    /* HEADER */
    .axa-header {{
        background: linear-gradient(135deg, {AXA_BLUE} 0%, {AXA_BLUE_LIGHT} 100%);
        color: {AXA_WHITE}; padding: 1.5rem 2rem; border-radius: 10px;
        margin-bottom: 1.5rem; display: flex; align-items: center; gap: 1rem;
    }}
    .axa-header h1 {{ margin: 0; font-size: 1.8rem; font-weight: 700; color: {AXA_WHITE} !important; }}
    .axa-header p {{ margin: 4px 0 0; font-size: 0.9rem; opacity: 0.85; color: {AXA_WHITE}; }}

    /* KPI CARDS */
    [data-testid="stMetric"] {{
        background: {AXA_WHITE}; border: 1px solid #E0E0E0;
        border-top: 4px solid {AXA_BLUE}; border-radius: 8px;
        padding: 1rem; box-shadow: 0 2px 8px rgba(0,0,140,0.08);
    }}
    [data-testid="stMetricLabel"] {{
        color: {AXA_BLUE} !important; font-weight: 600 !important;
        font-size: 0.8rem !important; text-transform: uppercase; letter-spacing: 0.05em;
    }}
    [data-testid="stMetricValue"] {{
        color: #1A1A1A !important; font-weight: 700 !important; font-size: 1.8rem !important;
    }}

    /* CHAT */
    [data-testid="stChatMessage"] {{
        background: {AXA_WHITE}; border-radius: 10px;
        border: 1px solid #E8E8E8; margin-bottom: 0.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    [data-testid="stChatInput"] {{ border: 2px solid {AXA_BLUE} !important; border-radius: 8px !important; }}

    /* BOUTONS */
    .stButton > button {{
        background-color: {AXA_WHITE} !important; color: {AXA_BLUE} !important;
        border: 1.5px solid {AXA_BLUE} !important; border-radius: 6px !important;
        font-weight: 500 !important; text-align: left !important; transition: all 0.2s ease;
    }}
    .stButton > button:hover {{
        background-color: {AXA_BLUE} !important; color: {AXA_WHITE} !important;
    }}

    /* EXPANDER */
    [data-testid="stExpander"] {{ background: #F8F9FF; border: 1px solid #D0D4F0; border-radius: 8px; }}

    /* BADGES */
    .badge {{ display: inline-block; padding: 3px 12px; border-radius: 20px; font-size: 0.8em; font-weight: 600; }}
    .badge-sql    {{ background: #E3F2FD; color: #1565C0; border: 1px solid #90CAF9; }}
    .badge-rag    {{ background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; }}
    .badge-hybrid {{ background: #FFF3E0; color: #E65100; border: 1px solid #FFCC80; }}

    .section-title {{
        color: {AXA_WHITE}; font-size: 0.75rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.1em;
        margin: 1rem 0 0.5rem; padding-bottom: 4px;
        border-bottom: 2px solid {AXA_RED}; display: inline-block;
    }}

    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)


def load_image_b64(path: Path) -> str:
    if path.exists():
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


def render_badge(strategy: str) -> str:
    icons   = {"sql": "💾", "rag": "📚", "hybrid": "🔀"}
    classes = {"sql": "badge-sql", "rag": "badge-rag", "hybrid": "badge-hybrid"}
    return f'<span class="badge {classes.get(strategy, "")}">{icons.get(strategy, "❓")} {strategy.upper()}</span>'


@st.cache_resource
def init_copilot():
    return DataQualityCopilot()


with st.spinner("🚀 Initialisation AXAMesh Copilot..."):
    copilot = init_copilot()

LOGO_PATH = Path(__file__).parent / "logo_axa.png"
ROOT      = Path(__file__).parent.parent.parent
GOLD_BASE = ROOT / "data" / "gold"


# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    logo_b64 = load_image_b64(LOGO_PATH)
    if logo_b64:
        st.markdown(
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="width:120px; margin-bottom:1.2rem; display:block;">',
            unsafe_allow_html=True,
        )
    st.markdown("## AXAMesh Copilot")
    st.markdown("**Assistant Data Quality**")
    st.markdown("<small>AXA Group Operations · GDAI<br>Data Products & Platforms</small>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<div class="section-title">🔧 Architecture</div>', unsafe_allow_html=True)
    st.markdown(f"**LLM** : `{copilot.info['llm']}`")
    st.markdown(f"**SQL** : `{copilot.info['sql']}`")
    st.markdown(f"**RAG** : `{copilot.info['rag']}`")
    st.markdown("---")

    st.markdown('<div class="section-title">💡 Questions exemples</div>', unsafe_allow_html=True)
    st.markdown("""
**💾 SQL — KPIs**
- Combien de FAIL sur axa_france ?
- Quel domaine a le plus de blockers ?
- Compare le pass rate des 3 entités

**📚 RAG — Concepts**
- C'est quoi un data product ?
- Les 4 principes du data mesh ?
- Que dit DAMA sur la complétude ?

**🔀 Hybride**
- Compare les entités et explique DAMA
- Mes données sont-elles prêtes pour l'IA ?
""")
    st.markdown("---")
    if st.button("🔄 Nouvelle conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ── HEADER ────────────────────────────────────────────────────
logo_b64 = load_image_b64(LOGO_PATH)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:56px;">' if logo_b64 else "🤖"

st.markdown(f"""
<div class="axa-header">
    <div>{logo_html}</div>
    <div>
        <h1>AXAMesh Copilot</h1>
        <p>Assistant conversationnel pour les <strong>CDAOs</strong>, <strong>Data Managers</strong>
        et le <strong>Management Committee</strong> AXA — questions sur la qualité & AI Readiness des données.</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ── KPIs ──────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
n_pass = n_warn = n_fail = total = 0
if (GOLD_BASE / "quality_report.csv").exists():
    df_q     = pd.read_csv(GOLD_BASE / "quality_report.csv")
    total    = len(df_q)
    n_pass   = (df_q["status"] == "PASS").sum()
    n_warn   = (df_q["status"] == "WARN").sum()
    n_fail   = (df_q["status"] == "FAIL").sum()
    pass_pct = round(100 * n_pass / total, 1)
    col1.metric("🔍 Contrôles totaux", total)
    col2.metric("✅ Pass Rate", f"{pass_pct}%")
    col3.metric("🔴 Blockers IA", n_fail)

if (GOLD_BASE / "ai_readiness_report.csv").exists():
    df_r  = pd.read_csv(GOLD_BASE / "ai_readiness_report.csv")
    avg_r = round(df_r["ai_readiness_score"].mean(), 1)
    col4.metric("🎯 AI Readiness Group", f"{avg_r}%")
elif total > 0:
    ai_score = round((n_pass * 100 + n_warn * 50) / total, 1)
    col4.metric("🎯 AI Readiness Group", f"{ai_score}%")

st.markdown("---")


# ── CHAT ──────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            if "meta" in msg:
                meta = msg["meta"]
                st.markdown(
                    render_badge(meta["strategy"]) +
                    f" &nbsp;<span style='color:#888;font-size:0.82em'>via {meta['routing_method']} · conf={meta['routing_confidence']}</span>",
                    unsafe_allow_html=True,
                )
            st.markdown(msg["content"])
            if "meta" in msg:
                with st.expander("🔍 Détails techniques"):
                    meta = msg["meta"]
                    if meta.get("sql_query"):
                        st.markdown("**Requête SQL générée :**")
                        st.code(meta["sql_query"], language="sql")
                    if meta.get("sources"):
                        st.markdown("**Sources RAG :**")
                        for s in meta["sources"]: st.markdown(f"- 📄 `{s}`")
                    if meta.get("sql_data") is not None and not meta["sql_data"].empty:
                        st.markdown("**Données :**")
                        st.dataframe(meta["sql_data"], use_container_width=True)


if not st.session_state.messages:
    st.markdown('<div class="section-title" style="color:#00008F; border-bottom-color:#FF1721;">🚀 Démarrage rapide</div>', unsafe_allow_html=True)
    sug_col1, sug_col2 = st.columns(2)
    suggestions = [
        "💾 Combien de FAIL critiques sur axa_france ?",
        "📚 Qu'est-ce qu'un data product chez AXA ?",
        "📚 Quels sont les 4 principes du data mesh ?",
        "🔀 Compare les 3 entités et explique le framework DAMA",
    ]
    for i, sug in enumerate(suggestions):
        col = sug_col1 if i % 2 == 0 else sug_col2
        if col.button(sug, key=f"sug_{i}", use_container_width=True):
            question = sug.split(" ", 1)[1]
            st.session_state.messages.append({"role": "user", "content": question})
            with st.spinner("🤖 Analyse en cours..."):
                result = copilot.ask(question)
            st.session_state.messages.append({
                "role": "assistant", "content": result["answer"],
                "meta": {
                    "strategy": result["strategy"], "routing_method": result["routing_method"],
                    "routing_confidence": result["routing_confidence"],
                    "sql_query": result.get("sql_query"), "sql_data": result.get("sql_data"),
                    "sources": result.get("sources", []),
                },
            })
            st.rerun()


if prompt := st.chat_input("Pose ta question sur la data quality AXA..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🤖 Routage + analyse..."):
            result = copilot.ask(prompt)
        st.markdown(
            render_badge(result["strategy"]) +
            f" &nbsp;<span style='color:#888;font-size:0.82em'>via {result['routing_method']} · conf={result['routing_confidence']}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(result["answer"])
        with st.expander("🔍 Détails techniques"):
            if result.get("sql_query"):
                st.markdown("**Requête SQL générée :**")
                st.code(result["sql_query"], language="sql")
            if result.get("sources"):
                st.markdown("**Sources RAG :**")
                for s in result["sources"]: st.markdown(f"- 📄 `{s}`")
            if result.get("sql_data") is not None and not result["sql_data"].empty:
                st.markdown("**Données :**")
                st.dataframe(result["sql_data"], use_container_width=True)
    st.session_state.messages.append({
        "role": "assistant", "content": result["answer"],
        "meta": {
            "strategy": result["strategy"], "routing_method": result["routing_method"],
            "routing_confidence": result["routing_confidence"],
            "sql_query": result.get("sql_query"), "sql_data": result.get("sql_data"),
            "sources": result.get("sources", []),
        },
    })