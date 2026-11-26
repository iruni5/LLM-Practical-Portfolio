import re
import time
import json
import hashlib
import requests
import numpy as np
import networkx as nx
import fitz  # PyMuPDF
import streamlit as st
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Import core ingestion functions from your ingest.py
from ingest import (
    ingest_pdf,
    list_documents,
    DATA_DIR,
    DB_PATH,
    COLLECTION,
)

# pyrefly: ignore[missing-import]
from langchain_chroma import Chroma
# pyrefly: ignore[missing-import]
from langchain_ollama import OllamaEmbeddings, OllamaLLM
# pyrefly: ignore[missing-import]
from langchain_core.prompts import PromptTemplate
# pyrefly: ignore[missing-import]
from langchain_core.documents import Document
# pyrefly: ignore[missing-import]
from sentence_transformers import CrossEncoder
# pyrefly: ignore[missing-import]
from sklearn.feature_extraction.text import TfidfVectorizer
# pyrefly: ignore[missing-import]
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Document & Literature AI Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

EMBEDDING_MODEL = "qwen3-embedding:0.6b"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_LLMS = ["llama3.2:3b", "llama3.1:latest", "llama3:latest"]
GRAPH_PATH = DB_PATH / "knowledge_graph.graphml"

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "active_view" not in st.session_state:
    st.session_state.active_view = "💬 AI Chat"


# -----------------------------------------------------------------------------
# 2. CACHED RESOURCES (ELIMINATES UI FREEZING & RELOAD LATENCY)
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_cached_vectorstore() -> Chroma:
    """Load OllamaEmbeddings and ChromaDB once and keep in memory."""
    DB_PATH.mkdir(parents=True, exist_ok=True)
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=str(DB_PATH),
    )


@st.cache_resource(show_spinner=False)
def get_cached_reranker():
    """Load the Cross-Encoder reranker model once into RAM."""
    try:
        return CrossEncoder(RERANKER_MODEL)
    except Exception:
        return None


@st.cache_data(ttl=30, show_spinner=False)
def get_ollama_status_and_models() -> Tuple[bool, List[str]]:
    """Fast non-blocking check (0.4s timeout) so the UI never hangs."""
    try:
        res = requests.get("http://localhost:11434/api/tags", timeout=0.4)
        if res.status_code == 200:
            models = [
                m.get("name", "")
                for m in res.json().get("models", [])
                if "embed" not in m.get("name", "").lower()
            ]
            ordered = [m for m in DEFAULT_LLMS if m in models] + [
                m for m in models if m not in DEFAULT_LLMS
            ]
            return True, ordered if ordered else DEFAULT_LLMS
    except Exception:
        pass
    return False, DEFAULT_LLMS


@st.cache_data(show_spinner=False)
def get_indexed_stats_cached() -> Tuple[int, Dict[str, int]]:
    """
    Permanently cached vector DB stats. Only cleared when a file is uploaded or deleted,
    preventing ChromaDB from being queried on every button click or slider move.
    """
    try:
        vs = get_cached_vectorstore()
        total_chunks = vs._collection.count()
        if total_chunks == 0:
            return 0, {}

        data = vs._collection.get(include=["metadatas"])
        metadatas = data.get("metadatas", [])
        file_counts: Dict[str, int] = {}
        for meta in metadatas:
            if meta and "filename" in meta:
                fname = meta["filename"]
                file_counts[fname] = file_counts.get(fname, 0) + 1
        return total_chunks, file_counts
    except Exception:
        return 0, {}


@st.cache_data(show_spinner=False)
def get_cached_knowledge_graph_stats() -> Tuple[int, int, List[Dict[str, str]]]:
    """Load NetworkX Knowledge Graph stats and triplets without blocking the UI."""
    if not GRAPH_PATH.exists():
        return 0, 0, []
    try:
        G = nx.read_graphml(str(GRAPH_PATH))
        triplets = []
        for u, v, data in G.edges(data=True):
            label = data.get("label", "RELATED_TO")
            triplets.append(
                {
                    "source": str(u),
                    "relation": str(label),
                    "target": str(v),
                    "file_hash": str(data.get("source_file", "")),
                }
            )
        return G.number_of_nodes(), G.number_of_edges(), triplets
    except Exception:
        return 0, 0, []


@st.cache_resource(show_spinner=False)
def get_cached_lexical_index(selected_doc: str, total_chunks: int):
    """
    Pre-computes and caches the TF-IDF matrix so Hybrid Search runs in <10ms
    instead of rebuilding the matrix on every chat message.
    """
    if total_chunks == 0:
        return None, None, [], []
    try:
        vs = get_cached_vectorstore()
        where_filter = (
            {"filename": selected_doc}
            if selected_doc != "All Indexed Documents"
            else None
        )
        all_data = vs.get(where=where_filter, include=["documents", "metadatas"])
        corpus_texts = all_data.get("documents", [])
        corpus_metas = all_data.get("metadatas", [])
        if not corpus_texts:
            return None, None, [], []

        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        tfidf_mat = vec.fit_transform(corpus_texts)
        return vec, tfidf_mat, corpus_texts, corpus_metas
    except Exception:
        return None, None, [], []


def clear_all_data_caches():
    """Clear cached stats whenever documents are added or removed."""
    get_indexed_stats_cached.clear()
    get_cached_knowledge_graph_stats.clear()
    get_cached_lexical_index.clear()


class LocalPDFUploadAdapter:
    """Wraps a local PDF Path object so it works with ingest.py's ingest_pdf()."""
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self._bytes = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._bytes


