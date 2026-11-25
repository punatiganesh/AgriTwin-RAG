import pickle
from pathlib import Path

import chromadb

EMBEDDINGS_PATH = Path(__file__).resolve().parent / "embedded_chunks.pkl"
CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"
COLLECTION_NAME = "agriculture_knowledge"


def load_embedded_chunks(path: Path):
    with path.open("rb") as infile:
        data = pickle.load(infile)

    if not isinstance(data, list):
        raise ValueError(f"Expected a list of embedded chunks in {path}, got {type(data).__name__}")

    return data


def main() -> None:
    try:
        if not EMBEDDINGS_PATH.exists():
            print(f"ERROR: Input file not found: {EMBEDDINGS_PATH}")
            raise SystemExit(1)

        embedded_chunks = load_embedded_chunks(EMBEDDINGS_PATH)
        if not embedded_chunks:
            raise ValueError("No embedded chunks available to store.")

        CHROMA_PATH.mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_or_create_collection(name=COLLECTION_NAME)

        new_count = 0
        skipped_count = 0

        for record in embedded_chunks:
            chunk_id = record.get("chunk_id")
            text = record.get("text", "")
            embedding = record.get("embedding")
            source = record.get("source")
            page = record.get("page")

            if not chunk_id:
                raise ValueError("Embedded chunk missing chunk_id.")
            if not text or not str(text).strip():
                raise ValueError(f"Embedded chunk {chunk_id} has empty text.")
            if embedding is None:
                raise ValueError(f"Embedded chunk {chunk_id} has no embedding.")
            if len(embedding) != 384:
                raise ValueError(
                    f"Embedded chunk {chunk_id} has dimension {len(embedding)}, expected 384."
                )

            existing = collection.get(ids=[chunk_id], include=[])
            if existing and chunk_id in existing.get("ids", []):
                skipped_count += 1
                continue

            collection.add(
                ids=[chunk_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[{
                    "source": source,
                    "page": page,
                    "chunk_id": chunk_id,
                }],
            )
            new_count += 1

        total_documents = collection.count()

        if total_documents == 0:
            raise ValueError("ChromaDB collection is empty after insertion.")

        print("========================================")
        print("AgriTwin-RAG CHROMADB STORAGE")
        print("========================================")
        print("Database:")
        print("rag/chroma_db/")
        print("Collection:")
        print(COLLECTION_NAME)
        print("Input chunks:")
        print(len(embedded_chunks))
        print("New chunks added:")
        print(new_count)
        print("Existing chunks skipped:")
        print(skipped_count)
        print("Total documents in collection:")
        print(total_documents)
        print("========================================")
        print("CHROMADB STORAGE COMPLETE")
        print("========================================")

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
