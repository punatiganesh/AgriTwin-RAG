"""
AgriTwin-RAG - Embedding Model Test
Validates the availability and functionality of the embedding model (all-MiniLM-L6-v2).
"""
import sys

MODEL_NAME = "all-MiniLM-L6-v2"
TEST_TEXT = "This is an agricultural document about rice crop management."

def test_embedding_model():
    print("=" * 40)
    print("AgriTwin-RAG Embedding Model Test")
    print("=" * 40)
    print(f"Loading embedding model: {MODEL_NAME}...")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print("\nERROR: Sentence Transformers package not found or failed to import.")
        print(f"Details: {e}")
        print("Please install via: python -m pip install sentence-transformers")
        sys.exit(1)

    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        print("\nERROR: Embedding model unavailable.")
        print("Unable to load or download the embedding model. Check internet connectivity.")
        print(f"Exception details: {type(e).__name__}: {e}")
        sys.exit(1)

    try:
        embedding = model.encode(TEST_TEXT)
        dimension = len(embedding)
    except Exception as e:
        print("\nERROR: Failed to generate embedding vector.")
        print(f"Exception details: {type(e).__name__}: {e}")
        sys.exit(1)

    print("\nEmbedding model loaded successfully.\n")
    print("Embedding dimension:")
    print(dimension)
    print("\nTest completed successfully.")
    print("=" * 40)

if __name__ == "__main__":
    test_embedding_model()