def sync_local_data_folder() -> List[str]:
    """Index any PDF sitting in data/ that has not yet been indexed into Chroma."""
    pdf_files = list_documents()
    results = []
    vs = get_cached_vectorstore()

    for pdf_path in pdf_files:
        try:
            raw_bytes = pdf_path.read_bytes()
            file_hash = hashlib.sha256(raw_bytes).hexdigest()
            existing = vs.get(where={"file_hash": file_hash}, limit=1)
            if not existing.get("ids"):
                adapter = LocalPDFUploadAdapter(pdf_path)
                msg = ingest_pdf(adapter)
                if not pdf_path.name.startswith(file_hash[:12]):
                    pdf_path.unlink(missing_ok=True)
                results.append(msg)
        except Exception as e:
            results.append(f"Skipped {pdf_path.name}: {e}")

    if results:
        clear_all_data_caches()
    return results


def remove_file_from_knowledge_graph(file_hashes: List[str]):
    """Remove nodes and edges belonging to deleted files from knowledge_graph.graphml."""
    if not GRAPH_PATH.exists() or not file_hashes:
        return
    try:
        G = nx.read_graphml(str(GRAPH_PATH))
        hash_set = set(file_hashes)
        edges_to_remove = [
            (u, v)
            for u, v, d in G.edges(data=True)
            if d.get("source_file") in hash_set
        ]
        G.remove_edges_from(edges_to_remove)
        nodes_to_remove = [
            n
            for n, d in G.nodes(data=True)
            if d.get("source_file") in hash_set and G.degree(n) == 0
        ]
        G.remove_nodes_from(nodes_to_remove)
        nx.write_graphml(G, str(GRAPH_PATH))
    except Exception:
        pass


