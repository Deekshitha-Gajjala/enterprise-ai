# ============================================================
# ENTERPRISE AI - MAIN BACKEND
# backend/app/main.py
# ============================================================

import os
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOCAL IMPORTS
# ============================================================

from .llm import (
    generate_chat_answer,
    generate_document_answer,
)

from .vector_store import VectorStore

from .pdf_processor import extract_pdf_chunks


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "uploads"

VECTOR_DB_DIR = BASE_DIR / "vector_db"

DATA_DIR = BASE_DIR / "data"

CHATS_FILE = DATA_DIR / "chats.json"


UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

VECTOR_DB_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Enterprise AI",
    description="Enterprise AI Document Assistant",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# GLOBAL VECTOR STORE
# ============================================================

vector_store: Optional[VectorStore] = None


# ============================================================
# CHAT STORAGE
# ============================================================

chats: Dict[str, Dict[str, Any]] = {}


# ============================================================
# LOAD CHATS
# ============================================================

def load_chats():

    global chats

    if not CHATS_FILE.exists():

        chats = {}

        return

    try:

        with open(
            CHATS_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):

            chats = data

        else:

            chats = {}

    except Exception as error:

        print(
            "[CHATS] Failed to load chats:",
            error,
        )

        chats = {}


# ============================================================
# SAVE CHATS
# ============================================================

def save_chats():

    try:

        with open(
            CHATS_FILE,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                chats,
                file,
                indent=2,
                ensure_ascii=False,
            )

    except Exception as error:

        print(
            "[CHATS] Failed to save chats:",
            error,
        )


# ============================================================
# CREATE CHAT
# ============================================================

def create_chat(
    first_message: str = "",
):

    chat_id = str(
        uuid.uuid4()
    )

    title = (
        first_message.strip()[:40]
        if first_message
        else "New chat"
    )

    chats[chat_id] = {

        "id": chat_id,

        "title": title,

        "created_at": datetime.now().isoformat(),

        "updated_at": datetime.now().isoformat(),

        "messages": [],
    }

    save_chats()

    return chats[chat_id]


# ============================================================
# GET OR CREATE CHAT
# ============================================================

def get_or_create_chat(
    chat_id: Optional[str],
    first_message: str = "",
):

    if chat_id and chat_id in chats:

        return chats[chat_id]

    return create_chat(
        first_message=first_message
    )


# ============================================================
# ADD CHAT MESSAGE
# ============================================================

def add_chat_message(
    chat: Dict[str, Any],
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None,
):

    message = {

        "role": role,

        "content": content,

        "timestamp": datetime.now().isoformat(),
    }

    if sources:

        message["sources"] = sources

    chat["messages"].append(
        message
    )

    chat["updated_at"] = (
        datetime.now().isoformat()
    )


# ============================================================
# DOCUMENT LIST
# ============================================================

def get_documents():

    documents = []

    for path in sorted(
        UPLOAD_DIR.glob("*.pdf")
    ):

        documents.append({

            # Use the stored filename as the document ID.
            # This matches the actual file saved in uploads/.
            "id": path.name,

            "filename": path.name,

            "name": path.name,

            "size": path.stat().st_size,

            "indexed": True,

        })

    return documents


# ============================================================
# REQUEST MODELS
# ============================================================

class AskRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1,
    )

    chat_id: Optional[str] = None

    history: Optional[List[Dict[str, Any]]] = None

    route: Optional[str] = None

    mode: Optional[str] = None


class ChatCreateRequest(BaseModel):

    title: Optional[str] = None


# ============================================================
# HELPER:
# IS DOCUMENT QUESTION?
# ============================================================

