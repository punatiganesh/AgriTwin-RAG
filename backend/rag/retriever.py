"""
AgriTwin-RAG - Semantic Document Retriever
Step 8: Semantic Retrieval from ChromaDB using all-MiniLM-L6-v2 embeddings.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import warnings

import chromadb
from sentence_transformers import SentenceTransformer

# Constants
MODEL_NAME = "all-MiniLM-L6-v2"
EXPECTED_DIMENSION = 384
CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"
COLLECTION_NAME = "agriculture_knowledge"

# Module-level singletons for efficient query execution
_MODEL: Optional[SentenceTransformer] = None
_COLLECTION: Optional[Any] = None


def get_embedding_model() -> SentenceTransformer:
    """Lazily load and cache the SentenceTransformer embedding model."""
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(MODEL_NAME)
    return _MODEL


def get_chroma_collection():
    """Lazily connect to ChromaDB and get the agriculture_knowledge collection."""
    global _COLLECTION
    if _COLLECTION is None:
        if not CHROMA_PATH.exists():
            raise FileNotFoundError(
                f"ChromaDB directory not found at {CHROMA_PATH}. Please run store_chroma.py first."
            )
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _COLLECTION = client.get_collection(name=COLLECTION_NAME)
    return _COLLECTION


def search_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Perform semantic search over agricultural document chunks.

    Args:
        query: Farmer's question or search query string.
        top_k: Number of most relevant passages to retrieve (default: 5).

    Returns:
        List of dictionaries with keys: text, source, page, chunk_id, distance.
    """
    if not query or not str(query).strip():
        warnings.warn("Empty query provided to search_documents.")
        return []

    model = get_embedding_model()
    collection = get_chroma_collection()

    # Generate 384-dimensional embedding for query
    query_embedding = model.encode(query)
    if len(query_embedding) != EXPECTED_DIMENSION:
        raise ValueError(
            f"Query embedding dimension {len(query_embedding)} does not match expected {EXPECTED_DIMENSION}."
        )

    # Search ChromaDB
    raw_results = collection.query(
        query_embeddings=[query_embedding.tolist() if hasattr(query_embedding, "tolist") else query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    documents = raw_results.get("documents", [[]])[0]
    metadatas = raw_results.get("metadatas", [[]])[0]
    distances = raw_results.get("distances", [[]])[0]
    ids = raw_results.get("ids", [[]])[0]

    results: List[Dict[str, Any]] = []

    for i in range(len(documents)):
        text = documents[i] if i < len(documents) else ""
        meta = metadatas[i] if i < len(metadatas) and metadatas[i] is not None else {}
        distance = distances[i] if i < len(distances) else 0.0
        chunk_id = meta.get("chunk_id") or (ids[i] if i < len(ids) else "")
        source = meta.get("source", "Unknown")
        page = meta.get("page", "Unknown")

        results.append({
            "text": text,
            "source": source,
            "page": page,
            "chunk_id": chunk_id,
            "distance": round(float(distance), 4)
        })

    if not results:
        warnings.warn(f"No results retrieved for query: '{query}'")

    return results


def main() -> None:
    test_questions = [
        "What are the management practices for rice?",
        "What irrigation practices are recommended?",
        "What does the document say about soil management?",
        "What are important crop management practices?"
    ]

    for question in test_questions:
        print("========================================")
        print("RAG RETRIEVAL TEST")
        print("========================================")
        print()
        print("Query:")
        print(question)
        print()

        results = search_documents(question, top_k=5)

        if not results:
            print("WARNING: No relevant documents found.")
            print()
            continue

        for rank, item in enumerate(results, start=1):
            print("----------------------------------------")
            print()
            print(f"Result {rank}")
            print()
            print("Source:")
            print(item["source"])
            print()
            print("Page:")
            print(item["page"])
            print()
            print("Chunk ID:")
            print(item["chunk_id"])
            print()
            print("Distance:")
            print(item["distance"])
            print()
            print("Retrieved text:")
            print(item["text"])
            print()


if __name__ == "__main__":
    main()
