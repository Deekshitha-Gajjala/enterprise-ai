# ============================================================
# ENTERPRISE AI - MAIN BACKEND
# backend/app/main.py
# ============================================================

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ------------------------------------------------------------
# ENVIRONMENT
# ------------------------------------------------------------

load_dotenv()

# ------------------------------------------------------------
# PINECONE
# IMPORTANT: this is the ONLY document vector system used here.
# There is NO VectorStore / SentenceTransformer import.
# ------------------------------------------------------------

from .pinecone_store import (
    delete_pdf_vectors,
    get_pinecone_stats,
    index_pdf_chunks,
    search_pinecone,
)

# ------------------------------------------------------------
# PDF + LLM
# ------------------------------------------------------------

from .pdf_processor import extract_pdf_chunks
from .llm import (
    generate_chat_answer,
    generate_document_answer,
)

# ------------------------------------------------------------
# AUTH
# ------------------------------------------------------------

from .auth import (
    create_access_token,
    create_user,
    decode_access_token,
    get_user_by_email,
    init_auth_db,
    verify_password,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
CHATS_FILE = DATA_DIR / "chats.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Enterprise AI",
    description="Enterprise AI Document Assistant",
    version="2.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# CHAT STORAGE
# ============================================================

chats: Dict[str, Dict[str, Any]] = {}


def load_chats() -> None:
    global chats

    if not CHATS_FILE.exists():
        chats = {}
        return

    try:
        with open(CHATS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Current format: dictionary keyed by chat ID.
        if isinstance(data, dict):
            chats = data
            return

        # Backward compatibility if an older version stored a list.
        if isinstance(data, list):
            chats = {
                str(item.get("id")): item
                for item in data
                if isinstance(item, dict) and item.get("id")
            }
            return

        chats = {}

    except Exception as error:
        print("[CHATS] Load error:", repr(error))
        chats = {}


def save_chats() -> None:
    try:
        with open(CHATS_FILE, "w", encoding="utf-8") as file:
            json.dump(
                chats,
                file,
                indent=2,
                ensure_ascii=False,
            )
    except Exception as error:
        print("[CHATS] Save error:", repr(error))


def now_iso() -> str:
    return datetime.now().isoformat()


def create_chat(first_message: str = "") -> Dict[str, Any]:
    chat_id = str(uuid.uuid4())
    timestamp = now_iso()

    title = (
        first_message.strip()[:45]
        if first_message and first_message.strip()
        else "New chat"
    )

    chat = {
        "id": chat_id,
        "title": title,
        "created_at": timestamp,
        "updated_at": timestamp,
        "messages": [],
    }

    chats[chat_id] = chat
    save_chats()

    return chat


def get_or_create_chat(
    chat_id: Optional[str],
    first_message: str = "",
) -> Dict[str, Any]:
    if chat_id and chat_id in chats:
        return chats[chat_id]

    return create_chat(first_message)


def add_chat_message(
    chat: Dict[str, Any],
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None,
) -> None:
    message: Dict[str, Any] = {
        "role": role,
        "content": content,
        "timestamp": now_iso(),
    }

    if sources:
        message["sources"] = sources

    chat.setdefault("messages", []).append(message)
    chat["updated_at"] = now_iso()


# ============================================================
# DOCUMENTS
# ============================================================

def get_documents() -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []

    for path in sorted(UPLOAD_DIR.glob("*.pdf")):
        try:
            size = path.stat().st_size
        except OSError:
            size = 0

        documents.append(
            {
                "id": path.name,
                "document_id": path.name,
                "filename": path.name,
                "original_name": path.name,
                "name": path.name,
                "size": size,
                "indexed": True,
            }
        )

    return documents


# ============================================================
# REQUEST MODELS
# ============================================================

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    chat_id: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    route: Optional[str] = None
    mode: Optional[str] = None
    filename: Optional[str] = None


class ChatCreateRequest(BaseModel):
    title: Optional[str] = None


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


# ============================================================
# ROUTING
# ============================================================

def is_document_question(
    question: str,
    route: Optional[str] = None,
    mode: Optional[str] = None,
    filename: Optional[str] = None,
) -> bool:
    # Selecting a document in the frontend always means document mode.
    if filename and filename.strip():
        return True

    for value in (route, mode):
        if not value:
            continue

        normalized = value.lower().strip()

        if normalized in {
            "document",
            "documents",
            "pdf",
            "document_search",
        }:
            return True

        if normalized in {
            "conversation",
            "chat",
            "general",
        }:
            return False

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
        "summarize the document",
        "summarise the document",
        "summarize the pdf",
        "summarise the pdf",
        "summary of the document",
        "summary of the pdf",
        "main topic of this pdf",
        "main topic of the pdf",
        "main topic of this document",
        "what is this pdf about",
        "what is the pdf about",
        "what is this document about",
        "what does the document say",
        "what does the pdf say",
        "chapter in the pdf",
        "page in the pdf",
    ]

    return any(keyword in text for keyword in document_keywords)


# ============================================================
# AUTH HELPERS
# ============================================================

def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization token is required.",
        )

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header.",
        )

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
        )

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=401,
            detail="Invalid token.",
        )

    user = get_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User no longer exists.",
        )

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    vector_count = 0

    try:
        stats = get_pinecone_stats()
        vector_count = int(
            getattr(stats, "total_vector_count", 0) or 0
        )
    except Exception as error:
        print("[HEALTH] Pinecone stats error:", repr(error))

    return {
        "status": "ok",
        "backend": "online",
        "documents": len(get_documents()),
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
# AUTH - REGISTER
# ============================================================

@app.post("/auth/register")
def register(request: RegisterRequest):
    email = request.email.lower().strip()

    existing = get_user_by_email(email)

    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    try:
        user = create_user(
            name=request.name,
            email=email,
            password=request.password,
        )
    except Exception as error:
        print("[AUTH] Register error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {error}",
        )

    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
    )

    return {
        "message": "Registration successful.",
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


# ============================================================
# AUTH - LOGIN
# ============================================================

@app.post("/auth/login")
def login(request: LoginRequest):
    email = request.email.lower().strip()

    user = get_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    try:
        valid = verify_password(
            request.password,
            user["password_hash"],
        )
    except Exception as error:
        print("[AUTH] Password verification error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Password verification failed.",
        )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    token = create_access_token(
        user_id=user["id"],
        email=user["email"],
    )

    safe_user = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }

    return {
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "user": safe_user,
    }


