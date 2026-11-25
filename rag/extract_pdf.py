import json
from pathlib import Path

import fitz

PDF_FILENAME = "icar_crop_management.pdf"
PDF_PATH = Path(__file__).resolve().parent / "documents" / PDF_FILENAME
OUTPUT_PATH = Path(__file__).resolve().parent / "extracted_text.json"


def extract_pdf_text(pdf_path: Path) -> list[dict]:
    """Open a PDF and extract text from every page while preserving page numbers."""
    doc = fitz.open(str(pdf_path))
    extracted_pages = []
    pages_with_text = 0
    pages_with_little_or_no_text = 0

    try:
        for page_number in range(1, doc.page_count + 1):
            page = doc[page_number - 1]
            text = page.get_text("text")
            cleaned_text = text.strip()

            if len(cleaned_text) > 50:
                pages_with_text += 1
            else:
                pages_with_little_or_no_text += 1
                if cleaned_text:
                    print(f"Warning: page {page_number} contains little extractable text.")
                else:
                    print(f"Warning: page {page_number} contains no extractable text.")

            extracted_pages.append({
                "source": PDF_FILENAME,
                "page": page_number,
                "text": text,
            })
    finally:
        doc.close()

    return extracted_pages, pages_with_text, pages_with_little_or_no_text


def main() -> None:
    try:
        if not PDF_PATH.exists():
            print(f"ERROR: PDF not found:\nrag/documents/{PDF_FILENAME}")
            raise SystemExit(1)

        extracted_pages, pages_with_text, pages_with_little_or_no_text = extract_pdf_text(PDF_PATH)

        with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
            json.dump(extracted_pages, output_file, ensure_ascii=False, indent=2)

        total_pages = len(extracted_pages)

        print("========================================")
        print("PDF TEXT EXTRACTION")
        print("========================================")
        print(f"PDF: {PDF_FILENAME}")
        print(f"Total pages: {total_pages}")
        print(f"Pages with text: {pages_with_text}")
        print(f"Pages with little/no text: {pages_with_little_or_no_text}")
        print(f"Output: rag/extracted_text.json")
        print("========================================")
        print("EXTRACTION COMPLETE")
        print("========================================")

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