# -----------------------------------------------------------------------------
# 3. ZERO-FLICKER THEME ENGINE & FIXED CHATBOT LAYOUT CSS
# -----------------------------------------------------------------------------
def inject_custom_css(theme: str):
    if theme == "dark":
        p = {
            "bg_main": "#0D0E12",
            "bg_sec": "#13151C",
            "bg_card": "#181B24",
            "bg_hover": "#212532",
            "text_pri": "#ECECEF",
            "text_sec": "#9499A6",
            "accent": "#D97757",
            "accent_soft": "rgba(217, 119, 87, 0.14)",
            "kg_accent": "#10B981",
            "kg_soft": "rgba(16, 185, 129, 0.14)",
            "border": "#262A36",
            "shadow": "0 6px 24px rgba(0, 0, 0, 0.35)",
            "code_bg": "#101217",
        }
    else:
        p = {
            "bg_main": "#FAF9F5",
            "bg_sec": "#F2EFE9",
            "bg_card": "#FFFFFF",
            "bg_hover": "#EAE6DF",
            "text_pri": "#191918",
            "text_sec": "#666560",
            "accent": "#C6613F",
            "accent_soft": "rgba(198, 97, 63, 0.12)",
            "kg_accent": "#059669",
            "kg_soft": "rgba(5, 150, 105, 0.12)",
            "border": "#E4E1D8",
            "shadow": "0 4px 20px rgba(25, 25, 24, 0.06)",
            "code_bg": "#F4F2ED",
        }

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {{
            --bg-main: {p["bg_main"]};
            --bg-sec: {p["bg_sec"]};
            --bg-card: {p["bg_card"]};
            --bg-hover: {p["bg_hover"]};
            --text-pri: {p["text_pri"]};
            --text-sec: {p["text_sec"]};
            --accent: {p["accent"]};
            --accent-soft: {p["accent_soft"]};
            --kg-accent: {p["kg_accent"]};
            --kg-soft: {p["kg_soft"]};
            --border: {p["border"]};
            --shadow: {p["shadow"]};
            --code-bg: {p["code_bg"]};
        }}

        /* Prevent Streamlit from dimming/blackening the screen during updates */
        [data-stale="true"],
        div[data-testid="stAppViewBlockContainer"] *,
        .stApp [data-testid="stVerticalBlock"] {{
            opacity: 1 !important;
            transition: none !important;
            filter: none !important;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes pulseDot {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.25); opacity: 0.65; }}
        }}

        .stApp {{
            background-color: var(--bg-main) !important;
            color: var(--text-pri) !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: var(--bg-sec) !important;
            border-right: 1px solid var(--border) !important;
        }}

        section[data-testid="stSidebar"] * {{
            color: var(--text-pri) !important;
        }}

        h1, h2, h3, h4, p, span, label, div {{
            color: var(--text-pri);
        }}

        code, pre {{
            font-family: 'JetBrains Mono', monospace !important;
            background-color: var(--code-bg) !important;
            border-radius: 6px;
        }}

        .hero-header {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.9rem 1.35rem;
            margin-bottom: 0.85rem;
            box-shadow: var(--shadow);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .hero-title {{
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .hero-subtitle {{
            color: var(--text-sec) !important;
            font-size: 0.82rem;
            margin-top: 2px;
        }}

        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 600;
            background: var(--bg-sec);
            border: 1px solid var(--border);
        }}

        .dot-online {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #10B981;
            animation: pulseDot 2s infinite ease-in-out;
        }}

        .dot-offline {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #EF4444;
        }}

        div[data-testid="stChatMessage"] {{
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 0.95rem 1.2rem !important;
            margin-bottom: 0.75rem !important;
            box-shadow: var(--shadow);
            animation: fadeIn 0.2s ease-out;
        }}

        div[data-testid="stChatInput"] {{
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 14px !important;
            box-shadow: var(--shadow) !important;
        }}

        div[data-testid="stChatInput"]:focus-within {{
            border-color: var(--accent) !important;
        }}

        .glass-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 0.85rem 1.1rem;
            margin-bottom: 0.65rem;
            box-shadow: var(--shadow);
        }}

        .citation-badge {{
            display: inline-block;
            background: var(--accent-soft);
            color: var(--accent) !important;
            border: 1px solid var(--accent);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.73rem;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 4px;
        }}

        .kg-badge {{
            display: inline-block;
            background: var(--kg-soft);
            color: var(--kg-accent) !important;
            border: 1px solid var(--kg-accent);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.73rem;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 4px;
        }}

        .telemetry-bar {{
            font-size: 0.76rem;
            color: var(--text-sec) !important;
            margin-top: 0.5rem;
            padding-top: 0.45rem;
            border-top: 1px dashed var(--border);
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
        }}

        .stButton > button {{
            background-color: var(--bg-card) !important;
            color: var(--text-pri) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
        }}

        .stButton > button:hover {{
            border-color: var(--accent) !important;
            background-color: var(--accent-soft) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_custom_css(st.session_state.theme)


# -----------------------------------------------------------------------------
# 4. KNOWLEDGE GRAPH & ADVANCED RAG RETRIEVAL ENGINE
# -----------------------------------------------------------------------------
def retrieve_knowledge_graph_facts(query: str, max_facts: int = 6) -> List[str]:
    """
    Search the cached NetworkX knowledge graph for entities mentioned in the query
    and return 1-hop and 2-hop relational triplets.
    """
    _, _, triplets = get_cached_knowledge_graph_stats()
    if not triplets:
        return []

    query_words = {
        w.lower() for w in re.findall(r"\w+", query) if len(w) > 3
    }
    if not query_words:
        return []

    matched_facts: List[str] = []
    matched_entities = set()

    # Hop 1: Direct entity match
    for t in triplets:
        src_low = t["source"].lower()
        tgt_low = t["target"].lower()
        if any(w in src_low or w in tgt_low for w in query_words):
            fact_str = f"[{t['source']}] --({t['relation']})--> [{t['target']}]"
            if fact_str not in matched_facts:
                matched_facts.append(fact_str)
            matched_entities.add(t["source"])
            matched_entities.add(t["target"])

    # Hop 2: Connected neighbor traversal if capacity remains
    if matched_entities and len(matched_facts) < max_facts:
        for t in triplets:
            if t["source"] in matched_entities or t["target"] in matched_entities:
                fact_str = f"[{t['source']}] --({t['relation']})--> [{t['target']}]"
                if fact_str not in matched_facts:
                    matched_facts.append(fact_str)
                if len(matched_facts) >= max_facts:
                    break

    return matched_facts[:max_facts]


def run_advanced_rag_stream(
    query: str,
    model_name: str,
    top_k: int,
    temperature: float,
    selected_doc: str,
    use_hyde: bool,
    use_multihop: bool,
    use_reranker: bool,
    use_compression: bool,
    use_kg: bool,
    total_chunks_count: int,
    chat_history: list,
    status_container=None,
):
    """
    Executes the 5-stage Hybrid & Knowledge Graph RAG Pipeline:
      1. Query Expansion + HyDE (Hypothetical Document Embeddings)
      2. Multi-Hop Hybrid Retrieval (Dense MMR + Cached Lexical TF-IDF via RRF)
      3. Cross-Encoder Reranking
      4. Contextual Sentence Compression
      4.5. Knowledge Graph Traversal (NetworkX Triplets)
      5. Streaming LLM Response Generation
    """
    t0 = time.perf_counter()
    vectorstore = get_cached_vectorstore()
    cross_encoder = get_cached_reranker() if use_reranker else None
    llm = OllamaLLM(model=model_name, temperature=temperature)

    trace_info: Dict[str, Any] = {
        "expanded_queries": [query],
        "hop2_codes": [],
        "candidates_count": 0,
        "final_count": 0,
        "graph_facts": [],
    }

    # --- STAGE 1: QUERY EXPANSION & HyDE (UNIVERSAL LITERATURE & DOCUMENT PROMPT) ---
    search_queries = [query]
    if use_hyde:
        if status_container:
            status_container.write("🪄 **Stage 1:** Generating HyDE hypothetical passage & sub-queries...")
        hyde_prompt = (
            "You are an expert document and literature search optimizer.\n"
            "Given the user's question below, write 2 short search queries targeting key names, plot points, or facts, "
            "and 1 concise hypothetical passage that would answer it.\n"
            f"Question: {query}\n"
            "Format:\nQ1: <query>\nQ2: <query>\nHYDE: <sentence>"
        )
        try:
            fast_llm = OllamaLLM(model=model_name, temperature=0.1)
            raw_exp = fast_llm.invoke(hyde_prompt)
            for line in raw_exp.splitlines():
                line = line.strip()
                if line.upper().startswith(("Q1:", "Q2:", "HYDE:")):
                    val = line.split(":", 1)[1].strip()
                    if len(val) > 5:
                        search_queries.append(val)
        except Exception:
            pass
    trace_info["expanded_queries"] = search_queries[:4]

    # --- STAGE 2: HYBRID + MULTI-HOP RETRIEVAL ---
    if status_container:
        status_container.write("🕸️ **Stage 2:** Executing Hybrid RRF (Dense MMR + Cached TF-IDF) & Multi-Hop lookup...")

    doc_map: Dict[str, Document] = {}
    rrf_scores: Dict[str, float] = {}

    search_kwargs: Dict[str, Any] = {"k": max(top_k + 2, 6), "fetch_k": max(top_k * 4, 16)}
    if selected_doc != "All Indexed Documents":
        search_kwargs["filter"] = {"filename": selected_doc}

    mmr_retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs=search_kwargs)

    for q in search_queries[:4]:
        try:
            dense_docs = mmr_retriever.invoke(q)
            for rank, doc in enumerate(dense_docs):
                key = f"{doc.metadata.get('file_hash', '')}_{doc.metadata.get('page', 0)}_{hash(doc.page_content)}"
                doc_map[key] = doc
                rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (60 + rank + 1)
        except Exception:
            continue

    # Fast Cached Lexical TF-IDF Retrieval
    vec, tfidf_mat, corpus_texts, corpus_metas = get_cached_lexical_index(
        selected_doc, total_chunks_count
    )
    if vec is not None and tfidf_mat is not None and corpus_texts:
        try:
            q_vec = vec.transform([query])
            sims = cosine_similarity(q_vec, tfidf_mat).flatten()
            top_idx = np.argsort(sims)[::-1][:8]
            for rank, idx in enumerate(top_idx):
                if sims[idx] > 0.04:
                    doc = Document(
                        page_content=corpus_texts[idx],
                        metadata=corpus_metas[idx] or {},
                    )
                    key = f"{doc.metadata.get('file_hash', '')}_{doc.metadata.get('page', 0)}_{hash(doc.page_content)}"
                    doc_map[key] = doc
                    rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (60 + rank + 1)
        except Exception:
            pass

    sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
    candidates = [doc_map[k] for k in sorted_keys[:10]]

    # Multi-Hop (Hop 2): Follow up on discovered codes or capitalized proper nouns
    if use_multihop and candidates:
        hop1_text = " ".join(d.page_content for d in candidates[:3])
        found_codes = set(re.findall(r"\b[A-Z]{2}\d{3}(?:\.\d)?\b", hop1_text))
        query_codes = set(re.findall(r"\b[A-Z]{2}\d{3}(?:\.\d)?\b", query.upper()))
        new_codes = list(found_codes - query_codes)[:3]
        if new_codes:
            trace_info["hop2_codes"] = new_codes
            hop2_q = f"{query} {' '.join(new_codes)}"
            try:
                hop2_docs = vectorstore.similarity_search(hop2_q, k=3)
                for doc in hop2_docs:
                    key = f"{doc.metadata.get('file_hash', '')}_{doc.metadata.get('page', 0)}_{hash(doc.page_content)}"
                    if key not in doc_map:
                        doc_map[key] = doc
                        candidates.append(doc)
            except Exception:
                pass

    trace_info["candidates_count"] = len(candidates)

    # --- STAGE 3: CROSS-ENCODER RERANKING ---
    if use_reranker and cross_encoder is not None and candidates:
        if status_container:
            status_container.write(
                f"🎯 **Stage 3:** Reranking {len(candidates)} candidate chunks with Cross-Encoder..."
            )
        try:
            pairs = [[query, d.page_content] for d in candidates]
            scores = cross_encoder.predict(pairs)
            scored = sorted(zip(candidates, scores), key=lambda x: float(x[1]), reverse=True)
            reranked_docs = []
            for d, sc in scored[:top_k]:
                d.metadata["rerank_score"] = round(float(sc), 3)
                reranked_docs.append(d)
        except Exception:
            reranked_docs = candidates[:top_k]
    else:
        reranked_docs = candidates[:top_k]

    # --- STAGE 4: CONTEXTUAL COMPRESSION ---
    if use_compression and reranked_docs:
        if status_container:
            status_container.write("✂️ **Stage 4:** Applying contextual sentence compression...")
        compressed_docs: List[Document] = []
        for d in reranked_docs:
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+|\n+", d.page_content)
                if len(s.strip()) > 15
            ]
            if len(sentences) <= 4 or cross_encoder is None:
                compressed_docs.append(d)
                continue
            try:
                s_pairs = [[query, s] for s in sentences]
                s_scores = cross_encoder.predict(s_pairs)
                keep_n = max(3, int(len(sentences) * 0.65))
                keep_idx = sorted(np.argsort(s_scores)[::-1][:keep_n])
                compressed_text = " ".join(sentences[i] for i in keep_idx)
                compressed_docs.append(
                    Document(page_content=compressed_text, metadata=dict(d.metadata))
                )
            except Exception:
                compressed_docs.append(d)
        final_docs = compressed_docs
    else:
        final_docs = reranked_docs

    # --- STAGE 4.5: KNOWLEDGE GRAPH RETRIEVAL ---
    graph_facts: List[str] = []
    if use_kg:
        if status_container:
            status_container.write("🧠 **Stage 4.5:** Traversing NetworkX Knowledge Graph for entity links...")
        graph_facts = retrieve_knowledge_graph_facts(query)
        trace_info["graph_facts"] = graph_facts

    trace_info["final_count"] = len(final_docs)
    retrieval_time = time.perf_counter() - t0

    # --- STAGE 5: FORMAT PROMPT & STREAM RESPONSE ---
    context_blocks = []
    if graph_facts:
        kg_formatted = "\n".join(f"- {fact}" for fact in graph_facts)
        context_blocks.append(f"[KNOWLEDGE GRAPH FACTS]\n{kg_formatted}")

    for idx, doc in enumerate(final_docs, 1):
        fname = doc.metadata.get("filename", "Document")
        page = doc.metadata.get("page", 0) + 1
        score = doc.metadata.get("rerank_score", "N/A")
        context_blocks.append(
            f"[Source {idx}: {fname} | Page {page} | Score: {score}]\n{doc.page_content.strip()}"
        )

    context_text = (
        "\n\n---\n\n".join(context_blocks)
        if context_blocks
        else "No matching context found in the vector database."
    )

    recent_turns = ""
    for msg in chat_history[-4:]:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        recent_turns += f"{role_label}: {msg['content']}\n"

    prompt_template = PromptTemplate.from_template(
        "You are an expert literary assistant and document analyst.\n"
        "Answer the user's question accurately using ONLY the provided Context and Knowledge Graph Facts below.\n"
        "- Cite the source document and page number naturally when stating facts, quotes, plot points, or rules (e.g., [Page X]).\n"
        "- Format lists, character relationships, or technical details cleanly using Markdown.\n"
        "- If the answer is not present in the context, state clearly that the uploaded documents do not contain that information.\n\n"
        "Recent Conversation:\n{history}\n\n"
        "Retrieved Context & Knowledge Graph:\n{context}\n\n"
        "Question: {question}\n\n"
        "Grounded Answer:"
    )

    final_prompt = prompt_template.format(
        history=recent_turns.strip() or "None",
        context=context_text,
        question=query,
    )

    stream_gen = llm.stream(final_prompt)
    return stream_gen, final_docs, retrieval_time, trace_info