# ============================================================
# AUTH - CURRENT USER
# ============================================================

@app.get("/auth/me")
def current_user(user: Dict[str, Any] = Depends(get_current_user)):
    return user


# ============================================================
# DOCUMENT LIST
# ============================================================

@app.get("/documents")
def documents():
    return get_documents()


# ============================================================
# PDF UPLOAD
# ============================================================

async def process_pdf_upload(file: UploadFile):
    if not file:
        raise HTTPException(
            status_code=400,
            detail="No file was uploaded.",
        )

    original_filename = file.filename or ""

    if not original_filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing.",
        )

    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    safe_filename = Path(original_filename).name

    if not safe_filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    destination = UPLOAD_DIR / safe_filename

    # Save PDF.
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as error:
        print("[UPLOAD] Save error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail=f"Could not save PDF: {error}",
        )

    print("[UPLOAD] PDF saved:", destination)

    # Extract text/chunks.
    try:
        chunks = extract_pdf_chunks(str(destination))
    except Exception as error:
        print("[PDF] Extraction error:", repr(error))
        destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Could not read PDF: {error}",
        )

    if not chunks:
        destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail=(
                "The PDF contains no extractable text. "
                "It may be scanned/image-only."
            ),
        )

    print(
        f"[PDF] Extracted {len(chunks)} chunks from "
        f"{safe_filename}"
    )

    # Remove old vectors for this exact filename.
    # If the namespace does not exist yet, simply continue.
    try:
        delete_pdf_vectors(safe_filename)
    except Exception as error:
        print(
            "[PINECONE] Previous vectors could not be deleted "
            "(safe to ignore for a new PDF):",
            repr(error),
        )

    # Index new chunks.
    try:
        pinecone_count = index_pdf_chunks(
            filename=safe_filename,
            chunks=chunks,
        )
    except Exception as error:
        print("[PINECONE] Indexing error:", repr(error))

        # Do not delete the PDF if Pinecone fails; it can be
        # re-indexed after fixing the service.
        raise HTTPException(
            status_code=500,
            detail=f"Could not index PDF in Pinecone: {error}",
        )

    print(
        f"[PINECONE] Indexed {pinecone_count} chunks "
        f"for {safe_filename}"
    )

    return {
        "success": True,
        "message": f"{safe_filename} uploaded and indexed successfully.",
        "filename": safe_filename,
        "original_name": original_filename,
        "chunks": pinecone_count,
        "number_of_chunks": pinecone_count,
        "documents": get_documents(),
    }


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    return await process_pdf_upload(file)


@app.post("/upload-pdf")
async def upload_pdf_alias(file: UploadFile = File(...)):
    return await process_pdf_upload(file)


@app.post("/documents/upload")
async def upload_pdf_documents(file: UploadFile = File(...)):
    return await process_pdf_upload(file)


# ============================================================
# DELETE DOCUMENT
# ============================================================

@app.delete("/documents/{document_id:path}")
def delete_document(document_id: str):
    document_name = Path(document_id).name

    if not document_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents can be deleted.",
        )

    document_path = UPLOAD_DIR / document_name

    if not document_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_name}",
        )

    # Delete Pinecone vectors first.
    try:
        delete_pdf_vectors(document_name)
    except Exception as error:
        print(
            "[DELETE] Pinecone vector deletion warning:",
            repr(error),
        )

    # Delete physical PDF.
    try:
        document_path.unlink()
    except Exception as error:
        print("[DELETE] File deletion error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail=f"Could not delete PDF: {error}",
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
    filename: Optional[str] = None,
):
    if not q.strip():
        return []

    top_k = max(1, min(int(top_k), 20))

    try:
        return search_pinecone(
            q,
            top_k=top_k,
            filename=filename,
        )
    except Exception as error:
        print("[SEARCH] Error:", repr(error))
        raise HTTPException(
            status_code=500,
            detail=f"Document search failed: {error}",
        )


