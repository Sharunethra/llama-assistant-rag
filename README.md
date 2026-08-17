# Llama Assistant — Local RAG-Based AI Document Assistant

A full-stack, interview-ready AI Document Assistant built with **Django REST Framework**, **PostgreSQL**, **FastEmbed**, **Local Ollama (Llama 3.2 3B)**, and **React (Vite)**.

---

## Key Features

### Task 1: Conversational AI
- **Token-Based Authentication**: Secure Registration, Login, and Logout APIs.
- **Multi-Turn Chat History**: Full conversation history persisted per user in PostgreSQL.
- **Local Self-Hosted LLM**: Powered by Ollama (`llama3.2:3b`) running 100% offline on local hardware with zero API token costs.
- **User Isolation**: Strict user-level access controls for conversations and messages.

### Task 2: Grounded Document RAG (Retrieval-Augmented Generation)
- **Document Ingestion**: Upload PDF and TXT documents associated with specific conversations.
- **Text Extraction**: Plain-text parsing via `pypdf` for PDFs and UTF-8 decoder for text files.
- **Word-Based Chunking**: Sliding-window chunking (400 words per chunk with 50-word overlap) to preserve context boundaries.
- **FastEmbed Embeddings**: Dense 384-dimensional vector embeddings generated locally via FastEmbed (`BAAI/bge-small-en-v1.5`).
- **PostgreSQL Vector Storage**: Embeddings and chunks stored in native `JSONField` database models.
- **Cosine Similarity Retrieval**: Exact mathematical vector retrieval with query cleaning:
  - *Broad/Summary Queries*: 6–8 representative chunks sampled across document segments.
  - *Specific Queries*: Top 4 highest cosine-similarity matching chunks.
  - *Document Order*: Retrieved chunks sorted by `chunk_index` ascending before prompt construction.
- **Strict Grounding**: Llama prompt engineered with strict instructions to answer *only* using retrieved document context and fall back to *"The requested information is not available in the uploaded document."* when context is missing.

---

## Project Structure

```text
chat_app/
│
├── backend/
│   ├── manage.py             # Django management CLI
│   ├── requirements.txt      # Backend Python dependencies
│   ├── config/
│   │   ├── settings.py       # DRF, PostgreSQL, CORS & Auth configuration
│   │   ├── urls.py           # Root URL routing
│   │   └── wsgi.py
│   ├── chat/
│   │   ├── models.py         # Conversation & Message Django ORM models
│   │   ├── serializers.py    # DRF Serializers for User, Conversation, Message
│   │   ├── views.py          # Auth, Conversation CRUD & Message API views
│   │   ├── urls.py           # Chat API routes (/api/auth/*, /api/chats/*)
│   │   ├── services.py       # Ollama LLM integration service (urllib standard library)
│   │   ├── admin.py          # Django Admin setup
│   │   ├── tests.py          # Unit tests covering Auth, Ollama Mocks & Isolation
│   │   └── migrations/
│   └── documents/
│       ├── models.py         # Document & DocumentChunk Django ORM models
│       ├── serializers.py    # DRF Serializers for Document upload & list
│       ├── views.py          # Document upload & listing API views
│       ├── urls.py           # Document API routes (/api/documents/*)
│       ├── services.py       # Text extraction, FastEmbed embeddings & Cosine Retrieval
│       ├── admin.py          # Django Admin setup
│       ├── tests.py          # Unit tests covering extraction, chunking & retrieval
│       └── migrations/
│
├── frontend/
│   ├── package.json          # React dependencies & scripts
│   ├── vite.config.js        # Vite development & build configuration
│   ├── index.html
│   └── src/
│       ├── main.jsx          # React entry point
│       ├── App.jsx           # Root layout & global chat state manager
│       ├── index.css         # Dark theme styling & UI tokens
│       ├── services/
│       │   └── api.js        # Axios instance with Auth token interceptors
│       └── components/
│           ├── Sidebar.jsx   # Conversation list, document list & user profile
│           ├── ChatWindow.jsx# Message list, document badge & scroll container
│           ├── Message.jsx   # Individual message bubble renderer
│           ├── MessageInput.jsx # Prompt input bar with document attachment
│           └── AuthModal.jsx # Login & Registration modal
│
├── .env.example              # Environment variables template
├── .gitignore
└── README.md                 # Complete system documentation
```

---

## Hardware Requirements & Recommended Model

- **Recommended Hardware**: 8 GB+ RAM, Quad-core CPU or Apple Silicon / NVIDIA GPU.
- **Recommended Model**: `llama3.2:3b` (3.2 Billion parameters, Meta AI).
  - *VRAM/RAM footprint*: ~2.0 GB.
  - *Embedding model*: `BAAI/bge-small-en-v1.5` (FastEmbed, 384 dimensions).

---

## Step-by-Step Setup Guide

