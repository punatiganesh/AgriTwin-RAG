"""
AgriTwin-RAG - Retrieval Test Script
Tests semantic document retrieval against ChromaDB for agricultural queries.
"""
import sys
from pathlib import Path

# Ensure rag directory is on sys.path so 'from retriever import search_documents' works
RAG_DIR = Path(__file__).resolve().parent
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from retriever import search_documents


def run_tests():
    test_questions = [
        "What are the management practices for rice?",
        "What irrigation practices are recommended?",
        "What does the document say about soil management?",
        "What are important crop management practices?"
    ]

    print("========================================")
    print("AgriTwin-RAG RETRIEVAL TEST")
    print("========================================")

    total_passed = 0

    for query in test_questions:
        print()
        print("Query:")
        print(query)
        print()

        results = search_documents(query, top_k=5)

        if not results:
            print("WARNING: No results returned for query.")
            continue

        query_valid = True
        for rank, res in enumerate(results, start=1):
            source = res.get("source")
            page = res.get("page")
            chunk_id = res.get("chunk_id")
            distance = res.get("distance")
            text = res.get("text", "")

            # Validation checks
            if not source or not str(source).strip():
                print(f"WARNING: Result {rank} missing source metadata!")
                query_valid = False
            if page is None or str(page).strip() == "":
                print(f"WARNING: Result {rank} missing page metadata!")
                query_valid = False
            if not chunk_id or not str(chunk_id).strip():
                print(f"WARNING: Result {rank} missing chunk_id!")
                query_valid = False
            if not text or not str(text).strip():
                print(f"WARNING: Result {rank} has empty retrieved text!")
                query_valid = False

            print(f"Result {rank}")
            print(f"Source: {source}")
            print(f"Page: {page}")
            print(f"Chunk ID: {chunk_id}")
            print(f"Distance: {distance}")
            print(f"Text: {text}")
            print()

        if query_valid:
            total_passed += 1

    print("========================================")
    print("RETRIEVAL TEST COMPLETE")
    print(f"Total Queries Evaluated: {len(test_questions)}")
    print(f"Successful Retrievals: {total_passed}/{len(test_questions)}")
    print("========================================")


if __name__ == "__main__":
    run_tests()
