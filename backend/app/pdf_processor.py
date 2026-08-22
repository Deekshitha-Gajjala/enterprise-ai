# ============================================================
# PDF PROCESSOR
# backend/app/pdf_processor.py
# ============================================================

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_chunks(
    pdf_path: str,
    chunk_size: int = 1200,
    overlap: int = 200,
):
    """
    Extract text from a PDF and create overlapping chunks.

    Returns:

    [
        {
            "text": "...",
            "filename": "...",
            "page": 1
        }
    ]

    This version:
    - handles normal text PDFs
    - handles pages with different text layouts
    - removes excessive whitespace
    - prevents duplicate/empty chunks
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            "The uploaded file is not a PDF."
        )

    reader = PdfReader(str(path))

    chunks = []

    print(
        f"[PDF] Processing: {path.name}"
    )

    print(
        f"[PDF] Number of pages: {len(reader.pages)}"
    )

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        try:

            raw_text = page.extract_text()

        except Exception as error:

            print(
                f"[PDF] Could not extract page {page_number}:",
                error
            )

            continue

        if not raw_text:
            print(
                f"[PDF] Page {page_number}: no extractable text"
            )
            continue

        # ----------------------------------------------------
        # CLEAN TEXT
        # ----------------------------------------------------

        text = raw_text.replace(
            "\x00",
            " "
        )

        text = " ".join(
            text.split()
        )

        if not text.strip():
            print(
                f"[PDF] Page {page_number}: empty after cleaning"
            )
            continue

        print(
            f"[PDF] Page {page_number}: "
            f"{len(text)} characters"
        )

        # ----------------------------------------------------
        # CHUNK
        # ----------------------------------------------------

        start = 0

        while start < len(text):

            end = min(
                start + chunk_size,
                len(text),
            )

            chunk_text = text[
                start:end
            ].strip()

            if chunk_text:

                chunks.append(
                    {
                        "text": chunk_text,
                        "filename": path.name,
                        "page": page_number,
                    }
                )

            if end >= len(text):
                break

            next_start = end - overlap

            if next_start <= start:
                next_start = start + 1

            start = next_start

    print(
        f"[PDF] Total chunks created: {len(chunks)}"
    )

    return chunks