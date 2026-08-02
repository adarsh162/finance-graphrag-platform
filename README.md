# Enterprise Finance GraphRAG

An advanced, event-driven Retrieval-Augmented Generation (RAG) system built to analyze complex financial documents (like SEC 10-K filings) in real-time. This project moves beyond standard semantic search by combining **Dense Vector Retrieval (pgvector)** with **Knowledge Graph Traversal (Neo4j)**, orchestrated by **LangGraph**.

## 🚀 Key Features

*   **Continuous Ingestion:** Asynchronously chunk and embed massive PDF documents in the background without blocking the user interface.
*   **Hybrid Search & Reranking:** Combines sparse (BM25) and dense (BAAI/BGE-Large) retrieval, dynamically reranked using a Cross-Encoder for maximum accuracy.
*   **GraphRAG Reasoning:** Uses an LLM to extract financial entities (Companies, Subsidiaries, Risk Factors, Revenue Streams) into Neo4j for multi-hop reasoning.
*   **Real-Time Streaming:** Streams LangGraph execution states and LLM tokens to a Next.js frontend using Server-Sent Events (SSE).

## 🏗️ Architecture Stack

*   **Backend:** FastAPI, Python, LangGraph, LangChain
*   **Frontend:** Next.js (App Router), React, Tailwind CSS, `@microsoft/fetch-event-source`
*   **Vector Database:** PostgreSQL with `pgvector`
*   **Graph Database:** Neo4j
*   **Models:** OpenAI (`gpt-4o`, `gpt-4o-mini`) & HuggingFace (`bge-large-en-v1.5`, `bge-reranker-v2-m3`)
*   **Infrastructure:** Docker Compose

---

## 🛠️ Prerequisites

Ensure you have the following installed on your machine:
*   [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Running)
*   [Python 3.10+](https://www.python.org/downloads/)
*   [Node.js 18+](https://nodejs.org/)

## ⚙️ Environment Setup

### 1. Backend Environment Variables
Create a `.env` file inside the `backend/` directory:

```env
OPENAI_API_KEY=your_openai_api_key_here

# PostgreSQL Configuration (Matches docker-compose)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=finance_graphrag

# Neo4j Configuration (Matches docker-compose)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

🚀 Installation & Running the Application
Step 1: Start the Databases
Spin up the PostgreSQL (pgvector) and Neo4j containers.

Bash
docker-compose up -d
Step 2: Start the FastAPI Backend
Open a new terminal, navigate to the backend folder, install dependencies, and start the server.

Bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --port 8000
Step 3: Start the Next.js Frontend
Open a third terminal, navigate to the frontend folder, install dependencies, and start the development server.

Bash
cd finance-graphrag-ui
npm install
npm run dev
The application will now be running at http://localhost:3000.

📖 Usage Instructions
Ingest a Document: Navigate to the web interface and fill out the upload form. Upload a sample SEC 10-K PDF (e.g., Apple 2023 10-K).

Monitor Processing: The UI will immediately accept the file, and background workers will begin chunking, generating dense embeddings, and extracting Neo4j graph entities.

Query the Agent: While or after the document processes, use the chat interface to ask complex financial questions (e.g., "Which subsidiary handles international revenue, and what are their stated risk factors?").

Watch it Stream: The UI will display the system's reasoning steps (routing, retrieving, generating) before streaming the final answer token-by-token.