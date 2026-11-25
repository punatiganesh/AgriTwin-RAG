import time
print("1. start", flush=True)
t0 = time.time()
import chromadb
print(f"2. chromadb imported in {time.time()-t0:.2f}s", flush=True)
t0 = time.time()
from sentence_transformers import SentenceTransformer
print(f"3. sentence_transformers imported in {time.time()-t0:.2f}s", flush=True)
t0 = time.time()
from rag.retriever import search_documents
print(f"4. retriever imported in {time.time()-t0:.2f}s", flush=True)
t0 = time.time()
from rag.llm_service import generate_answer
print(f"5. llm_service imported in {time.time()-t0:.2f}s", flush=True)
t0 = time.time()
from rag.farm_context import format_farm_context_block
print(f"6. farm_context imported in {time.time()-t0:.2f}s", flush=True)
