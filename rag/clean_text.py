import json
import re
from pathlib import Path


INPUT_PATH = Path(__file__).resolve().parent / "extracted_text.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "cleaned_text.json"


def normalize_whitespace(text: str) -> str:
    """Reduce excessive whitespace while preserving meaningful agricultural content."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" \n", "\n", text)
    text = re.sub(r"\n ", "\n", text)
    text = re.sub(r"(?<!\n)\n(?=[A-Za-z0-9])", " ", text)
    text = re.sub(r"(?<=[A-Za-z0-9])\n(?=\d)", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def remove_pdf_artifacts(text: str) -> str:
    """Remove obvious extraction artifacts while keeping meaningful text intact."""
    if not text:
        return ""

    text = text.replace("\u00a0", " ")
    text = re.sub(r"\b\d+\s*\n\s*\d+\s*\n\s*", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"(?<!\d)\s+-\s+(?=\d)", " - ", text)
    text = text.strip()
    return text


def clean_text_block(text: str) -> str:
    """Clean the extracted text without altering the meaning or technical content."""
    text = normalize_whitespace(text)
    text = remove_pdf_artifacts(text)
    return text.strip()


def load_extracted_pages(path: Path):
    with path.open("r", encoding="utf-8") as infile:
        data = json.load(infile)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of page records in {path}, got {type(data).__name__}")
    return data


def clean_pages(pages):
    cleaned_pages = []
    meaningful_pages = 0

    for entry in pages:
        if not isinstance(entry, dict):
            continue

        source = entry.get("source")
        page = entry.get("page")
        text = entry.get("text", "")

        cleaned_text = clean_text_block(text)

        if cleaned_text and len(cleaned_text.strip()) > 0:
            meaningful_pages += 1

        cleaned_pages.append({
            "source": source,
            "page": page,
            "text": cleaned_text,
        })

    return cleaned_pages, meaningful_pages


def main() -> None:
    try:
        if not INPUT_PATH.exists():
            print(f"ERROR: Input file not found: {INPUT_PATH}")
            raise SystemExit(1)

        pages = load_extracted_pages(INPUT_PATH)
        cleaned_pages, meaningful_pages = clean_pages(pages)

        with OUTPUT_PATH.open("w", encoding="utf-8") as outfile:
            json.dump(cleaned_pages, outfile, ensure_ascii=False, indent=2)

        print("========================================")
        print("AgriTwin-RAG TEXT CLEANING")
        print("========================================")
        print(f"Input: {INPUT_PATH.name}")
        print(f"Pages processed: {len(cleaned_pages)}")
        print(f"Pages with meaningful text: {meaningful_pages}")
        print("Cleaned text saved to:")
        print("rag/cleaned_text.json")
        print("========================================")
        print("TEXT CLEANING COMPLETE")
        print("========================================")

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