def is_document_question(
    question: str,
    route: Optional[str] = None,
    mode: Optional[str] = None,
) -> bool:

    # --------------------------------------------------------
    # Explicit frontend route
    # --------------------------------------------------------

    values = []

    if route:
        values.append(
            route.lower().strip()
        )

    if mode:
        values.append(
            mode.lower().strip()
        )

    for value in values:

        if value in {
            "document",
            "documents",
            "pdf",
            "document_search",
        }:

            return True

        if value in {
            "conversation",
            "chat",
            "general",
        }:

            return False

    # --------------------------------------------------------
    # Question-based detection
    # --------------------------------------------------------

    text = question.lower().strip()

    document_keywords = [

        "pdf",

        "uploaded document",

        "uploaded pdf",

        "this document",

        "the document",

        "this pdf",

        "the pdf",

        "according to the document",

        "according to the pdf",

        "from the document",

        "from the pdf",

        "in the document",

        "in the pdf",

        "document about",

        "pdf about",

        "summarize the document",

        "summarize the pdf",

        "summary of the document",

        "summary of the pdf",

        "chapter in the pdf",

        "page in the pdf",

    ]

    for keyword in document_keywords:

        if keyword in text:

            return True

    return False


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    document_count = len(
        get_documents()
    )

    vector_count = 0

    if vector_store is not None:

        try:

            vector_count = len(
                vector_store.records
            )

        except Exception:

            vector_count = 0

    return {

        "status": "ok",

        "backend": "online",

        "documents": document_count,

        "chunks": vector_count,

    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {

        "message": "Enterprise AI backend is running",

        "docs": "/docs",

        "health": "/health",

    }


# ============================================================
# DOCUMENTS
# ============================================================

@app.get("/documents")
def documents():

    return get_documents()


# ============================================================
# UPLOAD INTERNAL FUNCTION
# ============================================================

async def process_pdf_upload(
    file: UploadFile,
):

    global vector_store

    if not file:

        raise HTTPException(
            status_code=400,
            detail="No file was uploaded.",
        )

    filename = file.filename or ""

    if not filename:

        raise HTTPException(
            status_code=400,
            detail="Filename is missing.",
        )

    if not filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    # --------------------------------------------------------
    # Safe filename
    # --------------------------------------------------------

    safe_filename = Path(
        filename
    ).name

    destination = (
        UPLOAD_DIR / safe_filename
    )

    # --------------------------------------------------------
    # Save uploaded PDF
    # --------------------------------------------------------

    try:

        with open(
            destination,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

    except Exception as error:

        print(
            "[UPLOAD] Save error:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail=f"Could not save PDF: {error}",
        )

    print(
        "[UPLOAD] PDF saved:",
        destination,
    )

    # --------------------------------------------------------
    # Extract chunks
    # --------------------------------------------------------

    try:

        chunks = extract_pdf_chunks(
            str(destination)
        )

    except Exception as error:

        print(
            "[PDF] Extraction error:",
            repr(error),
        )

        # Delete broken PDF

        try:
            destination.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=f"Could not read PDF: {error}",
        )

    print(
        "[PDF] Extracted chunks:",
        len(chunks),
    )

    if not chunks:

        raise HTTPException(
            status_code=400,
            detail=(
                "The PDF contains no extractable text. "
                "It may be scanned/image-only."
            ),
        )

    # --------------------------------------------------------
    # REBUILD VECTOR DATABASE
    #
    # Important:
    # We rebuild using ALL PDFs currently in uploads.
    # --------------------------------------------------------

    try:

        all_records = []

        pdf_files = sorted(
            UPLOAD_DIR.glob("*.pdf")
        )

        for pdf_file in pdf_files:

            try:

                pdf_chunks = extract_pdf_chunks(
                    str(pdf_file)
                )

                all_records.extend(
                    pdf_chunks
                )

                print(
                    "[VECTOR] Added:",
                    pdf_file.name,
                    len(pdf_chunks),
                    "chunks",
                )

            except Exception as error:

                print(
                    "[VECTOR] Failed to process:",
                    pdf_file.name,
                    repr(error),
                )

        print(
            "[VECTOR] Rebuilding with",
            len(all_records),
            "chunks",
        )

        vector_store.rebuild(
            all_records
        )

    except Exception as error:

        print(
            "[VECTOR] Rebuild error:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail=f"Vector database error: {error}",
        )

    return {

        "success": True,

        "message": (
            f"{safe_filename} uploaded and indexed successfully."
        ),

        "filename": safe_filename,

        "chunks": len(chunks),

        "documents": get_documents(),

    }


# ============================================================
# UPLOAD ROUTE
# ============================================================

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):

    return await process_pdf_upload(
        file
    )


