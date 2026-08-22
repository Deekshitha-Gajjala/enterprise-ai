# ============================================================
# UPLOAD PDF TO PINECONE
# backend/app/upload_to_pinecone.py
# ============================================================

from pathlib import Path

from pypdf import PdfReader

from chunker import split_text
from pinecone_store import index_pdf_chunks, get_pinecone_stats


# ============================================================
# FIND PDF
# ============================================================

UPLOADS_DIR = Path("uploads")

pdf_files = list(
    UPLOADS_DIR.glob("*.pdf")
)

if not pdf_files:
    raise FileNotFoundError(
        "No PDF files found in uploads/"
    )

print(
    f"Found {len(pdf_files)} PDF file(s)."
)


# ============================================================
# PROCESS EACH PDF
# ============================================================

total_uploaded = 0


for pdf_path in pdf_files:

    print()
    print(
        "========================================"
    )

    print(
        f"Processing: {pdf_path.name}"
    )

    print(
        "========================================"
    )


    # --------------------------------------------------------
    # READ PDF
    # --------------------------------------------------------

    reader = PdfReader(
        str(pdf_path)
    )

    chunks = []


    # --------------------------------------------------------
    # EXTRACT + CHUNK
    # --------------------------------------------------------

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        try:

            raw_text = (
                page.extract_text()
                or ""
            )

        except Exception as error:

            print(
                f"Could not read page "
                f"{page_number}: {error}"
            )

            continue


        text = " ".join(
            raw_text.split()
        )


        if not text:
            continue


        page_chunks = split_text(
            text,
            chunk_size=1000,
            overlap=200,
        )


        for chunk_number, chunk in enumerate(
            page_chunks
        ):

            chunks.append(
                {
                    "text": chunk,
                    "filename": pdf_path.name,
                    "page": page_number,
                    "chunk": chunk_number,
                }
            )


    print(
        f"Extracted {len(chunks)} chunks."
    )


    if not chunks:

        print(
            f"Skipping {pdf_path.name}: "
            "no text found."
        )

        continue


    # --------------------------------------------------------
    # INDEX USING FASTEMBED
    # --------------------------------------------------------

    uploaded = index_pdf_chunks(
        filename=pdf_path.name,
        chunks=chunks,
    )


    print(
        f"[PINECONE] Indexed "
        f"{uploaded} chunks for "
        f"{pdf_path.name}"
    )


    total_uploaded += uploaded


# ============================================================
# VERIFY
# ============================================================

print()
print(
    "========================================"
)

print(
    "PDF UPLOAD TO PINECONE COMPLETE"
)

print(
    "========================================"
)

print()
print(
    "Total vectors uploaded:",
    total_uploaded,
)

print()
print(
    "Pinecone statistics:"
)

print(
    get_pinecone_stats()
)

print()
print("Done!")