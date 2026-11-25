"""
AgriTwin-RAG - LLM Test Script (Groq)
Tests RAG pipeline integration: Query -> Semantic Retrieval -> Context Assembly -> Groq LLM Answer Generation.
"""
import sys
from pathlib import Path

# Ensure rag directory is on sys.path
RAG_DIR = Path(__file__).resolve().parent
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from retriever import search_documents
from llm_service import (
    build_context,
    build_user_prompt,
    extract_sources,
    generate_answer,
    get_provider_info,
    is_llm_configured,
    LLMAuthenticationError,
    LLMNotConfiguredError,
    LLMServiceError,
)


def run_llm_test():
    test_question = "What are the management practices for rice?"

    print("========================================")
    print("AgriTwin-RAG LLM TEST (Groq LLM)")
    print("========================================")
    print()
    print("Question:")
    print(test_question)
    print()

    # Step 1: Semantic Retrieval
    retrieved_chunks = search_documents(test_question, top_k=5)
    print(f"Retrieved documents from ChromaDB:\n{len(retrieved_chunks)}")
    print()

    # Step 2: Build Context & Extract Sources
    context = build_context(retrieved_chunks)
    sources = extract_sources(retrieved_chunks)

    # Step 3: Build Prompt
    prompt = build_user_prompt(test_question, context, sources)
    print(f"RAG User Prompt generated successfully ({len(prompt)} chars).\n")

    # Step 4: Check Provider Configuration & Generate Answer
    if not is_llm_configured():
        print("GROQ_API_KEY is not configured in .env.")
        print("ChromaDB retrieval is working correctly.")
        print("To generate answers with Groq, set GROQ_API_KEY in .env.")
        print()
        print("Retrieved Sources:")
        for src in sources:
            print(f"- {src}")
    else:
        info = get_provider_info()
        print(f"Provider: {info.get('provider')} (Model: {info.get('model')})")
        print("Sending prompt to Groq...\n")

        try:
            answer = generate_answer(test_question, context, sources=sources)
            print("Groq LLM Answer:")
            print(answer)
            print()
            print("Sources:")
            for src in sources:
                print(f"- {src}")

        except LLMAuthenticationError:
            print("ERROR: Groq authentication failed. Check GROQ_API_KEY credentials.")
        except LLMNotConfiguredError:
            print("GROQ_API_KEY is not configured in .env.")
        except LLMServiceError as err:
            print(f"ERROR: {err}")
        except Exception as exc:
            print(f"ERROR: Unexpected error ({type(exc).__name__}).")

    print()
    print("========================================")
    print("LLM TEST COMPLETE")
    print("========================================")


if __name__ == "__main__":
    run_llm_test()

