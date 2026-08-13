# Financial GraphRAG Platform

An advanced Retrieval-Augmented Generation (RAG) platform designed specifically for extracting, querying, and synthesizing complex financial documents (e.g., SEC 10-K filings). This architecture leverages the combined power of knowledge graphs and vector databases to ensure hyper-accurate, multi-hop reasoning without LLM hallucinations.

---

## 🏗️ Architecture Overview

This platform utilizes a hybrid GraphRAG architecture orchestrated by LangGraph, balancing the dense, semantic understanding of vector embeddings with the strict, relationship-based topology of a graph database.

- **Graph Store (Neo4j):** Extracts and maps definitive relationships between entities (e.g., `Company -> HAS_SUBSIDIARY -> Subsidiary`, `Company -> FACED_WITH -> RiskFactor`).
- **Vector Store (PostgreSQL / `pgvector`):** Handles semantic similarity search over raw document chunks to capture nuanced financial narratives, metric tables, and temporal data.
- **Orchestration (LangGraph):** Manages stateful multi-agent workflows, controlling the routing, entity extraction, hybrid retrieval, and final response generation.

---

## ✨ Core Features

*   **Hybrid Retrieval Pipeline:** Merges graph traversal facts from Neo4j with dense semantic vector search results from PostgreSQL (`pgvector`) to capture both structural relationships and unstructured context.
*   **Cross-Encoder Reranking:** Leverages a `CrossEncoder` model to re-score and re-rank combined candidate context chunks before passing them to the generator LLM, ensuring top semantic relevance and cutting down noise.
*   **Strict Anti-Hallucination Guardrails:** Implements rigid system prompts that force the generator LLM to reject queries when required data (like specific revenue streams or missing subsidiaries) is not explicitly present in the combined context.
*   **Optimized Graph Extraction:** Uses unconstrained `LLMGraphTransformer` extraction for reliable ingestion, bypassing strict API tool-schema failures (e.g., `400 tool_use_failed`) common when parsing complex financial tables.
*   **Clean SSE Streaming (Server-Sent Events):** Filters LangGraph event streams strictly to the final generator node (`langgraph_node == "generate_response"`), completely eliminating entity tag bleed into the frontend UI.
*   **Trace Observability & Evaluation:** Calculates and logs real-time evaluation metrics for every query, distinguishing perfectly grounded responses (Faithfulness/Hallucination Score = 1) from fabricated inferences (Score = 0).
*   **Document Lifecycle Management:** Complete UI and backend support for viewing active ingested filings, uploading new PDFs for automatic graph & vector indexing, and removing documents with cascading deletions across Neo4j and `pgvector`.
*   **Security & Prompt Guardrails:** These intercept malicious inputs, such as prompt injections and jailbreak attempts, preventing unauthorized actions or data manipulation.

---

## 🛠️ Tech Stack

### Backend
*   **Framework:** FastAPI (Python 3.12)
*   **Orchestration:** LangGraph / LangChain
*   **Graph Database:** Neo4j (Cypher)
*   **Vector Database:** PostgreSQL with `pgvector` extension
*   **Reranker:** SentenceTransformers / HuggingFace (`CrossEncoder`)
*   **LLMs Supported:** Groq (Llama 3), Google Gemini Flash, OpenAI (GPT-4o)


### Frontend

- **Framework:** Next.js (React, TypeScript)
- **Styling:** Tailwind CSS
- **Data Fetching:** Native browser `EventSource` for real-time SSE streaming

---

## 🚀 Setup & Installation

### 1. Environment Variables

Create a `.env` file in your `backend/` directory with the following keys:

```env
# LLM Provider (groq, google, openai)
LLM_PROVIDER=groq
GROQ_API_KEY=your_api_key_here

# Neo4j Graph Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# PostgreSQL (pgvector)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=rag_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 2. Backend Initialization

Ensure PostgreSQL and Neo4j are running, then install dependencies and start the API:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the FastAPI Server
uvicorn main:app --reload
```

### 3. Frontend Initialization

```bash
cd frontend
npm install
npm run dev
```

---

## 🧠 System Behaviors & Best Practices

### The Fallback Mechanism

This platform is explicitly designed for financial accuracy. If you ask a question like, "What are the revenue streams for AeroTech's hardware?" and the source 10-K does not explicitly map a product to a revenue tier, the system will intentionally return:

> "The provided context does not contain sufficient information to answer this."

This is a feature, not a bug. It prevents the AI from fabricating mappings, ensuring a perfect Groundedness Score of 1 in the observability ledger.

### Managing Graph Extraction Schema

By default, the ingestion worker runs `LLMGraphTransformer` without strict `allowed_nodes` or `allowed_relationships` constraints. This ensures stable JSON tool calling from the LLMs. If you require a strict ontology, we recommend switching the extraction LLM provider to OpenAI (GPT-4o) to handle complex, multi-array schema validation flawlessly.

## 🔌 Key API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/documents` | Lists all ingested documents and their status. |
| `POST` | `/api/documents/upload` | Uploads a PDF file and triggers background vector & graph ingestion. |
| `DELETE` | `/api/documents/:id` | Deletes a document and cascades deletion through Neo4j and `pgvector`. |
| `POST` | `/api/chat/stream` | Initiates SSE streaming for interactive RAG queries. |