# ============================================================
# UPLOAD-PDF ROUTE
# ============================================================

@app.post("/upload-pdf")
async def upload_pdf_alias(
    file: UploadFile = File(...)
):

    return await process_pdf_upload(
        file
    )


# ============================================================
# FRONTEND COMPATIBILITY ROUTE
#
# YOUR FRONTEND CURRENTLY USES:
#
# POST /documents/upload
# ============================================================

@app.post("/documents/upload")
async def upload_pdf_documents(
    file: UploadFile = File(...)
):

    return await process_pdf_upload(
        file
    )


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.delete("/documents/{document_id:path}")
def delete_document(document_id: str):

    global vector_store

    # The frontend sends the stored filename as the document ID.
    # FastAPI gives us the decoded path value here.
    document_name = Path(document_id).name

    if not document_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents can be deleted.",
        )

    document_path = UPLOAD_DIR / document_name

    print("[DELETE PDF] Requested:", document_name)
    print("[DELETE PDF] Path:", document_path)

    if not document_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_name}",
        )

    # Delete the physical PDF.
    try:
        document_path.unlink()
    except Exception as error:
        print("[DELETE PDF] File deletion error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail=f"Could not delete PDF: {error}",
        )

    # Rebuild the local vector database using all PDFs
    # that are still present in uploads/.
    if vector_store is not None:
        try:
            all_records = []

            remaining_pdfs = sorted(
                UPLOAD_DIR.glob("*.pdf")
            )

            for pdf_file in remaining_pdfs:
                try:
                    pdf_chunks = extract_pdf_chunks(
                        str(pdf_file)
                    )

                    all_records.extend(pdf_chunks)

                    print(
                        "[DELETE VECTOR] Added:",
                        pdf_file.name,
                        len(pdf_chunks),
                        "chunks",
                    )

                except Exception as error:
                    print(
                        "[DELETE VECTOR] Failed to process:",
                        pdf_file.name,
                        repr(error),
                    )

            vector_store.rebuild(all_records)

            print(
                "[DELETE PDF] Vector database rebuilt:",
                len(vector_store.records),
                "chunks",
            )

        except Exception as error:
            print(
                "[DELETE PDF] Vector rebuild error:",
                repr(error),
            )

            # The PDF itself was already deleted, so report the
            # rebuild problem clearly instead of pretending deletion
            # failed.
            raise HTTPException(
                status_code=500,
                detail=(
                    "PDF was deleted, but the document search index "
                    f"could not be rebuilt: {error}"
                ),
            )

    print(
        "[DELETE PDF] Successfully deleted:",
        document_name,
    )

    return {
        "success": True,
        "message": f"{document_name} deleted successfully.",
        "filename": document_name,
        "documents": get_documents(),
    }


# ============================================================
# SEARCH DOCUMENTS
# ============================================================

@app.get("/documents/search")
def search_documents(
    q: str,
    top_k: int = 6,
):

    global vector_store

    if not q.strip():

        return []

    if vector_store is None:

        return []

    try:

        results = vector_store.search(
            q,
            top_k=top_k,
        )

        return results

    except Exception as error:

        print(
            "[SEARCH] Error:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail=f"Document search failed: {error}",
        )


# ============================================================
# ASK
# ============================================================

