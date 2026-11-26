from pathlib import Path
import hashlib
import re
import logging
import networkx as nx

# pyrefly: ignore[missing-import]
from langchain_community.document_loaders import PyMuPDFLoader
# pyrefly: ignore[missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter
# pyrefly: ignore[missing-import]
from langchain_ollama import OllamaEmbeddings, OllamaLLM
# pyrefly: ignore[missing-import]
from langchain_chroma import Chroma
# pyrefly: ignore[missing-import]
from langchain_experimental.graph_transformers import LLMGraphTransformer

# Setup basic logging for the ingestion pipeline
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "chroma_db"
COLLECTION = "university_knowledge"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.mkdir(parents=True, exist_ok=True)


def get_vectorstore():
    """Initialize and return the Chroma vector store."""
    try:
        embeddings = OllamaEmbeddings(model="qwen3-embedding:0.6b")
        return Chroma(
            collection_name=COLLECTION,
            embedding_function=embeddings,
            persist_directory=str(DB_PATH)
        )
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")
        raise RuntimeError(f"Vector store initialization failed: {e}")


def update_knowledge_graph(chunks, file_hash: str):
    """
    Extracts entities and relationships using the LLM and saves to NetworkX.
    Capped at 10 chunks per document to prevent local LLM timeout/freezing.
    """
    graph_path = DB_PATH / "knowledge_graph.graphml"
    
    logger.info("Extracting Knowledge Graph triplets (Limited to first 10 chunks for speed)...")
    
    try:
        llm = OllamaLLM(model="llama3.2:3b", temperature=0)
        
        # Define what the LLM should extract for both academic and narrative texts
        transformer = LLMGraphTransformer(
            llm=llm,
            allowed_nodes=["Character", "Location", "Concept", "Module", "Prerequisite", "Event"],
            allowed_relationships=["LOCATED_IN", "REQUIRES", "INTERACTS_WITH", "PART_OF", "CAUSES"]
        )
        
        # Limit to 10 chunks to avoid massive processing delays on novels
        graph_docs = transformer.convert_to_graph_documents(chunks[:10])
        
        # Load existing graph or create a new one
        if graph_path.exists():
            try:
                G = nx.read_graphml(str(graph_path))
            except Exception:
                logger.warning("Corrupted .graphml found. Creating a new Knowledge Graph.")
                G = nx.DiGraph()
        else:
            G = nx.DiGraph()
            
        # Add nodes and edges to the graph
        nodes_added = 0
        edges_added = 0
        
        for doc in graph_docs:
            for node in doc.nodes:
                G.add_node(node.id, type=node.type, source_file=file_hash)
                nodes_added += 1
            for rel in doc.relationships:
                G.add_edge(rel.source.id, rel.target.id, label=rel.type, source_file=file_hash)
                edges_added += 1
                
        # Save to disk
        nx.write_graphml(G, str(graph_path))
        logger.info(f"Knowledge Graph updated: added {nodes_added} nodes and {edges_added} edges.")
        
    except Exception as e:
        logger.error(f"Knowledge Graph extraction failed: {e}. Proceeding without graph update.")


def ingest_pdf(uploaded_file) -> str:
    """
    Save and index a PDF uploaded through Streamlit or the local sync function.
    Optimized for larger documents like novels by increasing chunk size.
    """
    try:
        pdf_bytes = uploaded_file.getvalue()
    except AttributeError:
        raise ValueError("Uploaded file must have a .getvalue() method.")

    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")

    # Use a content hash to identify duplicate documents accurately
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Clean the original filename
    filename = Path(getattr(uploaded_file, "name", "unknown.pdf")).name
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

    # Unique filename avoids overwriting other PDFs in the data directory
    saved_name = f"{file_hash[:12]}_{filename}"
    pdf_path = DATA_DIR / saved_name

    vectorstore = get_vectorstore()

    # Check whether this exact PDF has already been indexed
    try:
        existing = vectorstore.get(
            where={"file_hash": file_hash},
            limit=1
        )
        if existing and existing.get("ids"):
            return f"Already indexed: {filename}"
    except Exception as e:
        logger.warning(f"Could not verify existing documents for {filename}: {e}")

    # Save PDF to data folder
    pdf_path.write_bytes(pdf_bytes)

    try:
        # Load PDF using PyMuPDF (fastest loader)
        loader = PyMuPDFLoader(str(pdf_path))
        documents = loader.load()

        # Split into chunks - Optimized for Novels & Large Texts
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2500,  # Increased from 1000 to process novels much faster
            chunk_overlap=250
        )

        chunks = splitter.split_documents(documents)

        if not chunks:
            raise ValueError(f"No extractable text found in PDF: {filename}.")

        # Attach source metadata to every chunk for precise filtering
        for chunk in chunks:
            # Safely extract the page number, defaulting to 0 if missing
            page_num = chunk.metadata.get("page", 0)
            chunk.metadata = {
                "file_hash": file_hash,
                "filename": filename,
                "source": saved_name,
                "page": page_num
            }

        # Stable IDs prevent duplicate entries in ChromaDB
        chunk_ids = [
            f"{file_hash}_{i}"
            for i in range(len(chunks))
        ]

        logger.info(f"Adding {len(chunks)} chunks for {filename} to ChromaDB...")
        vectorstore.add_documents(
            documents=chunks,
            ids=chunk_ids
        )

        # Execute Knowledge Graph extraction
        update_knowledge_graph(chunks, file_hash)

        return f"Successfully indexed {filename} ({len(chunks)} chunks)"

    except Exception as e:
        logger.error(f"Ingestion failed for {filename}: {e}")
        # Rollback: Remove any partially indexed chunks from ChromaDB
        try:
            partial = vectorstore.get(where={"file_hash": file_hash})
            if partial and partial.get("ids"):
                vectorstore.delete(ids=partial["ids"])
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup partial vectors: {cleanup_error}")

        # Rollback: Remove the raw PDF file if ingestion failed
        pdf_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to index {filename}: {str(e)}")


def list_documents() -> list[Path]:
    """Return the PDFs currently stored in the data folder."""
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("*.pdf"))