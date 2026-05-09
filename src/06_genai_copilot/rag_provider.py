"""
AXAMesh - RAG Provider
======================
Recherche sémantique sur la knowledge base "unstructured" :
  - dama_dmbok.md           : framework data quality
  - axa_data_glossary.md    : glossaire des concepts AXA
  - data_mesh_principles.md : principes data mesh

Stack :
  - ChromaDB              : base vectorielle persistante locale
  - sentence-transformers : embeddings multilingues (FR/EN)
                            modèle : paraphrase-multilingual-MiniLM-L12-v2

Cette implémentation est volontairement **agnostique** : en production
chez AXA, ChromaDB serait remplacé par Azure AI Search (pattern identique).
"""

import os
from pathlib import Path
from typing import List, Optional

ROOT       = Path(__file__).parent.parent.parent
KB_DIR     = Path(__file__).parent / "knowledge_base"
CHROMA_DIR = ROOT / "data" / "vector_db"

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "axamesh_kb"
CHUNK_SIZE      = 600   # caractères par chunk
CHUNK_OVERLAP   = 100   # recouvrement entre chunks


class RAGProvider:
    """Provider RAG : indexe les docs et fait des recherches sémantiques."""

    def __init__(self, kb_dir: Path = KB_DIR,
                 chroma_dir: Path = CHROMA_DIR,
                 auto_index: bool = True):
        self.kb_dir = kb_dir
        self.chroma_dir = chroma_dir
        self.client = None
        self.collection = None
        self.embedder = None
        self._init_chromadb()
        if auto_index:
            self._ensure_indexed()

    @property
    def name(self) -> str:
        return f"RAGProvider [ChromaDB + {EMBEDDING_MODEL}]"

    # ──────────────────────────────────────────────────────────
    # INITIALISATION
    # ──────────────────────────────────────────────────────────

    def _init_chromadb(self):
        """Initialise ChromaDB en mode persistant."""
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "Module 'chromadb' manquant. Installe avec : pip install chromadb"
            )

        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "Module 'sentence-transformers' manquant. "
                "Installe avec : pip install sentence-transformers"
            )

        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

        # Crée ou récupère la collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # ──────────────────────────────────────────────────────────
    # CHUNKING
    # ──────────────────────────────────────────────────────────

    def _chunk_text(self, text: str,
                    chunk_size: int = CHUNK_SIZE,
                    overlap: int = CHUNK_OVERLAP) -> List[str]:
        """Découpe le texte en chunks avec recouvrement, en respectant
        les frontières de paragraphes autant que possible."""
        # Split par paragraphes (double saut de ligne)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = ""
        for p in paragraphs:
            if len(current) + len(p) + 2 <= chunk_size:
                current = (current + "\n\n" + p) if current else p
            else:
                if current:
                    chunks.append(current)
                # Si le paragraphe est trop gros, on le découpe brutalement
                if len(p) > chunk_size:
                    for i in range(0, len(p), chunk_size - overlap):
                        chunks.append(p[i:i + chunk_size])
                    current = ""
                else:
                    current = p
        if current:
            chunks.append(current)
        return chunks

    # ──────────────────────────────────────────────────────────
    # INDEXATION
    # ──────────────────────────────────────────────────────────

    def _ensure_indexed(self):
        """Indexe les fichiers MD si la collection est vide."""
        if self.collection.count() > 0:
            return
        self.index_knowledge_base()

    def index_knowledge_base(self) -> int:
        """Indexe tous les fichiers .md de la knowledge base."""
        if not self.kb_dir.exists():
            print(f"⚠️  Dossier knowledge base introuvable : {self.kb_dir}")
            return 0

        md_files = sorted(self.kb_dir.glob("*.md"))
        if not md_files:
            print(f"⚠️  Aucun fichier .md trouvé dans {self.kb_dir}")
            return 0

        # Reset de la collection pour réindexer proprement
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        all_ids, all_docs, all_metas = [], [], []
        for path in md_files:
            text = path.read_text(encoding="utf-8")
            chunks = self._chunk_text(text)
            for i, chunk in enumerate(chunks):
                cid = f"{path.stem}__chunk_{i:03d}"
                all_ids.append(cid)
                all_docs.append(chunk)
                all_metas.append({
                    "source": path.name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                })
            print(f"📄 {path.name} : {len(chunks)} chunks indexés")

        # Génère les embeddings
        embeddings = self.embedder.encode(
            all_docs, show_progress_bar=False
        ).tolist()

        # Insertion en batch
        self.collection.add(
            ids=all_ids,
            documents=all_docs,
            embeddings=embeddings,
            metadatas=all_metas,
        )
        print(f"✅ {len(all_docs)} chunks indexés au total")
        return len(all_docs)

    # ──────────────────────────────────────────────────────────
    # RECHERCHE SÉMANTIQUE
    # ──────────────────────────────────────────────────────────

    def search(self, query: str, n_results: int = 4) -> list:
        """Recherche les chunks les plus pertinents pour la question."""
        query_embedding = self.embedder.encode([query]).tolist()
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
        )
        # Restructure le résultat
        chunks = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                chunks.append({
                    "text": doc,
                    "source": meta.get("source", "?"),
                    "chunk_index": meta.get("chunk_index", 0),
                    "score": round(1 - distance, 3),  # similarité cosine
                })
        return chunks

    def query(self, question: str, n_results: int = 4) -> dict:
        """Retourne les chunks pertinents formatés pour le LLM."""
        chunks = self.search(question, n_results=n_results)
        if not chunks:
            return {
                "context": "",
                "sources": [],
                "n_chunks": 0,
            }

        context_parts = []
        sources = set()
        for c in chunks:
            context_parts.append(
                f"[Source: {c['source']} | Pertinence: {c['score']}]\n{c['text']}"
            )
            sources.add(c["source"])

        return {
            "context": "\n\n---\n\n".join(context_parts),
            "sources": sorted(sources),
            "n_chunks": len(chunks),
        }