# ============================================================
# PINECONE VECTOR STORE
# backend/app/pinecone_store.py
# ============================================================

import os
import hashlib
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer


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

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

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
    "[PINECONE] Loading embedding model..."
)

embedding_model = SentenceTransformer(
    MODEL_NAME
)

print(
    "[PINECONE] Embedding model loaded."
)


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
        str(chunk.get("text", "")).strip()
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

    embeddings = embedding_model.encode(
        [
            item[1]
            for item in valid_items
        ],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    if embeddings.shape[1] != DIMENSION:
        raise ValueError(
            f"Expected {DIMENSION}-dimensional "
            f"embeddings, got {embeddings.shape[1]}"
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

                "values": embedding.tolist(),

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

    # --------------------------------------------------------
    # Create query embedding
    # --------------------------------------------------------

    query_embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]

    if query_embedding.shape[0] != DIMENSION:

        raise ValueError(
            f"Expected query dimension "
            f"{DIMENSION}, got "
            f"{query_embedding.shape[0]}"
        )

    # --------------------------------------------------------
    # Retrieve MORE candidates than we finally need.
    #
    # This is important when multiple PDFs are uploaded.
    # --------------------------------------------------------

    candidate_k = max(
        int(top_k) * 5,
        30,
    )

    search_kwargs = {
        "vector": query_embedding.tolist(),

        "top_k": candidate_k,

        "include_metadata": True,
    }

    # --------------------------------------------------------
    # Optional filename filter
    # --------------------------------------------------------

    if filename:

        search_kwargs["filter"] = {
            "filename": {
                "$eq": filename
            }
        }

    # --------------------------------------------------------
    # Search Pinecone
    # --------------------------------------------------------

    result = index.query(
        **search_kwargs
    )

    matches = []

    # --------------------------------------------------------
    # Convert Pinecone results
    # --------------------------------------------------------

    for match in result.matches:

        metadata = (
            match.metadata
            or {}
        )

        text = str(
            metadata.get(
                "text",
                "",
            )
        ).strip()

        matched_filename = str(
            metadata.get(
                "filename",
                "",
            )
        )

        if not text:
            continue

        matches.append(
            {
                "text": text,

                "filename": matched_filename,

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

    # --------------------------------------------------------
    # Filename-aware reranking
    #
    # This helps when the user's question mentions a
    # particular uploaded PDF/module.
    #
    # Example:
    #
    # "What is the ML Unit 2 PDF about?"
    #
    # A filename such as:
    #
    # ML Unit 2.2 Solved Problems.pdf
    #
    # receives a boost.
    # --------------------------------------------------------

    query_words = set(
        query.lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace(".", " ")
        .split()
    )

    # Words that are too generic to help identify a PDF.
    ignored_words = {
        "what",
        "is",
        "the",
        "a",
        "an",
        "about",
        "explain",
        "tell",
        "me",
        "this",
        "that",
        "pdf",
        "document",
        "according",
        "to",
        "in",
        "of",
        "and",
        "or",
        "please",
    }

    useful_query_words = {
        word
        for word in query_words
        if word not in ignored_words
        and len(word) > 1
    }

    for match in matches:

        filename_text = (
            match["filename"]
            .lower()
            .replace("_", " ")
            .replace("-", " ")
            .replace(".", " ")
        )

        filename_words = set(
            filename_text.split()
        )

        filename_overlap = (
            useful_query_words
            & filename_words
        )

        # Small but meaningful filename boost.
        match["rerank_score"] = (
            match["score"]
            + (
                0.12
                * len(filename_overlap)
            )
        )

    # --------------------------------------------------------
    # Sort using reranked score
    # --------------------------------------------------------

    matches.sort(
        key=lambda item: item[
            "rerank_score"
        ],
        reverse=True,
    )

    # --------------------------------------------------------
    # Return only requested number of results
    # --------------------------------------------------------

    final_matches = matches[
        :int(top_k)
    ]

    # --------------------------------------------------------
    # Remove internal reranking field
    # --------------------------------------------------------

    for match in final_matches:

        match.pop(
            "rerank_score",
            None,
        )

    return final_matches


# ============================================================
# STATISTICS
# ============================================================

def get_pinecone_stats():

    return index.describe_index_stats()