# ============================================================
# PINECONE VECTOR STORE
# backend/app/pinecone_store.py
# ============================================================

import os
import hashlib
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from pinecone import Pinecone
from fastembed import TextEmbedding


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise RuntimeError(
        "PINECONE_API_KEY is missing from .env"
    )


# ============================================================
# CONFIGURATION
# ============================================================

INDEX_NAME = "enterprise-ai"

# Lightweight ONNX-based embedding model
MODEL_NAME = "BAAI/bge-small-en-v1.5"

DIMENSION = 384


# ============================================================
# PINECONE CLIENT
# ============================================================

print("[PINECONE] Connecting...")

pc = Pinecone(
    api_key=PINECONE_API_KEY
)

index = pc.Index(
    INDEX_NAME
)

print(
    "[PINECONE] Connected to:",
    INDEX_NAME
)


# ============================================================
# EMBEDDING MODEL
# ============================================================

print(
    "[PINECONE] Loading lightweight embedding model..."
)

embedding_model = TextEmbedding(
    model_name=MODEL_NAME
)

print(
    "[PINECONE] Embedding model loaded."
)


# ============================================================
# EMBEDDING HELPER
# ============================================================

def create_embeddings(
    texts: List[str],
):
    """
    Create normalized embeddings using FastEmbed.

    Returns:
        List[List[float]]
    """

    if not texts:
        return []

    embeddings = list(
        embedding_model.embed(texts)
    )

    result = []

    for embedding in embeddings:

        vector = embedding.tolist()

        if len(vector) != DIMENSION:
            raise ValueError(
                f"Expected {DIMENSION}-dimensional "
                f"embedding, got {len(vector)}"
            )

        result.append(vector)

    return result


# ============================================================
# CREATE UNIQUE VECTOR ID
# ============================================================

def make_vector_id(
    filename: str,
    page: int,
    chunk_index: int,
) -> str:

    raw = (
        f"{filename}|"
        f"{page}|"
        f"{chunk_index}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# INDEX PDF CHUNKS
# ============================================================

def index_pdf_chunks(
    filename: str,
    chunks: List[Dict[str, Any]],
):

    if not chunks:
        return 0

    texts = [
        str(
            chunk.get(
                "text",
                "",
            )
        ).strip()
        for chunk in chunks
    ]

    valid_items = []

    for i, text in enumerate(texts):

        if not text:
            continue

        valid_items.append(
            (
                i,
                text,
                chunks[i],
            )
        )

    if not valid_items:
        return 0

    print(
        f"[PINECONE] Creating embeddings for "
        f"{len(valid_items)} chunks..."
    )

    embeddings = create_embeddings(
        [
            item[1]
            for item in valid_items
        ]
    )

    vectors = []

    for (
        original_index,
        text,
        chunk,
    ), embedding in zip(
        valid_items,
        embeddings,
    ):

        page = int(
            chunk.get(
                "page",
                0,
            )
        )

        vector_id = make_vector_id(
            filename,
            page,
            original_index,
        )

        vectors.append(
            {
                "id": vector_id,

                "values": embedding,

                "metadata": {
                    "text": text,
                    "filename": filename,
                    "page": page,
                    "chunk_index": original_index,
                },
            }
        )

    # --------------------------------------------------------
    # Upload in batches
    # --------------------------------------------------------

    batch_size = 100

    for start in range(
        0,
        len(vectors),
        batch_size,
    ):

        batch = vectors[
            start:start + batch_size
        ]

        index.upsert(
            vectors=batch
        )

        print(
            f"[PINECONE] Uploaded "
            f"{min(start + batch_size, len(vectors))}"
            f"/{len(vectors)}"
        )

    return len(vectors)


# ============================================================
# DELETE PDF VECTORS
# ============================================================

def delete_pdf_vectors(
    filename: str,
):

    print(
        f"[PINECONE] Deleting vectors for: "
        f"{filename}"
    )

    index.delete(
        filter={
            "filename": {
                "$eq": filename
            }
        }
    )

    print(
        f"[PINECONE] Deleted vectors for: "
        f"{filename}"
    )


# ============================================================
# SEARCH
# ============================================================

def search_pinecone(
    query: str,
    top_k: int = 6,
    filename: Optional[str] = None,
):

    if not query or not query.strip():
        return []

    query_embeddings = create_embeddings(
        [query]
    )

    if not query_embeddings:
        return []

    query_embedding = query_embeddings[0]

    search_kwargs = {
        "vector": query_embedding,
        "top_k": int(top_k),
        "include_metadata": True,
    }

    if filename:

        search_kwargs["filter"] = {
            "filename": {
                "$eq": filename
            }
        }

    result = index.query(
        **search_kwargs
    )

    matches = []

    for match in result.matches:

        metadata = (
            match.metadata
            or {}
        )

        matches.append(
            {
                "text": metadata.get(
                    "text",
                    "",
                ),

                "filename": metadata.get(
                    "filename",
                    "",
                ),

                "page": metadata.get(
                    "page",
                    "",
                ),

                "score": float(
                    match.score
                ),

                "chunk_index": metadata.get(
                    "chunk_index"
                ),
            }
        )

    return matches


# ============================================================
# STATISTICS
# ============================================================

def get_pinecone_stats():

    return index.describe_index_stats()