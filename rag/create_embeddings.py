import json
import pickle
from pathlib import Path

from sentence_transformers import SentenceTransformer

CHUNKS_PATH = Path(__file__).resolve().parent / "chunks.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "embedded_chunks.pkl"
MODEL_NAME = "all-MiniLM-L6-v2"
EXPECTED_DIMENSION = 384


def main() -> None:
    try:
        if not CHUNKS_PATH.exists():
            print(f"ERROR: Input file not found: {CHUNKS_PATH}")
            raise SystemExit(1)

        with CHUNKS_PATH.open("r", encoding="utf-8") as infile:
            chunks = json.load(infile)

        if not isinstance(chunks, list):
            raise ValueError(f"Expected a list of chunks in {CHUNKS_PATH}, got {type(chunks).__name__}")

        model = SentenceTransformer(MODEL_NAME)

        embedded_records = []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                raise ValueError("Chunk record is not a dictionary.")

            chunk_id = chunk.get("chunk_id")
            source = chunk.get("source")
            page = chunk.get("page")
            text = chunk.get("text", "")

            if not chunk_id:
                raise ValueError("Chunk missing chunk_id.")
            if not source:
                raise ValueError(f"Chunk {chunk_id} missing source metadata.")
            if page is None:
                raise ValueError(f"Chunk {chunk_id} missing page metadata.")
            if not str(text).strip():
                raise ValueError(f"Chunk {chunk_id} has empty text.")

            embedding = model.encode(text)
            embedding_size = len(embedding)

            if embedding_size != EXPECTED_DIMENSION:
                raise ValueError(
                    f"Chunk {chunk_id} produced embedding dimension {embedding_size}, expected {EXPECTED_DIMENSION}."
                )

            embedded_records.append({
                "chunk_id": chunk_id,
                "source": source,
                "page": page,
                "text": text,
                "embedding": embedding,
            })

        if len(embedded_records) != len(chunks):
            raise ValueError("Embedding count does not match chunk count.")

        for record in embedded_records:
            if "embedding" not in record or record["embedding"] is None:
                raise ValueError(f"Missing embedding for chunk {record.get('chunk_id')}")

        with OUTPUT_PATH.open("wb") as outfile:
            pickle.dump(embedded_records, outfile)

        print("========================================")
        print("AgriTwin-RAG EMBEDDING GENERATION")
        print("========================================")
        print("Input:")
        print("rag/chunks.json")
        print("Model:")
        print(MODEL_NAME)
        print("Embedding dimension:")
        print(EXPECTED_DIMENSION)
        print("Chunks:")
        print(len(chunks))
        print("Generating embeddings...")
        print("Embeddings generated:")
        print(len(embedded_records))
        print("Output:")
        print("rag/embedded_chunks.pkl")
        print("========================================")
        print("EMBEDDING GENERATION COMPLETE")
        print("========================================")

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