@app.post("/ask")
def ask_question(
    request: AskRequest,
):

    global vector_store

    question = request.question.strip()

    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    print(
        "[ASK]",
        question,
    )

    # --------------------------------------------------------
    # CHAT
    # --------------------------------------------------------

    chat = get_or_create_chat(
        request.chat_id,
        question,
    )

    # --------------------------------------------------------
    # Build history
    # --------------------------------------------------------

    history = request.history

    if history is None:

        history = []

        for message in chat.get(
            "messages",
            [],
        ):

            role = message.get(
                "role"
            )

            content = message.get(
                "content"
            )

            if role in {
                "user",
                "assistant",
            } and content:

                history.append({

                    "role": role,

                    "content": content,

                })

    # --------------------------------------------------------
    # Add user's message
    # --------------------------------------------------------

    add_chat_message(
        chat,
        "user",
        question,
    )

    save_chats()

    # --------------------------------------------------------
    # Decide route
    # --------------------------------------------------------

    document_route = is_document_question(
        question,
        request.route,
        request.mode,
    )

    print(
        "[ROUTER]",
        question,
    )

    print(
        "[ROUTER] ->",
        "DOCUMENT"
        if document_route
        else "CONVERSATION",
    )

    # ========================================================
    # DOCUMENT QUESTION
    # ========================================================

    if document_route:

        if vector_store is None:

            answer = (
                "The document search system is not ready yet. "
                "Please wait a moment and try again."
            )

            sources = []

        elif not vector_store.records:

            answer = (
                "There are no indexed PDF documents available. "
                "Please upload a PDF first."
            )

            sources = []

        else:

            try:

                results = vector_store.search(
                    question,
                    top_k=6,
                )

            except Exception as error:

                print(
                    "[SEARCH ERROR]",
                    repr(error),
                )

                answer = (
                    "I couldn't search the uploaded document "
                    "because the document index encountered an error."
                )

                sources = []

            else:

                # ------------------------------------------------
                # Build context
                # ------------------------------------------------

                context_parts = []

                sources = []

                for result in results:

                    text = str(
                        result.get(
                            "text",
                            "",
                        )
                    ).strip()

                    if not text:
                        continue

                    filename = result.get(
                        "filename",
                        "Unknown document",
                    )

                    page = result.get(
                        "page",
                        "",
                    )

                    score = result.get(
                        "score",
                        0,
                    )

                    context_parts.append(
                        f"""
Document: {filename}
Page: {page}

{text}
"""
                    )

                    sources.append({

                        "filename": filename,

                        "page": page,

                        "text": text,

                        "score": score,

                    })

                context = "\n".join(
                    context_parts
                )

                # ------------------------------------------------
                # Generate document answer
                # ------------------------------------------------

                try:

                    if context.strip():

                        answer = generate_document_answer(

                            question=question,

                            context=context,

                            history=history,

                        )

                    else:

                        answer = (
                            "I couldn't find any relevant "
                            "information in the uploaded PDF."
                        )

                except Exception as error:

                    print(
                        "[DOCUMENT LLM ERROR]",
                        repr(error),
                    )

                    answer = (
                        "I found the uploaded document, "
                        "but I could not generate an answer "
                        "from it right now."
                    )

    # ========================================================
    # NORMAL CONVERSATION
    # ========================================================

    else:

        try:

            answer = generate_chat_answer(

                question=question,

                history=history,

            )

        except Exception as error:

            print(
                "[CHAT LLM ERROR]",
                repr(error),
            )

            raise HTTPException(
                status_code=500,
                detail=f"AI generation failed: {error}",
            )

        sources = []

    # ========================================================
    # SAVE ASSISTANT RESPONSE
    # ========================================================

    add_chat_message(
        chat,
        "assistant",
        answer,
        sources=sources,
    )

    save_chats()

    # ========================================================
    # RESPONSE
    # ========================================================

    return {

        "answer": answer,

        "sources": sources,

        "chat_id": chat["id"],

        "route": (
            "DOCUMENT"
            if document_route
            else "CONVERSATION"
        ),

    }


# ============================================================
# CHATS
# ============================================================