# -----------------------------------------------------------------------------
# 5. SIDEBAR: CONTROLS, ADVANCED RAG TOGGLES & DATA SYNC
# -----------------------------------------------------------------------------
ollama_ok, available_models = get_ollama_status_and_models()
total_chunks, doc_chunk_map = get_indexed_stats_cached()
kg_nodes, kg_edges, kg_triplets = get_cached_knowledge_graph_stats()

with st.sidebar:
    st.markdown("### ⚙️ Workspace Controls")

    t_col1, t_col2 = st.columns(2)
    with t_col1:
        if st.button(
            "☀️ Light" if st.session_state.theme == "dark" else "🌙 Dark",
            use_container_width=True,
        ):
            st.session_state.theme = (
                "light" if st.session_state.theme == "dark" else "dark"
            )
            st.rerun()
    with t_col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.divider()

    st.markdown("#### 🧠 Model & Scope")
    llm_model = st.selectbox(
        "Generation LLM (Ollama)",
        options=available_models,
        index=0,
        help="Automatically lists your installed Ollama models.",
    )

    doc_options = ["All Indexed Documents"] + sorted(list(doc_chunk_map.keys()))
    selected_doc_scope = st.selectbox(
        "🎯 Document Scope Filter",
        options=doc_options,
        index=0,
    )

    top_k_slider = st.slider("Retrieved Chunks (k)", min_value=2, max_value=8, value=4)
    temp_slider = st.slider(
        "Model Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05
    )

    st.divider()

    st.markdown("#### 🚀 Advanced RAG Modules")
    use_kg = st.toggle(
        "🧠 Knowledge Graph RAG",
        value=True,
        help="Traverses NetworkX entity triplets (.graphml) for multi-hop relationship grounding.",
    )
    use_reranker = st.toggle(
        "🎯 Cross-Encoder Reranking",
        value=True,
        help="Re-scores retrieved chunks using ms-marco-MiniLM CrossEncoder.",
    )
    use_multihop = st.toggle(
        "🕸️ Multi-Hop + Hybrid RRF",
        value=True,
        help="Combines Dense MMR + Cached Lexical TF-IDF and performs 2-hop entity lookup.",
    )
    use_compression = st.toggle(
        "✂️ Contextual Compression",
        value=False,
        help="Strips low-score sentences from chunks. Keep OFF for faster response times on large novels.",
    )
    use_hyde = st.toggle(
        "🪄 HyDE Query Expansion",
        value=False,
        help="Generates a hypothetical answer & sub-queries before searching (adds ~2s LLM latency).",
    )

    st.divider()

    st.markdown("#### 📥 Quick Data Sync")
    if st.button("🔄 Sync Local `data/` Folder", use_container_width=True):
        with st.spinner("Indexing PDFs & extracting Knowledge Graph..."):
            synced = sync_local_data_folder()
            if synced:
                for m in synced:
                    st.success(m)
                st.rerun()
            else:
                st.toast("All PDFs in data/ are already indexed!", icon="✅")

    if st.session_state.messages:
        chat_export = json.dumps(st.session_state.messages, indent=2)
        st.download_button(
            "📤 Export Chat Log (.json)",
            data=chat_export,
            file_name="rag_chat_session.json",
            mime="application/json",
            use_container_width=True,
        )

    st.caption(
        f"📦 **Vector DB:** `{COLLECTION}`  \n"
        f"🧩 **Indexed Chunks:** `{total_chunks}`  \n"
        f"🕸️ **KG Graph:** `{kg_nodes} nodes · {kg_edges} edges`  \n"
        f"🔢 **Embeddings:** `{EMBEDDING_MODEL}`"
    )


