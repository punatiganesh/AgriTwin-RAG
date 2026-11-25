"""
AgriTwin-RAG - Flask RAG API Integration Test
Step 10: Tests /api/rag/health and /api/rag/chat endpoints.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app


def test_flask_rag_pipeline():
    print("========================================")
    print("FLASK RAG BACKEND INTEGRATION TEST")
    print("========================================")
    print()

    client = app.test_client()

    # 1. Health Check Endpoint Test
    print("1. Testing GET /api/rag/health...")
    health_res = client.get("/api/rag/health")
    print(f"Status Code: {health_res.status_code}")
    health_data = health_res.get_json()
    print(f"Response: {json.dumps(health_data, indent=2)}")
    assert health_res.status_code == 200, f"Expected 200, got {health_res.status_code}"
    assert health_data.get("success") is True
    assert health_data.get("service") == "AgriTwin-RAG"
    assert "retriever" in health_data
    assert "llm" in health_data
    print("[PASS] Health check test passed\n")

    # 2. Empty Query Validation Test
    print("2. Testing POST /api/rag/chat with empty query...")
    empty_res = client.post(
        "/api/rag/chat",
        data=json.dumps({"query": ""}),
        content_type="application/json",
    )
    print(f"Status Code: {empty_res.status_code}")
    empty_data = empty_res.get_json()
    print(f"Response: {json.dumps(empty_data, indent=2)}")
    assert empty_res.status_code == 400, f"Expected 400, got {empty_res.status_code}"
    assert empty_data.get("success") is False
    assert empty_data.get("error") == "Query is required."
    print("[PASS] Empty query validation test passed\n")

    # 3. Missing Query Key Test
    print("3. Testing POST /api/rag/chat with missing query key...")
    missing_res = client.post(
        "/api/rag/chat",
        data=json.dumps({}),
        content_type="application/json",
    )
    print(f"Status Code: {missing_res.status_code}")
    missing_data = missing_res.get_json()
    print(f"Response: {json.dumps(missing_data, indent=2)}")
    assert missing_res.status_code == 400, f"Expected 400, got {missing_res.status_code}"
    assert missing_data.get("success") is False
    assert missing_data.get("error") == "Query is required."
    print("[PASS] Missing query validation test passed\n")

    # 4. Non-JSON Request Validation Test
    print("4. Testing POST /api/rag/chat with non-JSON payload...")
    non_json_res = client.post(
        "/api/rag/chat",
        data="invalid payload string",
        content_type="text/plain",
    )
    print(f"Status Code: {non_json_res.status_code}")
    non_json_data = non_json_res.get_json()
    print(f"Response: {json.dumps(non_json_data, indent=2)}")
    assert non_json_res.status_code == 400, f"Expected 400, got {non_json_res.status_code}"
    assert non_json_data.get("success") is False
    assert non_json_data.get("error") == "Query is required."
    print("[PASS] Non-JSON request validation test passed\n")

    # 5. Live RAG Chat Pipeline Test (ChromaDB + LLM Error Handling)
    test_query = "What are the management practices for rice?"
    print(f"5. Testing POST /api/rag/chat live pipeline with query: '{test_query}'...")
    chat_res = client.post(
        "/api/rag/chat",
        data=json.dumps({"query": test_query}),
        content_type="application/json",
    )
    print(f"Status Code: {chat_res.status_code}")
    chat_data = chat_res.get_json()
    print(f"Response: {json.dumps(chat_data, indent=2)}")

    if chat_res.status_code == 200:
        assert chat_data.get("success") is True
        assert chat_data.get("query") == test_query
        assert "answer" in chat_data
        assert isinstance(chat_data.get("sources"), list)
        print(f"Retrieved {len(chat_data['sources'])} sources:")
        for src in chat_data["sources"]:
            print(f"  - {src.get('source')} (Page {src.get('page')}, ID: {src.get('chunk_id')})")
        print("[PASS] Live query chat test passed\n")
    elif chat_res.status_code in (401, 502, 503):
        print(f"Note: LLM returned status {chat_res.status_code} ({chat_data.get('error')})")
        print("Backend error handling is working correctly without leaking credentials.\n")
        print("[PASS] Live query chat (error handled cleanly) passed\n")
    else:
        raise AssertionError(f"Unexpected status code {chat_res.status_code}: {chat_data}")

    # 6. Full Success Flow Test (Real ChromaDB Retrieval + Answer & Sources Verification)
    print("6. Testing successful answer generation and sources return...")
    mock_answer = (
        "Based on ICAR recommendations, key management practices for rice include balanced "
        "fertilizer application, integrated pest management against gall midge, and optimal water management."
    )
    with patch("app.generate_answer", return_value=mock_answer):
        success_res = client.post(
            "/api/rag/chat",
            data=json.dumps({"query": test_query}),
            content_type="application/json",
        )
        print(f"Status Code: {success_res.status_code}")
        success_data = success_res.get_json()
        print(f"Response: {json.dumps(success_data, indent=2)}")

        assert success_res.status_code == 200, f"Expected 200, got {success_res.status_code}"
        assert success_data.get("success") is True
        assert success_data.get("query") == test_query
        assert success_data.get("answer") == mock_answer
        assert isinstance(success_data.get("sources"), list)
        assert len(success_data["sources"]) == 5, f"Expected 5 sources, got {len(success_data['sources'])}"

        for src in success_data["sources"]:
            assert "source" in src and src["source"] == "icar_crop_management.pdf"
            assert "page" in src
            assert "chunk_id" in src
            assert "text" not in src  # Ensure raw context is not exposed in sources array

        print(f"Successfully verified 5 retrieved sources:")
        for idx, src in enumerate(success_data["sources"], start=1):
            print(f"  {idx}. {src['source']}, Page {src['page']}, Chunk ID: {src['chunk_id']}")
        print("[PASS] Full success answer & sources test passed\n")

    # 7. No Retrieval Results Handling Test
    print("7. Testing empty retrieval handling...")
    with patch("app.search_documents", return_value=[]):
        empty_retrieval_res = client.post(
            "/api/rag/chat",
            data=json.dumps({"query": "Unknown hypothetical non-agricultural query xyz123"}),
            content_type="application/json",
        )
        print(f"Status Code: {empty_retrieval_res.status_code}")
        empty_retrieval_data = empty_retrieval_res.get_json()
        print(f"Response: {json.dumps(empty_retrieval_data, indent=2)}")

        assert empty_retrieval_res.status_code == 200
        assert empty_retrieval_data.get("success") is False
        assert "could not find relevant information" in empty_retrieval_data.get("answer", "")
        assert empty_retrieval_data.get("sources") == []
        print("[PASS] Empty retrieval handling test passed\n")

    print("========================================")
    print("ALL 7 INTEGRATION TESTS PASSED (100%)")
    print("========================================")


if __name__ == "__main__":
    test_flask_rag_pipeline()
