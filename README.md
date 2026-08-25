# Enterprise AI --- Intelligent Document Assistant

> A production-deployed full-stack RAG platform that lets authenticated
> users upload PDF documents and interact with their content through
> natural-language questions.

[![Live
Application](https://img.shields.io/badge/Live%20Application-Enterprise%20AI-6f42c1?style=for-the-badge)](https://enterprise-ai-frontend-p445.onrender.com)
[![Backend
API](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://enterprise-ai-f8pd.onrender.com)
[![API
Docs](https://img.shields.io/badge/API-Swagger%20Docs-009688?style=for-the-badge)](https://enterprise-ai-f8pd.onrender.com/docs)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/Deekshitha-Gajjala/enterprise-ai)

------------------------------------------------------------------------

## 🚀 Project Overview

Enterprise AI is a full-stack **Retrieval-Augmented Generation (RAG)**
application built to make enterprise documents searchable and
conversational.

Instead of manually searching through long PDFs, an authenticated user
can upload a document and ask questions in natural language. The system
extracts the document text, creates lightweight semantic embeddings,
stores them in Pinecone, retrieves the most relevant context for a
question, and sends that context to a Groq-powered LLM to generate an
answer.

The project was developed as an end-to-end application and deployed to
the cloud with a separately hosted React frontend and FastAPI backend.

### Core workflow

``` text
User
  ↓
React + Vite Frontend
  ↓ HTTPS REST API
FastAPI Backend
  ↓
PDF Extraction → Chunking → FastEmbed
  ↓
Pinecone Vector Database
  ↓
Semantic Retrieval
  ↓
Groq LLM
  ↓
Contextual AI Response
```

------------------------------------------------------------------------

# ⭐ Key Features

## 🔐 Authentication

-   User registration
-   User login
-   JWT-based authentication
-   Current-user endpoint
-   Password hashing
-   Environment-based authentication secret

Endpoints:

  Method   Endpoint           Purpose
  -------- ------------------ ------------------
  `POST`   `/auth/register`   Register a user
  `POST`   `/auth/login`      Login
  `GET`    `/auth/me`         Get current user

------------------------------------------------------------------------

## 📄 PDF Document Management

Users can upload PDFs through the application.

The backend:

1.  Receives the PDF
2.  Extracts text with `pypdf`
3.  Splits text into retrievable chunks
4.  Generates semantic embeddings with FastEmbed
5.  Stores vectors in Pinecone
6.  Keeps document metadata for retrieval and management

Endpoints:

  Method     Endpoint                     Purpose
  ---------- ---------------------------- ------------------
  `GET`      `/documents`                 List documents
  `POST`     `/upload`                    Upload PDF
  `POST`     `/upload-pdf`                PDF upload alias
  `POST`     `/documents/upload`          Document upload
  `DELETE`   `/documents/{document_id}`   Delete document

------------------------------------------------------------------------

# 🧠 Retrieval-Augmented Generation

The central AI capability is RAG.

A traditional LLM cannot automatically know the contents of a user's
private PDF. Enterprise AI solves this by retrieving relevant document
information before generating an answer.

### RAG process

``` text
Question
   ↓
Create Query Embedding
   ↓
Search Pinecone
   ↓
Retrieve Relevant Chunks
   ↓
Build Context
   ↓
Send Context + Question to Groq
   ↓
Generate Answer
```

### Why RAG?

RAG helps:

-   Ground answers in uploaded documents
-   Avoid sending an entire PDF to the LLM
-   Reduce unnecessary context
-   Support private/domain-specific knowledge
-   Make document QA more scalable

------------------------------------------------------------------------

# 🔎 Embedding & Vector Search

The production system uses **FastEmbed** for lightweight semantic
embeddings.

``` text
FastEmbed
   ↓
384-dimensional vectors
   ↓
Pinecone
   ↓
Cosine similarity search
```

The Pinecone index is configured for:

  Property            Value
  ------------------- -----------
  Vector database     Pinecone
  Dimension           384
  Similarity metric   Cosine
  Embedding runtime   FastEmbed

Document metadata is stored alongside vectors so retrieved chunks can be
connected back to their source document information.

------------------------------------------------------------------------

# 🤖 LLM Layer

After semantic retrieval, relevant document context is passed to a
Groq-powered LLM.

``` text
Retrieved Context
        +
User Question
        ↓
Prompt / Context Construction
        ↓
Groq LLM
        ↓
Natural-language response
```

The important design principle is:

> **Retrieve relevant information first, then generate the answer.**

This is preferable to blindly sending entire documents to the model
because it reduces unnecessary context and focuses generation on
relevant information.

------------------------------------------------------------------------

# 💬 Chat Management

The backend exposes conversation-management APIs.

  Method     Endpoint             Purpose
  ---------- -------------------- -----------------
  `GET`      `/chats`             List chats
  `POST`     `/chats`             Create a chat
  `GET`      `/chats/{chat_id}`   Retrieve a chat
  `DELETE`   `/chats/{chat_id}`   Delete a chat

This gives the frontend a clean REST interface for conversation
management.

------------------------------------------------------------------------

# 🏗️ System Architecture

``` mermaid
flowchart LR
    USER[User] --> FE[React + Vite]

    FE -->|HTTPS| API[FastAPI Backend]

    API --> AUTH[JWT Authentication]
    API --> DOCS[Document Processing]
    API --> CHAT[Chat Management]
    API --> RAG[RAG Pipeline]

    DOCS --> PDF[pypdf]
    PDF --> CHUNK[Chunking]
    CHUNK --> EMB[FastEmbed]
    EMB --> PINE[(Pinecone)]

    RAG --> EMB
    RAG --> PINE
    RAG --> GROQ[Groq LLM]

    GROQ --> API
    API --> FE
```

------------------------------------------------------------------------

# 🔄 Complete Document-to-Answer Flow

``` text
                         PDF
                          │
                          ▼
                 ┌─────────────────┐
                 │  FastAPI Upload │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ pypdf Extraction│
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ Text Chunking   │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │    FastEmbed    │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │    Pinecone     │
                 └────────┬────────┘
                          │
                          │
                    User Question
                          │
                          ▼
                 ┌─────────────────┐
                 │ Query Embedding │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ Semantic Search │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ Relevant Chunks │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │    Groq LLM     │
                 └────────┬────────┘
                          ▼
                    AI Response
```

------------------------------------------------------------------------

# 🛠️ Technology Stack

  Layer              Technology      Role
  ------------------ --------------- ----------------------------
  Frontend           React           User interface
  Build tool         Vite            Frontend build/development
  Backend            FastAPI         REST API
  Server             Uvicorn         ASGI server
  Language           Python          Backend/AI development
  LLM                Groq            AI response generation
  Vector DB          Pinecone        Semantic vector search
  Embeddings         FastEmbed       Lightweight embeddings
  PDF processing     pypdf           PDF text extraction
  Authentication     JWT             Secure authentication
  Password hashing   Passlib         Password security
  Configuration      python-dotenv   Environment variables
  Hosting            Render          Cloud deployment
  Source control     Git/GitHub      Version control

------------------------------------------------------------------------

# 📁 Repository Structure

``` text
enterprise-ai/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── pinecone_store.py
│   │   ├── upload_to_pinecone.py
│   │   └── ...
│   │
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── Login.jsx
│   │   └── ...
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── ...
│
├── .gitignore
└── README.md
```

------------------------------------------------------------------------

# ⚙️ Local Setup

## Prerequisites

-   Python 3.x
-   Node.js and npm
-   Git
-   Pinecone account/API key
-   Groq API key

------------------------------------------------------------------------

## 1. Clone the repository

``` bash
git clone https://github.com/Deekshitha-Gajjala/enterprise-ai.git
cd enterprise-ai
```

------------------------------------------------------------------------

## 2. Create the Python environment

### Windows

``` bash
python -m venv venv
venv\Scriptsctivate
```

### macOS/Linux

``` bash
python3 -m venv venv
source venv/bin/activate
```

------------------------------------------------------------------------

## 3. Install backend dependencies

``` bash
pip install -r backend/requirements.txt
```

------------------------------------------------------------------------

## 4. Configure environment variables

Create a local `.env` file:

``` env
PINECONE_API_KEY=your_pinecone_api_key
GROQ_API_KEY=your_groq_api_key
AUTH_SECRET_KEY=your_secure_random_secret
```

Generate a strong authentication secret:

``` python
import secrets
print(secrets.token_urlsafe(48))
```

Never commit `.env` or API keys to GitHub.

------------------------------------------------------------------------

## 5. Start the backend

From the repository root:

``` bash
uvicorn backend.app.main:app --reload
```

Backend:

``` text
http://127.0.0.1:8000
```

Swagger:

``` text
http://127.0.0.1:8000/docs
```

Health check:

``` text
http://127.0.0.1:8000/health
```

------------------------------------------------------------------------

## 6. Start the frontend

Open another terminal:

``` bash
cd frontend
npm install
npm run dev
```

Open the Vite URL displayed in the terminal.

------------------------------------------------------------------------

# ☁️ Production Deployment

The project is deployed as two independent Render services.

## Backend

**Type:** Render Web Service

Production URL:

https://enterprise-ai-f8pd.onrender.com

Start command:

``` bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

API documentation:

https://enterprise-ai-f8pd.onrender.com/docs

------------------------------------------------------------------------

## Frontend

**Type:** Render Static Site

Production URL:

https://enterprise-ai-frontend-p445.onrender.com

Build command:

``` bash
npm install && npm run build
```

Publish directory:

``` text
dist
```

The frontend uses a configurable production API URL instead of
hard-coding the local development server.

------------------------------------------------------------------------

# 🧯 Major Engineering Challenge: Cloud Memory Limit

One of the most important problems solved during deployment was the
memory footprint of the embedding stack.

The initial approach used:

``` text
Sentence Transformers
        +
PyTorch
        +
heavy ML/CUDA-related dependencies
```

The production Render instance had a strict memory constraint. The
deployment logs showed that large NVIDIA/CUDA-related packages were
being downloaded and the service eventually exceeded the available
memory.

### Root cause

A full PyTorch-based embedding runtime was unnecessary for this
application's production workload.

### Solution

The embedding layer was redesigned around:

``` text
FastEmbed
```

The production dependency stack became substantially lighter:

``` text
FastAPI
+
FastEmbed
+
Pinecone
+
Groq
```

### Result

The backend successfully deployed and started in production.

The successful deployment logs showed:

``` text
[PINECONE] Connected
[PINECONE] vectors=12
Enterprise AI backend ready.
Your service is live
```

### Why this is important

This demonstrates more than simply integrating an AI API. The project
required:

-   Reading deployment logs
-   Identifying dependency bloat
-   Understanding the runtime memory problem
-   Reconsidering the embedding architecture
-   Replacing an unnecessarily heavy dependency
-   Testing locally
-   Committing the fix
-   Redeploying
-   Verifying the production service

------------------------------------------------------------------------

# 🔐 Security

Sensitive values are supplied through environment variables rather than
source code.

Production secrets include:

``` text
PINECONE_API_KEY
GROQ_API_KEY
AUTH_SECRET_KEY
```

Security practices used in the project include:

-   Environment-based secret management
-   JWT authentication
-   Password hashing
-   `.env` exclusion from source control
-   Separate production configuration
-   Avoiding API keys in frontend source code

> If an API key is ever exposed publicly, revoke and rotate it
> immediately.

------------------------------------------------------------------------

# 🧪 API Documentation & Testing

FastAPI automatically generates interactive OpenAPI documentation.

Production Swagger UI:

https://enterprise-ai-f8pd.onrender.com/docs

Available API areas include:

``` text
Health
Authentication
Documents
PDF Upload
Chat Management
Document Deletion
```

The API documentation was also used during development to verify
endpoint registration and production connectivity.

------------------------------------------------------------------------

# 📊 Production Status

  Component                        Status
  -------------------------------- ----------------
  React frontend                   ✅ Live
  Vite production build            ✅ Working
  FastAPI backend                  ✅ Live
  Authentication                   ✅ Implemented
  PDF upload                       ✅ Implemented
  PDF extraction                   ✅ Implemented
  Embedding generation             ✅ Implemented
  Pinecone connection              ✅ Working
  Semantic vector search           ✅ Implemented
  Groq integration                 ✅ Implemented
  Chat APIs                        ✅ Implemented
  Document APIs                    ✅ Implemented
  Swagger/OpenAPI                  ✅ Available
  Render deployment                ✅ Live
  Production memory optimization   ✅ Completed

------------------------------------------------------------------------

# 🧠 Engineering Decisions

## Why FastAPI?

FastAPI was selected because it provides:

-   High-performance ASGI execution
-   Type-safe request/response handling
-   Automatic OpenAPI documentation
-   Straightforward file-upload support
-   Clean REST API development

------------------------------------------------------------------------

## Why Pinecone?

Pinecone provides managed vector storage and semantic search without
requiring the application server to maintain a large local vector index.

This is especially useful for a cloud-deployed RAG system.

------------------------------------------------------------------------

## Why FastEmbed?

The production environment had limited memory. FastEmbed provided the
embedding capability without requiring the full heavyweight PyTorch
runtime used by the earlier approach.

------------------------------------------------------------------------

## Why RAG instead of sending the whole PDF to the LLM?

Sending the entire document can:

-   Increase token usage
-   Increase latency
-   Increase cost
-   Exceed context limits
-   Add irrelevant information

RAG retrieves only the relevant pieces before generation.

------------------------------------------------------------------------

## Why separate frontend and backend deployments?

The architecture allows the frontend and backend to be independently
built, deployed, scaled, and debugged.

``` text
React Static Site
       │
       │ HTTPS
       ▼
FastAPI Web Service
       │
       ├── Pinecone
       └── Groq
```

------------------------------------------------------------------------

# 🧪 Development & Deployment Workflow

``` text
1. Design RAG architecture
        ↓
2. Build PDF processing
        ↓
3. Implement embeddings
        ↓
4. Integrate Pinecone
        ↓
5. Build authentication
        ↓
6. Build document APIs
        ↓
7. Build chat APIs
        ↓
8. Build React frontend
        ↓
9. Integrate frontend + backend
        ↓
10. Build production frontend
        ↓
11. Deploy backend
        ↓
12. Analyze deployment failures
        ↓
13. Optimize ML dependencies
        ↓
14. Replace heavyweight embedding stack
        ↓
15. Redeploy
        ↓
16. Verify production endpoints
```

------------------------------------------------------------------------

# 📈 Skills Demonstrated

This project demonstrates practical experience across multiple
engineering areas.

### Artificial Intelligence

-   Retrieval-Augmented Generation
-   Embeddings
-   Semantic search
-   LLM integration
-   Context retrieval
-   Prompt/context construction

### Backend

-   Python
-   FastAPI
-   REST API design
-   JWT authentication
-   File uploads
-   PDF processing
-   API documentation

### Frontend

-   React
-   Vite
-   API integration
-   Authentication UI
-   Production builds

### Databases

-   Pinecone
-   Vector databases
-   Similarity search
-   Metadata-based retrieval

### Cloud / DevOps

-   Render
-   Git
-   GitHub
-   Environment variables
-   Production debugging
-   Deployment optimization

------------------------------------------------------------------------

# 💼 Resume-Ready Description

### Enterprise AI --- Intelligent Document Assistant

**Tech:** React, Vite, FastAPI, Python, Groq, Pinecone, FastEmbed, JWT,
Render

> Built and deployed a full-stack Retrieval-Augmented Generation
> platform that enables authenticated users to upload PDFs and interact
> with document content through natural-language queries. Implemented
> PDF extraction, text chunking, 384-dimensional semantic embeddings,
> Pinecone vector search, Groq-based LLM generation, JWT authentication,
> document management, and chat APIs. Diagnosed a production memory
> failure caused by a heavyweight Sentence Transformers/PyTorch
> embedding stack and redesigned the embedding layer with FastEmbed,
> enabling successful deployment on a constrained cloud instance.

------------------------------------------------------------------------

# 🎤 Interview Explanation

### What problem does the project solve?

> Enterprise documents often contain large amounts of information that
> are difficult to search manually. I built an AI document assistant
> where users can upload PDFs and ask questions about their contents
> using natural language.

### Explain your RAG pipeline.

> When a PDF is uploaded, I extract the text, split it into chunks,
> generate embeddings using FastEmbed, and store those vectors in
> Pinecone. When the user asks a question, I generate a query embedding,
> perform semantic similarity search in Pinecone, retrieve the most
> relevant chunks, and pass those chunks with the question to the Groq
> LLM to generate the answer.

### What was your biggest technical challenge?

> The initial deployment failed because the Sentence Transformers and
> PyTorch dependency chain consumed too much memory. I inspected the
> Render logs, identified the heavy ML dependencies, and replaced that
> embedding stack with FastEmbed. After testing locally, I pushed the
> optimized implementation and successfully deployed the backend.

### Why Pinecone?

> I wanted persistent managed vector storage rather than keeping a
> potentially large vector index in application memory. Pinecone
> provides semantic similarity search and metadata support.

### Why not send the complete PDF to the LLM?

> It would increase context size, latency, and cost. RAG retrieves only
> the most relevant chunks, so the model receives focused context.

------------------------------------------------------------------------

# 🔭 Future Improvements

The current deployed application focuses on the core authenticated
PDF-RAG workflow.

Potential next improvements:

-   [ ] Streaming LLM responses
-   [ ] Source citations in answers
-   [ ] Multi-document conversations
-   [ ] Document-level permissions
-   [ ] Role-based access control
-   [ ] OCR for scanned PDFs
-   [ ] Voice input
-   [ ] Voice output
-   [ ] Image understanding
-   [ ] Conversation export
-   [ ] RAG evaluation metrics
-   [ ] Automated unit/integration tests
-   [ ] CI/CD pipeline
-   [ ] Production relational database
-   [ ] Rate limiting
-   [ ] Monitoring and observability
-   [ ] Advanced document filtering

------------------------------------------------------------------------

# 🌐 Links

### Live Application

https://enterprise-ai-frontend-p445.onrender.com

### Backend API

https://enterprise-ai-f8pd.onrender.com

### Swagger Documentation

https://enterprise-ai-f8pd.onrender.com/docs

### GitHub Repository

https://github.com/Deekshitha-Gajjala/enterprise-ai

------------------------------------------------------------------------

# 👩‍💻 Author

## Deekshitha Gajjala

Computer Science / Data Science\
GITAM University, Bengaluru

GitHub:\
https://github.com/Deekshitha-Gajjala

------------------------------------------------------------------------

# ⭐ If You Like the Project

If this project was useful or interesting, consider starring the
repository.

------------------------------------------------------------------------

## 📜 License

This project is intended for educational, portfolio, and development
purposes.