@app.get("/chats")
def get_chats():

    result = []

    for chat in chats.values():

        result.append({

            "id": chat.get(
                "id"
            ),

            "title": chat.get(
                "title",
                "New chat",
            ),

            "created_at": chat.get(
                "created_at"
            ),

            "updated_at": chat.get(
                "updated_at"
            ),

        })

    result.sort(
        key=lambda x: x.get(
            "updated_at",
            "",
        ),
        reverse=True,
    )

    return result


# ============================================================
# CREATE CHAT
# ============================================================

@app.post("/chats")
def create_new_chat(
    request: ChatCreateRequest = ChatCreateRequest(),
):

    chat = create_chat(
        first_message=(
            request.title
            or "New chat"
        )
    )

    if request.title:

        chat["title"] = request.title

        save_chats()

    return chat


# ============================================================
# GET SINGLE CHAT
# ============================================================

@app.get("/chats/{chat_id}")
def get_chat(
    chat_id: str,
):

    chat = chats.get(
        chat_id
    )

    if not chat:

        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    return chat


# ============================================================
# DELETE CHAT
# ============================================================

@app.delete("/chats/{chat_id}")
def delete_chat(
    chat_id: str,
):

    if chat_id not in chats:

        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    del chats[chat_id]

    save_chats()

    return {

        "success": True,

        "message": "Chat deleted.",

    }


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():

    global vector_store

    print(
        "=================================================="
    )

    print(
        "Enterprise AI starting..."
    )

    print(
        "=================================================="
    )

    # --------------------------------------------------------
    # Load chats
    # --------------------------------------------------------

    load_chats()

    print(
        "[CHATS] Loaded:",
        len(chats),
    )

    # --------------------------------------------------------
    # Initialize vector store
    # --------------------------------------------------------

    try:

        print(
            "[VECTOR] Initializing vector store..."
        )

        vector_store = VectorStore(
            folder_path=str(
                VECTOR_DB_DIR
            )
        )

        print(
            "[VECTOR] Loaded:",
            len(
                vector_store.records
            ),
            "chunks",
        )

    except Exception as error:

        print(
            "[VECTOR] Initialization error:",
            repr(error),
        )

        # ----------------------------------------------------
        # Do NOT kill backend.
        # Start empty vector store if needed.
        # ----------------------------------------------------

        try:

            vector_store = VectorStore(
                folder_path=str(
                    VECTOR_DB_DIR
                )
            )

        except Exception as second_error:

            print(
                "[VECTOR] Could not initialize:",
                repr(second_error),
            )

            vector_store = None

    # --------------------------------------------------------
    # If vector DB is empty but PDFs exist,
    # rebuild automatically.
    # --------------------------------------------------------

    if vector_store is not None:

        pdf_files = list(
            UPLOAD_DIR.glob("*.pdf")
        )

        if (
            pdf_files
            and not vector_store.records
        ):

            print(
                "[VECTOR] PDFs found but index is empty."
            )

            print(
                "[VECTOR] Rebuilding vector database..."
            )

            all_records = []

            for pdf_file in pdf_files:

                try:

                    chunks = extract_pdf_chunks(
                        str(pdf_file)
                    )

                    all_records.extend(
                        chunks
                    )

                    print(
                        "[VECTOR] Processed:",
                        pdf_file.name,
                        "->",
                        len(chunks),
                        "chunks",
                    )

                except Exception as error:

                    print(
                        "[VECTOR] Failed:",
                        pdf_file.name,
                        repr(error),
                    )

            if all_records:

                try:

                    vector_store.rebuild(
                        all_records
                    )

                    print(
                        "[VECTOR] Rebuild complete:",
                        len(
                            vector_store.records
                        ),
                        "chunks",
                    )

                except Exception as error:

                    print(
                        "[VECTOR] Rebuild failed:",
                        repr(error),
                    )

    print(
        "=================================================="
    )

    print(
        "Enterprise AI backend ready."
    )

    print(
        "Health: http://127.0.0.1:8000/health"
    )

    print(
        "Docs:   http://127.0.0.1:8000/docs"
    )

    print(
        "=================================================="
    )


# ============================================================