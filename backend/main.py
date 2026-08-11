# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes_chat import router as chat_router
from api.routes_ingestion import router as ingestion_router
from api.routes_eval import router as eval_router
from api.documents import router as documents_router
from api.documents import engine as sqlalchemy_engine
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from services.pgvector_client import engine, TABLE_NAME, VECTOR_SIZE

# Load the .env file BEFORE importing any other modules
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize the table structure
    try:
        await engine.ainit_vectorstore_table(
            table_name=TABLE_NAME,
            vector_size=VECTOR_SIZE,
        )
        print(f"INFO: Successfully created vector table '{TABLE_NAME}'")
    except ProgrammingError:
        print(f"INFO: Vector table '{TABLE_NAME}' already exists. Skipping creation.")

    create_traces_table_query = text("""
        CREATE TABLE IF NOT EXISTS chat_traces (
            id VARCHAR(36) PRIMARY KEY,
            thread_id VARCHAR(255),
            user_query TEXT NOT NULL,
            retrieved_context JSONB,
            llm_response TEXT NOT NULL,
            hallucination_score INT,
            relevance_score INT,
            total_tokens INT DEFAULT 0,
            guardrail_flagged BOOLEAN DEFAULT FALSE,
            eval_reasoning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    try:
        async with sqlalchemy_engine.begin() as conn:
            await conn.execute(create_traces_table_query)
        print("INFO: Successfully ensured 'chat_traces' table exists.")
    except Exception as e:
        print(f"WARNING: Could not initialize 'chat_traces' table: {e}")

    yield

# Update your FastAPI instantiation to use it:
app = FastAPI(lifespan=lifespan)

# Enable CORS for the Next.js React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the routes
app.include_router(chat_router, prefix="/api")
app.include_router(ingestion_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(eval_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