# -----------------------------------------------------------------------------
# 6. TOP HERO HEADER & NON-JUMPING VIEW SWITCHER
# -----------------------------------------------------------------------------
status_dot = "dot-online" if ollama_ok else "dot-offline"
status_text = (
    f"Ollama Online · {llm_model}"
    if ollama_ok
    else "Ollama Offline (Run `ollama serve`)"
)

st.markdown(
    f"""
    <div class="hero-header">
        <div>
            <div class="hero-title">📚 Universal Document &amp; Literature AI Assistant</div>
            <div class="hero-subtitle">
                Knowledge Graph + Hybrid RAG · Cross-Encoder Reranking, Multi-Hop, HyDE &amp; Compression
            </div>
        </div>
        <div class="status-pill">
            <span class="{status_dot}"></span>
            <span>{status_text}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

selected_view = st.segmented_control(
    "Workspace View",
    options=[
        "💬 AI Chat",
        "📖 Document & Knowledge Graph Explorer",
        "📥 Data Ingestion Hub",
    ],
    default=st.session_state.active_view,
    label_visibility="collapsed",
)
if selected_view and selected_view != st.session_state.active_view:
    st.session_state.active_view = selected_view
    st.rerun()


# =============================================================================
# VIEW 1: AI CHAT WORKSPACE (DOCKED INPUT & ZERO-FLICKER STREAMING)
# =============================================================================
if st.session_state.active_view == "💬 AI Chat":
    if total_chunks == 0:
        unindexed_local = list_documents()
        if unindexed_local:
            st.info(
                f"Found **{len(unindexed_local)} PDF(s)** in your `data/` folder ready to be indexed. "
                "Click **🔄 Sync Local `data/` Folder** in the sidebar to index them."
            )
        else:
            st.warning(
                "Your Chroma vector database is currently empty! Switch to **📥 Data Ingestion Hub** to upload a novel or handbook PDF."
            )

    chat_feed_container = st.container()

    with chat_feed_container:
        if not st.session_state.messages:
            st.markdown("##### ✨ Suggested Starter Queries (Handbooks & Novels)")
            c1, c2, c3 = st.columns(3)
            starters = [
                "Summarize the main themes, core subjects, or key topics in this document.",
                "Who are the primary characters or key entities, and how do they interact?",
                "What are the most important rules, requirements, or pivotal events?",
            ]
            for col, text in zip([c1, c2, c3], starters):
                with col:
                    if st.button(text, use_container_width=True):
                        st.session_state.pending_prompt = text
                        st.rerun()

        # Render existing conversation history
        for message in st.session_state.messages:
            with st.chat_message(
                message["role"],
                avatar="🧑‍💻" if message["role"] == "user" else "📚",
            ):
                st.markdown(message["content"])

                if message["role"] == "assistant" and (
                    message.get("sources") or message.get("graph_facts")
                ):
                    tel = message.get("telemetry", {})
                    kg_count = len(message.get("graph_facts", []))
                    st.markdown(
                        f"""
                        <div class="telemetry-bar">
                            <span>⚡ Retrieval: <b>{tel.get('retrieval_s', 0):.2f}s</b></span>
                            <span>⏱️ Total: <b>{tel.get('total_s', 0):.2f}s</b></span>
                            <span>🎯 Vector Chunks: <b>{tel.get('candidates', 0)} → {len(message.get('sources', []))}</b></span>
                            <span>🕸️ KG Facts: <b>{kg_count}</b></span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.expander("🔍 View Verified Source Passages & Knowledge Graph Links"):
                        if message.get("graph_facts"):
                            st.markdown("**🕸️ Matched Knowledge Graph Triplets:**")
                            kg_html = "".join(
                                f"<span class='kg-badge'>{fact}</span>"
                                for fact in message["graph_facts"]
                            )
                            st.markdown(
                                f"<div style='margin-bottom:10px;'>{kg_html}</div>",
                                unsafe_allow_html=True,
                            )

                        for idx, src in enumerate(message.get("sources", []), 1):
                            score_badge = (
                                f"<span class='citation-badge'>🎯 Score: {src['score']}</span>"
                                if src.get("score") not in (None, "N/A")
                                else ""
                            )
                            st.markdown(
                                f"""
                                <div class="glass-card">
                                    <span class="citation-badge">Source {idx}</span>
                                    <span class="citation-badge">📄 {src['filename']}</span>
                                    <span class="citation-badge">📍 Page {src['page']}</span>
                                    {score_badge}
                                    <p style="margin-top: 8px; font-size: 0.85rem; line-height: 1.55;">
                                        {src['snippet']}
                                    </p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

    # DOCKED BOTTOM CHAT INPUT
    typed_query = st.chat_input("Ask about your uploaded novel, story, or university handbook...")
    user_query = typed_query or st.session_state.pending_prompt
    if st.session_state.pending_prompt:
        st.session_state.pending_prompt = None

    if user_query:
        st.session_state.messages.append({"role": "user", "content": user_query})

        with chat_feed_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(user_query)

            with st.chat_message("assistant", avatar="📚"):
                if not ollama_ok:
                    st.error(
                        "Cannot connect to Ollama at http://localhost:11434. Please ensure Ollama is running."
                    )
                else:
                    try:
                        t_start = time.perf_counter()
                        with st.status(
                            "🧠 Running Hybrid + Knowledge Graph RAG Pipeline...",
                            expanded=False,
                        ) as status_box:
                            stream_gen, retrieved_docs, ret_time, trace_info = (
                                run_advanced_rag_stream(
                                    query=user_query,
                                    model_name=llm_model,
                                    top_k=top_k_slider,
                                    temperature=temp_slider,
                                    selected_doc=selected_doc_scope,
                                    use_hyde=use_hyde,
                                    use_multihop=use_multihop,
                                    use_reranker=use_reranker,
                                    use_compression=use_compression,
                                    use_kg=use_kg,
                                    total_chunks_count=total_chunks,
                                    chat_history=st.session_state.messages[:-1],
                                    status_container=status_box,
                                )
                            )
                            kg_matched = trace_info.get("graph_facts", [])
                            status_box.update(
                                label=(
                                    f"✅ Retrieved {len(retrieved_docs)} chunks & "
                                    f"{len(kg_matched)} KG facts in {ret_time:.2f}s"
                                ),
                                state="complete",
                                expanded=False,
                            )

                        full_response = st.write_stream(stream_gen)
                        total_time = time.perf_counter() - t_start

                        serialized_sources = []
                        for d in retrieved_docs:
                            serialized_sources.append(
                                {
                                    "filename": d.metadata.get("filename", "Unknown PDF"),
                                    "page": d.metadata.get("page", 0) + 1,
                                    "score": d.metadata.get("rerank_score", "N/A"),
                                    "snippet": d.page_content[:500] + "..."
                                    if len(d.page_content) > 500
                                    else d.page_content,
                                }
                            )

                        telemetry_data = {
                            "retrieval_s": ret_time,
                            "total_s": total_time,
                            "candidates": trace_info.get(
                                "candidates_count", len(serialized_sources)
                            ),
                        }

                        st.markdown(
                            f"""
                            <div class="telemetry-bar">
                                <span>⚡ Retrieval: <b>{ret_time:.2f}s</b></span>
                                <span>⏱️ Total: <b>{total_time:.2f}s</b></span>
                                <span>🎯 Vector Chunks: <b>{telemetry_data['candidates']} → {len(serialized_sources)}</b></span>
                                <span>🕸️ KG Facts: <b>{len(kg_matched)}</b></span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        if serialized_sources or kg_matched:
                            with st.expander(
                                "🔍 View Verified Source Passages & Knowledge Graph Links"
                            ):
                                if kg_matched:
                                    st.markdown("**🕸️ Matched Knowledge Graph Triplets:**")
                                    kg_html = "".join(
                                        f"<span class='kg-badge'>{fact}</span>"
                                        for fact in kg_matched
                                    )
                                    st.markdown(
                                        f"<div style='margin-bottom:10px;'>{kg_html}</div>",
                                        unsafe_allow_html=True,
                                    )

                                for idx, src in enumerate(serialized_sources, 1):
                                    score_badge = (
                                        f"<span class='citation-badge'>🎯 Score: {src['score']}</span>"
                                        if src.get("score") not in (None, "N/A")
                                        else ""
                                    )
                                    st.markdown(
                                        f"""
                                        <div class="glass-card">
                                            <span class="citation-badge">Source {idx}</span>
                                            <span class="citation-badge">📄 {src['filename']}</span>
                                            <span class="citation-badge">📍 Page {src['page']}</span>
                                            {score_badge}
                                            <p style="margin-top: 8px; font-size: 0.85rem; line-height: 1.55;">
                                                {src['snippet']}
                                            </p>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": full_response,
                                "sources": serialized_sources,
                                "graph_facts": kg_matched,
                                "telemetry": telemetry_data,
                            }
                        )

                    except Exception as e:
                        st.error(
                            f"Generation Error: {e}\n\nVerify `ollama pull {llm_model}` and `ollama pull {EMBEDDING_MODEL}` have completed."
                        )


# =============================================================================
# VIEW 2: DOCUMENT READER, CHUNK INSPECTOR & KNOWLEDGE GRAPH EXPLORER
# =============================================================================
@st.fragment
def render_document_reader():
    st.markdown("#### 📖 Document Reader, Vector Chunks & Knowledge Graph Explorer")
    pdf_files = list_documents()

    if not pdf_files:
        st.info("No PDF files found in the `data/` directory yet.")
        return

    reader_col1, reader_col2 = st.columns([1.6, 1.4])
    with reader_col1:
        selected_pdf_path = st.selectbox(
            "Select a Stored PDF from `data/`",
            options=pdf_files,
            format_func=lambda p: p.name,
        )
    with reader_col2:
        view_mode = st.radio(
            "Inspector Mode",
            options=[
                "📄 Visual Page",
                "🧩 Vector Chunks",
                "🕸️ Knowledge Graph Triplets",
            ],
            horizontal=True,
        )

    if view_mode == "🕸️ Knowledge Graph Triplets":
        n_nodes, n_edges, all_triplets = get_cached_knowledge_graph_stats()
        st.markdown(
            f"Showing **{n_edges}** extracted relationships across **{n_nodes}** entities in `knowledge_graph.graphml`:"
        )
        kg_filter = st.text_input(
            "🔎 Filter Knowledge Graph entities or relations",
            placeholder="e.g., Character name, LOCATED_IN, REQUIRES...",
        )
        filtered_t = [
            t
            for t in all_triplets
            if not kg_filter.strip()
            or kg_filter.lower() in t["source"].lower()
            or kg_filter.lower() in t["relation"].lower()
            or kg_filter.lower() in t["target"].lower()
        ]
        if not filtered_t:
            st.info(
                "No Knowledge Graph triplets found yet. Upload or sync a PDF to extract entities."
            )
        else:
            for idx, t in enumerate(filtered_t[:60], 1):
                st.markdown(
                    f"""
                    <div class="glass-card" style="padding: 0.65rem 1rem;">
                        <span class="citation-badge">Triplet #{idx}</span>
                        <span class="kg-badge">{t['source']}</span>
                        <span style="font-size:0.82rem; color:var(--text-sec); font-weight:600;">
                            ──[ {t['relation']} ]──▶
                        </span>
                        <span class="kg-badge" style="margin-left:6px;">{t['target']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        return

    if selected_pdf_path and selected_pdf_path.exists():
        doc_pdf = fitz.open(str(selected_pdf_path))
        num_pages = len(doc_pdf)

        if view_mode == "📄 Visual Page":
            ctrl_col1, ctrl_col2 = st.columns([1, 2])
            with ctrl_col1:
                page_num = st.number_input(
                    f"Page (1 to {num_pages})",
                    min_value=1,
                    max_value=max(1, num_pages),
                    value=1,
                )
            with ctrl_col2:
                keyword_search = st.text_input(
                    "🔎 Search keyword inside this PDF",
                    placeholder="Search character, chapter, or module code...",
                )

            if keyword_search.strip():
                matches = []
                for p_idx in range(num_pages):
                    txt = doc_pdf[p_idx].get_text("text")
                    if keyword_search.lower() in txt.lower():
                        matches.append(p_idx + 1)
                if matches:
                    st.success(
                        f"Found **'{keyword_search}'** on Page(s): {', '.join(map(str, matches[:25]))}"
                    )
                else:
                    st.warning(f"No exact match found for '{keyword_search}'.")

            page_obj = doc_pdf[page_num - 1]
            pix = page_obj.get_pixmap(dpi=130)
            img_bytes = pix.tobytes("png")
            extracted_text = page_obj.get_text("text")

            vis_col, txt_col = st.columns([1.15, 1])
            with vis_col:
                st.markdown(f"**Page {page_num} Visual Render**")
                st.image(img_bytes, use_container_width=True)
            with txt_col:
                st.markdown(f"**Page {page_num} Extracted Raw Text (PyMuPDF)**")
                st.text_area(
                    "Extracted Text",
                    value=extracted_text
                    if extracted_text.strip()
                    else "[No extractable text on this page]",
                    height=600,
                    label_visibility="collapsed",
                )
        else:
            vs = get_cached_vectorstore()
            raw_bytes = selected_pdf_path.read_bytes()
            f_hash = hashlib.sha256(raw_bytes).hexdigest()
            chunk_data = vs.get(
                where={"file_hash": f_hash}, include=["documents", "metadatas"]
            )
            docs_list = chunk_data.get("documents", [])
            metas_list = chunk_data.get("metadatas", [])

            st.markdown(
                f"Showing **{len(docs_list)}** indexed chunks (2,500-char size) in ChromaDB for `{selected_pdf_path.name}`:"
            )
            for idx, (c_text, c_meta) in enumerate(
                zip(docs_list[:30], metas_list[:30]), 1
            ):
                p_no = c_meta.get("page", 0) + 1
                st.markdown(
                    f"""
                    <div class="glass-card">
                        <span class="citation-badge">Chunk #{idx}</span>
                        <span class="citation-badge">Page {p_no}</span>
                        <span class="citation-badge">{len(c_text)} chars</span>
                        <p style="margin-top: 8px; font-size: 0.85rem; white-space: pre-wrap;">{c_text}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        doc_pdf.close()


if st.session_state.active_view == "📖 Document & Knowledge Graph Explorer":
    render_document_reader()


# =============================================================================
# VIEW 3: DATA INGESTION & KNOWLEDGE BASE MANAGEMENT
# =============================================================================
if st.session_state.active_view == "📥 Data Ingestion Hub":
    st.markdown("#### 📥 Feed Documents & Novels into the RAG + Knowledge Graph Pipeline")
    st.write(
        "Upload novels, story manuscripts, or university handbooks. Each PDF is SHA-256 fingerprinted, "
        "split into **2,500-character chunks** for fast high-volume ingestion, embedded with `qwen3-embedding:0.6b`, "
        "and parsed by `LLMGraphTransformer` to build the NetworkX Knowledge Graph."
    )

    main_uploads = st.file_uploader(
        "Drag and drop PDF files here",
        type=["pdf"],
        accept_multiple_files=True,
        key="main_tab_uploader",
    )

    if main_uploads:
        if st.button("🚀 Start Ingestion & Knowledge Graph Pipeline", use_container_width=True):
            progress = st.progress(0)
            for idx, uploaded_pdf in enumerate(main_uploads, 1):
                try:
                    with st.spinner(
                        f"Indexing {uploaded_pdf.name} (2,500-char chunks + Knowledge Graph extraction)..."
                    ):
                        res_message = ingest_pdf(uploaded_pdf)
                        st.success(f"✅ {res_message}")
                except Exception as exc:
                    st.error(f"❌ Failed on {uploaded_pdf.name}: {exc}")
                progress.progress(idx / len(main_uploads))
            clear_all_data_caches()
            time.sleep(0.4)
            st.rerun()

    st.divider()
    st.markdown("#### 🗂️ Indexed Knowledge Base Inventory")

    if not doc_chunk_map:
        st.info("No documents are currently indexed in ChromaDB.")
    else:
        for fname, count in sorted(doc_chunk_map.items()):
            col_info, col_action = st.columns([4, 1])
            with col_info:
                st.markdown(
                    f"""
                    <div class="glass-card" style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <b>📄 {fname}</b><br>
                            <span style="font-size:0.8rem; color:var(--text-sec);">Collection: {COLLECTION}</span>
                        </div>
                        <span class="citation-badge">{count} Vector Chunks</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_action:
                if st.button("🗑️ Remove", key=f"del_{fname}", use_container_width=True):
                    vs = get_cached_vectorstore()
                    existing = vs.get(where={"filename": fname}, include=["metadatas"])
                    if existing.get("ids"):
                        deleted_hashes = list(
                            {
                                m.get("file_hash", "")
                                for m in existing.get("metadatas", [])
                                if m and m.get("file_hash")
                            }
                        )
                        vs.delete(ids=existing["ids"])
                        remove_file_from_knowledge_graph(deleted_hashes)
                    for p in list_documents():
                        if p.name.endswith(fname):
                            p.unlink(missing_ok=True)
                    clear_all_data_caches()
                    st.rerun()