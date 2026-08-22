import os
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

from chunker import split_text


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError(
        "PINECONE_API_KEY not found in .env"
    )

INDEX_NAME = "enterprise-ai"

PDF_PATH = Path(
    "uploads/Module_1_DL_1.pdf"
)


# ============================================================
# CHECK PDF
# ============================================================

if not PDF_PATH.exists():
    raise FileNotFoundError(
        f"PDF not found: {PDF_PATH}"
    )

print(
    "PDF found:",
    PDF_PATH
)


# ============================================================
# CONNECT TO PINECONE
# ============================================================

print("Connecting to Pinecone...")

pc = Pinecone(
    api_key=PINECONE_API_KEY
)

index = pc.Index(
    INDEX_NAME
)

print("Connected to Pinecone.")


# ============================================================
# LOAD EMBEDDING MODEL
# ============================================================

print()
print("Loading embedding model...")

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

print("Embedding model loaded.")


# ============================================================
# READ PDF
# ============================================================

print()
print("Reading PDF...")

reader = PdfReader(
    str(PDF_PATH)
)

all_chunks = []


# ============================================================
# EXTRACT + CHUNK PDF
# ============================================================

for page_number, page in enumerate(
    reader.pages,
    start=1,
):

    text = page.extract_text() or ""

    text = " ".join(
        text.split()
    )

    if not text:
        continue

    chunks = split_text(
        text,
        chunk_size=1000,
        overlap=200,
    )

    for chunk_number, chunk in enumerate(
        chunks
    ):

        all_chunks.append(
            {
                "text": chunk,
                "filename": PDF_PATH.name,
                "page": page_number,
                "chunk": chunk_number,
            }
        )


print(
    f"Extracted {len(all_chunks)} chunks."
)


if not all_chunks:
    raise ValueError(
        "No text chunks were extracted from the PDF."
    )


# ============================================================
# CREATE EMBEDDINGS
# ============================================================

print()
print("Creating embeddings...")

texts = [
    item["text"]
    for item in all_chunks
]

embeddings = model.encode(
    texts,
    normalize_embeddings=True,
    convert_to_numpy=True,
    show_progress_bar=True,
)

print(
    "Embedding shape:",
    embeddings.shape
)


# ============================================================
# PREPARE PINECONE RECORDS
# ============================================================

records = []

for item, embedding in zip(
    all_chunks,
    embeddings,
):

    record = {
        "id": (
            f"module1-page-"
            f"{item['page']}-"
            f"chunk-"
            f"{item['chunk']}"
        ),

        "values": embedding.tolist(),

        "metadata": {
            "text": item["text"],
            "filename": item["filename"],
            "page": item["page"],
            "chunk": item["chunk"],
        },
    }

    records.append(
        record
    )


# ============================================================
# UPLOAD TO PINECONE
# ============================================================

print()
print(
    f"Uploading {len(records)} vectors..."
)

batch_size = 100

for start in range(
    0,
    len(records),
    batch_size,
):

    end = min(
        start + batch_size,
        len(records),
    )

    batch = records[
        start:end
    ]

    index.upsert(
        vectors=batch
    )

    print(
        f"Uploaded {end}/{len(records)}"
    )


# ============================================================
# VERIFY
# ============================================================

print()
print("==============================")
print("PDF UPLOAD TO PINECONE COMPLETE")
print("==============================")

stats = index.describe_index_stats()

print()
print("Pinecone statistics:")
print(stats)

print()
print("Done!")