# ============================================================
# ASK QUESTION
# ============================================================

@app.post("/ask")
def ask_question(request: AskRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    print("[ASK]", question)

    # --------------------------------------------------------
    # Chat
    # --------------------------------------------------------

    chat = get_or_create_chat(
        request.chat_id,
        question,
    )

    # --------------------------------------------------------
    # History
    # --------------------------------------------------------

    if request.history is not None:
        history = request.history
    else:
        history = []

        for message in chat.get("messages", []):
            role = message.get("role")
            content = message.get("content")

            if (
                role in {"user", "assistant"}
                and content
            ):
                history.append(
                    {
                        "role": role,
                        "content": content,
                    }
                )

    # Keep prompt size reasonable.
    history = history[-10:]

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    add_chat_message(
        chat,
        "user",
        question,
    )
    save_chats()

    # --------------------------------------------------------
    # Route
    # --------------------------------------------------------

    document_route = is_document_question(
        question=question,
        route=request.route,
        mode=request.mode,
        filename=request.filename,
    )

    print(
        "[ROUTER] ->",
        "DOCUMENT" if document_route else "CONVERSATION",
    )

    # ========================================================
    # DOCUMENT RAG
    # ========================================================

    if document_route:
        try:
            top_k = 6

            results = search_pinecone(
                query=question,
                top_k=top_k,
                filename=request.filename,
            )

        except Exception as error:
            print("[PINECONE SEARCH ERROR]", repr(error))

            answer = (
                "I couldn't search the uploaded document "
                "because the document index encountered an error."
            )
            sources: List[Dict[str, Any]] = []

        else:
            if not results:
                answer = (
                    "There are no relevant indexed PDF passages "
                    "available for this question."
                )
                sources = []

            else:
                context_parts: List[str] = []
                sources = []

                for result in results:
                    text = str(
                        result.get("text", "")
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
                        f"Document: {filename}\n"
                        f"Page: {page}\n\n"
                        f"{text}"
                    )

                    sources.append(
                        {
                            "filename": filename,
                            "page": page,
                            "text": text,
                            "score": score,
                        }
                    )

                context = "\n\n---\n\n".join(
                    context_parts
                )

                if not context.strip():
                    answer = (
                        "I couldn't find relevant information "
                        "in the uploaded PDF."
                    )
                else:
                    try:
                        answer = generate_document_answer(
                            question=question,
                            context=context,
                            history=history,
                        )
                    except Exception as error:
                        print(
                            "[DOCUMENT LLM ERROR]",
                            repr(error),
                        )

                        answer = (
                            "I found relevant information in the "
                            "PDF, but the AI could not generate "
                            "the final answer right now."
                        )

    # ========================================================
    # NORMAL CHAT
    # ========================================================

    else:
        try:
            answer = generate_chat_answer(
                question=question,
                history=history,
            )
        except Exception as error:
            print("[CHAT LLM ERROR]", repr(error))

            raise HTTPException(
                status_code=500,
                detail=f"AI generation failed: {error}",
            )

        sources = []

    # --------------------------------------------------------
    # Save assistant response
    # --------------------------------------------------------

    add_chat_message(
        chat,
        "assistant",
        answer,
        sources=sources,
    )

    save_chats()

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
        result.append(
            {
                "id": chat.get("id"),
                "title": chat.get("title", "New chat"),
                "created_at": chat.get("created_at"),
                "updated_at": chat.get("updated_at"),
            }
        )

    result.sort(
        key=lambda item: item.get("updated_at", ""),
        reverse=True,
    )

    return result


@app.post("/chats")
def create_new_chat(
    request: ChatCreateRequest = ChatCreateRequest(),
):
    chat = create_chat(
        first_message=request.title or "New chat"
    )

    if request.title:
        chat["title"] = request.title
        save_chats()

    return chat


@app.get("/chats/{chat_id}")
def get_chat(chat_id: str):
    chat = chats.get(chat_id)

    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    return chat


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: str):
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
        "id": chat_id,
    }


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    print("=" * 60)
    print("Enterprise AI starting...")
    print("=" * 60)

    # Authentication database.
    try:
        init_auth_db()
        print("[AUTH] Authentication database ready.")
    except Exception as error:
        print("[AUTH] Database initialization error:", repr(error))
        raise

    # Chat history.
    load_chats()
    print("[CHATS] Loaded:", len(chats))

    # Do NOT initialize VectorStore here.
    # Do NOT load SentenceTransformer here.
    # Pinecone + FastEmbed are handled by pinecone_store.py.

    try:
        stats = get_pinecone_stats()

        print(
            "[PINECONE] Connected.",
            "vectors=",
            getattr(stats, "total_vector_count", 0),
        )
    except Exception as error:
        # Keep backend alive so /health and auth can still respond.
        print(
            "[PINECONE] Startup stats warning:",
            repr(error),
        )

    print("=" * 60)
    print("Enterprise AI backend ready.")
    print("=" * 60)


# ============================================================
# LOCAL ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
