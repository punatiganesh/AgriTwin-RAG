import json
import re
from pathlib import Path

INPUT_PATH = Path(__file__).resolve().parent / "cleaned_text.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "chunks.json"
TARGET_WORDS = 650
OVERLAP_WORDS = 120


def load_cleaned_pages(path: Path):
    with path.open("r", encoding="utf-8") as infile:
        data = json.load(infile)

    if not isinstance(data, list):
        raise ValueError(f"Expected a list of page records in {path}, got {type(data).__name__}")

    return data


def split_sentences(text: str):
    if not text:
        return []
    normalized = text.replace("\n", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    segments = re.split(r"(?<=[.!?])\s+", normalized)
    return [seg.strip() for seg in segments if seg.strip()]


def build_segments(pages):
    segments = []
    for entry in pages:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source")
        page = entry.get("page")
        text = entry.get("text", "")
        if not text or not str(text).strip():
            continue

        for sentence in split_sentences(str(text)):
            segments.append({
                "source": source,
                "page": page,
                "text": sentence,
            })

    return segments


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def get_page_label(pages_in_chunk):
    unique_pages = sorted({int(p) for p in pages_in_chunk if str(p).isdigit()})
    if not unique_pages:
        return 1
    if len(unique_pages) == 1:
        return unique_pages[0]
    return f"{unique_pages[0]}-{unique_pages[-1]}"


def chunk_segments(segments):
    chunks = []
    current_words = []
    current_pages = []
    current_source = None
    current_chunk_index = 1

    for segment in segments:
        source = segment.get("source")
        page = segment.get("page")
        sentence = segment.get("text", "").strip()

        if not sentence:
            continue

        if current_source is None:
            current_source = source

        if current_words and len(current_words) >= TARGET_WORDS:
            text = " ".join(current_words).strip()
            if text:
                chunk_id = f"{current_source.replace('.pdf', '')}_p{get_page_label(current_pages)}_{current_chunk_index:03d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "source": current_source,
                    "page": get_page_label(current_pages),
                    "text": text,
                })

                current_chunk_index += 1
                remaining = current_words[-OVERLAP_WORDS:]
                current_words = remaining
                current_pages = list(dict.fromkeys(current_pages[-OVERLAP_WORDS:]))
            else:
                current_words = []
                current_pages = []

        current_words.extend(re.findall(r"\S+", sentence))
        current_pages.append(page)

    if current_words:
        text = " ".join(current_words).strip()
        if text:
            chunk_id = f"{current_source.replace('.pdf', '')}_p{get_page_label(current_pages)}_{current_chunk_index:03d}"
            chunks.append({
                "chunk_id": chunk_id,
                "source": current_source,
                "page": get_page_label(current_pages),
                "text": text,
            })

    # Rebuild final chunks to ensure no empty chunk and to tighten oversize chunks.
    refined = []
    for idx, chunk in enumerate(chunks, start=1):
        text = chunk["text"].strip()
        if not text:
            continue
        words = re.findall(r"\S+", text)
        if len(words) > 800:
            start = 0
            while start < len(words):
                end = min(start + TARGET_WORDS, len(words))
                piece = " ".join(words[start:end]).strip()
                if piece:
                    chunk_id = f"{chunk['source'].replace('.pdf', '')}_p{chunk['page']}_{idx:03d}_{start:04d}"
                    refined.append({
                        "chunk_id": chunk_id,
                        "source": chunk["source"],
                        "page": chunk["page"],
                        "text": piece,
                    })
                start = end - OVERLAP_WORDS if end < len(words) else len(words)
        else:
            refined.append(chunk)

    return refined


def validate_chunks(chunks):
    if not chunks:
        raise ValueError("No chunks were created.")

    for chunk in chunks:
        if not chunk.get("chunk_id"):
            raise ValueError("Chunk missing chunk_id.")
        if not chunk.get("source"):
            raise ValueError("Chunk missing source metadata.")
        if "page" not in chunk:
            raise ValueError("Chunk missing page metadata.")
        if not chunk.get("text", "").strip():
            raise ValueError(f"Chunk {chunk.get('chunk_id')} has empty text.")

    total_words = sum(word_count(chunk.get("text", "")) for chunk in chunks)
    average = total_words / len(chunks)
    return len(chunks), round(average)


def main() -> None:
    try:
        if not INPUT_PATH.exists():
            print(f"ERROR: Input file not found: {INPUT_PATH}")
            raise SystemExit(1)

        cleaned_pages = load_cleaned_pages(INPUT_PATH)
        segments = build_segments(cleaned_pages)
        chunks = chunk_segments(segments)
        chunk_count, avg_words = validate_chunks(chunks)

        with OUTPUT_PATH.open("w", encoding="utf-8") as outfile:
            json.dump(chunks, outfile, ensure_ascii=False, indent=2)

        print("========================================")
        print("AgriTwin-RAG TEXT CHUNKING")
        print("========================================")
        print("Input:")
        print("rag/cleaned_text.json")
        print(f"Chunks created: {chunk_count}")
        print(f"Average chunk size: {avg_words} words")
        print("Target chunk size:")
        print("500–800 words")
        print("Target overlap:")
        print("approximately 100 words")
        print("Output:")
        print("rag/chunks.json")
        print("========================================")
        print("CHUNKING COMPLETE")
        print("========================================")

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