### 1. Install & Run Ollama
Download and install Ollama from [ollama.com](https://ollama.com).

Pull the Llama 3.2 3B model:
```bash
ollama pull llama3.2:3b
```
Ensure Ollama server is running (defaults to `http://localhost:11434`).

### 2. PostgreSQL Setup
Create the target database in PostgreSQL:
```sql
psql -U postgres
CREATE DATABASE chatapp_db;
```

### 3. Environment Configuration
Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```
Ensure `.env` contains:
```ini
SECRET_KEY=your_django_secret_key_here
DEBUG=True

DB_NAME=chatapp_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password_here
DB_HOST=localhost
DB_PORT=5432

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### 4. Backend Setup & Run
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Run unit tests
python manage.py test documents chat

# Start Django backend server (http://localhost:8000)
python manage.py runserver
```

### 5. Frontend Setup & Run
```bash
cd frontend

# Install node packages
npm install

# Start Vite dev server (http://localhost:5173)
npm run dev

# Verify production build
npm run build
```

---

## Technical Architecture

### Task 1: Normal Conversational Flow
```text
React Frontend ──► Django REST API ──► PostgreSQL (User/Conversation/Message)
                                 │
                                 └──► Python urllib ──► Ollama (http://localhost:11434) ──► Llama 3.2 3B
```

### Task 2: Grounded Document RAG Flow
```text
PDF / TXT Document Upload 
  ──► pypdf / UTF-8 Text Extraction
  ──► 400-Word Chunking (50-word overlap)
  ──► FastEmbed Vector Embedding (384 dimensions)
  ──► PostgreSQL DocumentChunk Storage
  
User Question
  ──► Filename Query Cleaning
  ──► FastEmbed Query Vector
  ──► Cosine Similarity Scoring
  ──► Representative Chunk Selection (6 for broad queries, 4 for specific)
  ──► Grounded Prompt Construction
  ──► Ollama Llama 3.2 3B
  ──► Grounded AI Response
```

---

## Technical Interview Questions & Answers

#### 1. What is the core architecture of this project?
> **Answer**: It is a decoupled full-stack Web application using React (Vite) on the frontend, Django REST Framework and PostgreSQL on the backend, and a self-hosted local RAG pipeline using FastEmbed (`bge-small-en-v1.5`) and local Ollama (`llama3.2:3b`).

#### 2. How does the RAG retrieval pipeline work?
> **Answer**: When a document is uploaded, text is extracted (`pypdf` or UTF-8), split into 400-word chunks (50-word overlap), converted into 384-dimensional dense vector embeddings using FastEmbed, and saved in PostgreSQL. On user queries, the query vector is compared against document chunks via Python Cosine Similarity. Top matching chunks are injected into a grounded prompt passed to Llama 3.2 3B.

#### 3. How does the system handle broad summary questions versus specific factual questions?
> **Answer**: Broad questions (e.g. *"What are the key points in this document?"*) use regex pattern matching to trigger segmented retrieval, sampling 6–8 representative chunks distributed evenly across the entire document length. Specific questions retrieve the top 4 cosine-similarity chunks. All chunks are ordered by `chunk_index` ascending before LLM generation to maintain original document narrative flow.

#### 4. How do you prevent LLM hallucinations?
> **Answer**: System prompts enforce strict grounding instructions: *"You are answering questions about an uploaded document. Answer ONLY based on the provided context. If the answer cannot be found in the context, say 'The requested information is not available in the uploaded document.'"*

#### 5. Why use local Ollama instead of cloud LLM APIs (e.g., OpenAI/Anthropic)?
> **Answer**: Local inference provides 100% data privacy (sensitive uploaded PDFs never leave the host machine), zero token cost, offline availability, and eliminates external network latency or API rate limits.

#### 6. What is the difference between FastEmbed and the LLM model?
> **Answer**: FastEmbed runs a lightweight embedding model (`bge-small-en-v1.5`, 384 dimensions) to convert text into mathematical vector representations for semantic search. Ollama runs the generative LLM (`llama3.2:3b`) to process the context and generate natural language answers.

#### 7. How is conversation history handled?
> **Answer**: Prior messages in a thread are fetched from PostgreSQL (`Message` ORM model), formatted into `{"role": "user"|"assistant", "content": ...}` arrays, and supplied alongside retrieved document context in the Ollama API payload.

#### 8. How is multi-user security enforced?
> **Answer**: Django REST Framework token authentication verifies user identity on every request. Conversations and uploaded Document models use ForeignKeys to `django.contrib.auth.models.User`, and viewsets strictly filter queries by `request.user`.

#### 9. What happens if Ollama is down or disconnected?
> **Answer**: In `chat/services.py`, HTTP calls to Ollama catch `urllib.error.URLError` and return a user-friendly error message (`"AI service is unavailable. Please make sure Ollama is installed and running..."`) without crashing the Django backend server.

#### 10. How would you scale this RAG pipeline for production?
> **Answer**: Use `pgvector` extension in PostgreSQL or a dedicated vector database for indexing million+ vector chunks, offload PDF extraction and embedding generation to Celery background tasks, serve Ollama/vLLM on GPU nodes behind a load balancer, and stream LLM outputs to the frontend via Server-Sent Events (SSE).
