import re
import sys
import time
import hashlib
import requests
import numpy as np
import networkx as nx
from pathlib import Path
from typing import List, Dict, Any

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

# Import ingestion utilities from ingest.py
from ingest import ingest_pdf, list_documents

# Configuration matching ingest.py
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "chroma_db"
COLLECTION = "university_knowledge"

PREFERRED_LLMS = ["llama3.2:3b", "llama3.1:latest", "llama3:latest"]
EMBEDDING_MODEL = "qwen3-embedding:0.6b"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


# -----------------------------------------------------------------------------
# 1. SYSTEM VERIFICATION & AUTO-INGESTION HELPERS
# -----------------------------------------------------------------------------
class _LocalPDFAdapter:
    """Wraps a local Path object so ingest_pdf() from ingest.py can index it."""
    def __init__(self, path: Path):
        self.name = path.name
        self._bytes = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._bytes


def check_ollama_and_select_model() -> str:
    """Verify Ollama is running and pick the best installed LLM."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code != 200:
            print("Warning: Ollama server returned an unexpected status.")
            return PREFERRED_LLMS[0]

        installed = [
            m.get("name", "") for m in response.json().get("models", [])
        ]

        if EMBEDDING_MODEL not in installed:
            print(
                f"WARNING: '{EMBEDDING_MODEL}' not found in Ollama. "
                f"Run: ollama pull {EMBEDDING_MODEL}"
            )

        for candidate in PREFERRED_LLMS:
            if candidate in installed:
                return candidate

        if installed:
            # Pick first non-embedding model available
            for model_name in installed:
                if "embed" not in model_name.lower():
                    return model_name

        return PREFERRED_LLMS[0]

    except requests.exceptions.ConnectionError:
        print("CRITICAL ERROR: Ollama is not running!")
        print("Please start the Ollama application before running this script.")
        sys.exit(1)


def ensure_database_populated(vectorstore: Chroma) -> None:
    """Automatically index PDFs in data/ if ChromaDB is currently empty."""
    existing = vectorstore.get(limit=1)
    if existing.get("ids"):
        return

    pdf_files = list_documents()
    if not pdf_files:
        print(
            "WARNING: ChromaDB is empty and no PDFs were found in 'data/'. "
            "Place your university handbook PDF in the 'data/' folder."
        )
        return

    print(f"ChromaDB is empty. Auto-indexing {len(pdf_files)} PDF(s) from 'data/'...")
    for pdf_path in pdf_files:
        try:
            raw_bytes = pdf_path.read_bytes()
            file_hash = hashlib.sha256(raw_bytes).hexdigest()
            adapter = _LocalPDFAdapter(pdf_path)
            msg = ingest_pdf(adapter)
            if not pdf_path.name.startswith(file_hash[:12]):
                pdf_path.unlink(missing_ok=True)
            print(f"  -> {msg}")
        except Exception as e:
            print(f"  -> Failed to index {pdf_path.name}: {e}")


# -----------------------------------------------------------------------------
# 2. ADVANCED RAG ENGINE (HyDE + MULTI-HOP + RERANKING + COMPRESSION + KG)
# -----------------------------------------------------------------------------
class AdvancedRAGChain:
    """
    Modular Advanced RAG Pipeline implementing:
      Stage 1: Query Expansion + HyDE (Hypothetical Document Embeddings)
      Stage 2: Multi-Hop + Hybrid Retrieval (Dense MMR + Lexical TF-IDF RRF)
      Stage 3: Cross-Encoder Reranking
      Stage 4: Contextual Compression (Sentence-Level Extraction)
      Stage 4.5: Knowledge Graph Traversal
      Stage 5: Grounded LLM Answer Generation
    """

    def __init__(
        self,
        vectorstore: Chroma,
        llm: OllamaLLM,
        use_hyde: bool = True,
        use_multihop: bool = True,
        use_reranker: bool = True,
        use_compression: bool = True,
        top_k: int = 4,
    ):
        self.vectorstore = vectorstore
        self.llm = llm
        self.use_hyde = use_hyde
        self.use_multihop = use_multihop
        self.use_reranker = use_reranker
        self.use_compression = use_compression
        self.top_k = top_k

        # Load Cross-Encoder Reranker once into memory
        self.cross_encoder = None
        if self.use_reranker:
            try:
                self.cross_encoder = CrossEncoder(RERANKER_MODEL)
            except Exception as e:
                print(f"Note: CrossEncoder fallback enabled ({e}).")

        # Prompts adapted for universal document/literature use
        self.hyde_prompt = PromptTemplate.from_template(
            "You are an expert document and literature search optimizer.\n"
            "Given the user's question below, output:\n"
            "1. SUBQUERIES: Two specific search queries targeting exact names, themes, plot points, or key facts.\n"
            "2. HYDE: A concise 2-sentence hypothetical excerpt written in the tone of the document or novel that would perfectly answer the question.\n\n"
            "Question: {question}\n\n"
            "Output format:\n"
            "SUBQUERY_1: <query 1>\n"
            "SUBQUERY_2: <query 2>\n"
            "HYDE: <hypothetical passage>"
        )

        self.answer_prompt = PromptTemplate.from_template(
            "You are an expert literary assistant and document analyst. Answer the user's question accurately based ONLY on the following context.\n"
            "Cite the source filename and page number naturally (e.g., [Page X]) when stating facts, quotes, plot points, or details.\n"
            "If the answer is not present in the context, politely state that the uploaded documents do not contain that information.\n\n"
            "Context:\n{context}\n\n"
            "Question: {input}\n\n"
            "Answer:"
        )

    # --- STAGE 1: QUERY EXPANSION & HyDE ---
    def _expand_query_and_hyde(self, query: str) -> List[str]:
        search_queries = [query]
        if not self.use_hyde:
            return search_queries

        try:
            raw_expansion = self.llm.invoke(
                self.hyde_prompt.format(question=query)
            )
            for line in raw_expansion.splitlines():
                line = line.strip()
                if line.upper().startswith(("SUBQUERY_1:", "SUBQUERY_2:", "HYDE:")):
                    content = line.split(":", 1)[1].strip()
                    if content and len(content) > 5:
                        search_queries.append(content)
        except Exception:
            pass

        return search_queries[:4]

    # --- STAGE 2: HYBRID + MULTI-HOP RETRIEVAL ---
    def _hybrid_retrieve(self, queries: List[str], fetch_k: int = 12) -> List[Document]:
        doc_map: Dict[str, Document] = {}
        rrf_scores: Dict[str, float] = {}

        mmr_retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 6, "fetch_k": fetch_k},
        )

        # 2A. Dense Vector Retrieval
        for q in queries:
            try:
                dense_docs = mmr_retriever.invoke(q)
                for rank, doc in enumerate(dense_docs):
                    key = f"{doc.metadata.get('file_hash', '')}_{doc.metadata.get('page', 0)}_{hash(doc.page_content)}"
                    doc_map[key] = doc
                    rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (60 + rank + 1)
            except Exception:
                continue

        # 2B. Lexical Keyword Retrieval
        try:
            all_data = self.vectorstore.get(include=["documents", "metadatas"])
            corpus_texts = all_data.get("documents", [])
            corpus_metas = all_data.get("metadatas", [])

            if corpus_texts:
                vectorizer = TfidfVectorizer(
                    stop_words="english", ngram_range=(1, 2)
                )
                tfidf_matrix = vectorizer.fit_transform(corpus_texts)
                query_vec = vectorizer.transform([queries[0]])
                lexical_sims = cosine_similarity(query_vec, tfidf_matrix).flatten()
                top_lex_indices = np.argsort(lexical_sims)[::-1][:8]

                for rank, idx in enumerate(top_lex_indices):
                    if lexical_sims[idx] > 0.05:
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
        hop1_docs = [doc_map[k] for k in sorted_keys[:10]]

        # 2C. Multi-Hop Retrieval (Hop 2 on found entities)
        if self.use_multihop and hop1_docs:
            hop1_text = " ".join(d.page_content for d in hop1_docs[:3])
            discovered_codes = set(re.findall(r"\b[A-Z]{2}\d{3}(?:\.\d)?\b", hop1_text))
            query_codes = set(re.findall(r"\b[A-Z]{2}\d{3}(?:\.\d)?\b", queries[0].upper()))
            new_codes = list(discovered_codes - query_codes)[:3]

            if new_codes:
                hop2_query = f"{queries[0]} {' '.join(new_codes)}"
                try:
                    hop2_docs = self.vectorstore.similarity_search(hop2_query, k=4)
                    for doc in hop2_docs:
                        key = f"{doc.metadata.get('file_hash', '')}_{doc.metadata.get('page', 0)}_{hash(doc.page_content)}"
                        if key not in doc_map:
                            doc_map[key] = doc
                            hop1_docs.append(doc)
                except Exception:
                    pass

        return hop1_docs

    # --- STAGE 3: CROSS-ENCODER RERANKING ---
    def _rerank_documents(self, query: str, docs: List[Document]) -> List[Document]:
        if not docs:
            return []

        if self.use_reranker and self.cross_encoder is not None:
            try:
                pairs = [[query, doc.page_content] for doc in docs]
                scores = self.cross_encoder.predict(pairs)
                scored_docs = sorted(
                    zip(docs, scores), key=lambda x: float(x[1]), reverse=True
                )
                ranked = []
                for doc, score in scored_docs[: self.top_k]:
                    doc.metadata["rerank_score"] = round(float(score), 4)
                    ranked.append(doc)
                return ranked
            except Exception:
                pass

        return docs[: self.top_k]

    # --- STAGE 4: CONTEXTUAL COMPRESSION ---
    def _compress_documents(self, query: str, docs: List[Document]) -> List[Document]:
        if not self.use_compression or not docs:
            return docs

        compressed_docs: List[Document] = []
        query_terms = set(re.findall(r"\w+", query.lower()))

        for doc in docs:
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+|\n+", doc.page_content)
                if len(s.strip()) > 15
            ]
            if len(sentences) <= 4:
                compressed_docs.append(doc)
                continue

            if self.cross_encoder is not None:
                try:
                    pairs = [[query, s] for s in sentences]
                    s_scores = self.cross_encoder.predict(pairs)
                    keep_count = max(3, int(len(sentences) * 0.65))
                    top_indices = sorted(np.argsort(s_scores)[::-1][:keep_count])
                    kept_text = " ".join(sentences[i] for i in top_indices)
                except Exception:
                    kept_text = doc.page_content
            else:
                scored = []
                for idx, s in enumerate(sentences):
                    s_terms = set(re.findall(r"\w+", s.lower()))
                    overlap = len(query_terms & s_terms)
                    scored.append((overlap, idx))
                top_indices = sorted([idx for _, idx in sorted(scored, reverse=True)[:5]])
                kept_text = " ".join(sentences[i] for i in top_indices)

            compressed_doc = Document(
                page_content=kept_text,
                metadata=dict(doc.metadata),
            )
            compressed_docs.append(compressed_doc)

        return compressed_docs

    # --- STAGE 4.5: KNOWLEDGE GRAPH RETRIEVAL ---
    def _graph_retrieve(self, query: str) -> List[str]:
        """Search the NetworkX graph for query keywords and return connected facts."""
        graph_path = DB_PATH / "knowledge_graph.graphml"
        if not graph_path.exists():
            return []
            
        try:
            G = nx.read_graphml(str(graph_path))
        except Exception:
            return []
            
        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return []
            
        graph_facts = []
        for node in G.nodes():
            if any(word in str(node).lower() for word in query_words if len(word) > 3):
                for neighbor in G.successors(node):
                    edge_data = G.get_edge_data(node, neighbor)
                    label = edge_data.get("label", "RELATED_TO")
                    graph_facts.append(f"[{node}] {label} [{neighbor}]")
                    
                for neighbor in G.predecessors(node):
                    edge_data = G.get_edge_data(neighbor, node)
                    label = edge_data.get("label", "RELATED_TO")
                    graph_facts.append(f"[{neighbor}] {label} [{node}]")
                    
        return list(set(graph_facts))[:5]

    # --- STAGE 5: EXECUTION & GENERATION ---
    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        query = inputs.get("input", "").strip()
        t_start = time.perf_counter()

        # 1. Query Expansion + HyDE
        expanded_queries = self._expand_query_and_hyde(query)

        # 2. Multi-Hop Hybrid Retrieval
        candidate_docs = self._hybrid_retrieve(expanded_queries)

        # 3. Cross-Encoder Reranking
        reranked_docs = self._rerank_documents(query, candidate_docs)

        # 4. Contextual Compression
        final_docs = self._compress_documents(query, reranked_docs)

        # 4.5. Knowledge Graph Retrieval
        graph_facts = self._graph_retrieve(query)

        retrieval_time = time.perf_counter() - t_start

        # Format Context with Source & Page Citations
        context_blocks = []
        for idx, doc in enumerate(final_docs, 1):
            fname = doc.metadata.get("filename", "Document")
            page = doc.metadata.get("page", 0) + 1
            score = doc.metadata.get("rerank_score", "N/A")
            context_blocks.append(
                f"[Source {idx}: {fname} | Page {page} | Relevance Score: {score}]\n{doc.page_content}"
            )

        # Inject Graph Facts directly into the prompt context block
        if graph_facts:
            kg_string = "\n".join(f"- {fact}" for fact in graph_facts)
            context_blocks.insert(0, f"[KNOWLEDGE GRAPH FACTS]\n{kg_string}")

        context_str = (
            "\n\n---\n\n".join(context_blocks)
            if context_blocks
            else "No relevant context found in the database."
        )

        # 5. Generate Final Grounded Answer
        formatted_prompt = self.answer_prompt.format(
            context=context_str, input=query
        )
        answer = self.llm.invoke(formatted_prompt)
        total_time = time.perf_counter() - t_start

        return {
            "input": query,
            "answer": answer,
            "context": final_docs,
            "expanded_queries": expanded_queries,
            "telemetry": {
                "candidates_retrieved": len(candidate_docs),
                "final_chunks": len(final_docs),
                "graph_facts": len(graph_facts),
                "retrieval_seconds": round(retrieval_time, 2),
                "total_seconds": round(total_time, 2),
            },
        }


# -----------------------------------------------------------------------------
# 3. FACTORY FUNCTION & INTERACTIVE CLI LOOP
# -----------------------------------------------------------------------------
def get_rag_chain(
    model_name: str = None,
    use_hyde: bool = True,
    use_multihop: bool = True,
    use_reranker: bool = True,
    use_compression: bool = True,
    top_k: int = 4,
) -> AdvancedRAGChain:
    """Initialize embeddings, ChromaDB, Cross-Encoder, and Ollama LLM."""
    selected_llm = model_name or check_ollama_and_select_model()

    # 1. Setup Embeddings
    try:
        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    except Exception as e:
        raise RuntimeError(f"Failed to load embedding model: {e}")

    # 2. Connect to ChromaDB & Auto-Index data/ if empty
    DB_PATH.mkdir(parents=True, exist_ok=True)
    vectorstore = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=str(DB_PATH),
    )
    ensure_database_populated(vectorstore)

    # 3. Setup LLM
    try:
        llm = OllamaLLM(model=selected_llm, temperature=0.2)
    except Exception as e:
        raise RuntimeError(f"Failed to load LLM ({selected_llm}): {e}")

    return AdvancedRAGChain(
        vectorstore=vectorstore,
        llm=llm,
        use_hyde=use_hyde,
        use_multihop=use_multihop,
        use_reranker=use_reranker,
        use_compression=use_compression,
        top_k=top_k,
    )


def run_pipeline():
    """Execute the interactive CLI loop."""
    active_model = check_ollama_and_select_model()
    print(f"Initializing Advanced RAG Pipeline with LLM '{active_model}'...")
    print("Loading Embeddings, ChromaDB, and Cross-Encoder Reranker...")

    try:
        chain = get_rag_chain(model_name=active_model)
    except Exception as e:
        print(f"Failed to initialize pipeline: {e}")
        sys.exit(1)

    print("\n--- Advanced RAG Pipeline Ready ---")
    print("Active Modules: [HyDE] -> [Hybrid/Multi-Hop] -> [Cross-Encoder] -> [Compression] -> [Knowledge Graph]")

    while True:
        try:
            query = input("\nAsk a question (or exit): ").strip()

            if query.lower() in ["exit", "quit"]:
                print("Exiting pipeline.")
                break

            if not query:
                continue

            print("Executing retrieval pipeline...")

            response = chain.invoke({"input": query})
            telemetry = response.get("telemetry", {})
            sources = response.get("context", [])

            print(f"\nAnswer: {response.get('answer', 'No answer generated.')}")
            print(
                f"\n[Telemetry] Candidates: {telemetry.get('candidates_retrieved', 0)} -> "
                f"Reranked: {telemetry.get('final_chunks', 0)} chunks | "
                f"KG Facts: {telemetry.get('graph_facts', 0)} | "
                f"Retrieval: {telemetry.get('retrieval_seconds', 0)}s | "
                f"Total: {telemetry.get('total_seconds', 0)}s"
            )

            if sources:
                citations = [
                    f"{d.metadata.get('filename', 'Doc')} (p.{d.metadata.get('page', 0) + 1})"
                    for d in sources
                ]
                print(f"[Verified Sources] {', '.join(citations)}")

        except KeyboardInterrupt:
            print("\nExiting pipeline.")
            break
        except Exception as e:
            print(f"\nAn error occurred during generation: {e}")
            print(
                f"Ensure your models ({active_model} and {EMBEDDING_MODEL}) are pulled via Ollama."
            )


if __name__ == "__main__":
    run_pipeline()