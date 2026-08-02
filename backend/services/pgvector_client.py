import os
from dotenv import load_dotenv
from langchain_postgres import PGEngine, PGVectorStore
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
# Initialize your embeddings
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-large-en-v1.5")

# 1. Create the async engine manager
DB_USER=os.getenv("POSTGRES_USER")
DB_PASSWORD=os.getenv("POSTGRES_PASSWORD")
DB_HOST=os.getenv("POSTGRES_HOST")
DB_PORT=os.getenv("POSTGRES_PORT")
DB_NAME=os.getenv("POSTGRES_DB")
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = PGEngine.from_connection_string(DATABASE_URL)

# 2. Define your table name
TABLE_NAME = "finance_documents"
VECTOR_SIZE = 1024

# 3. Create the modern PGVectorStore client
async def get_pgvector_client() -> PGVectorStore:
    """
    Asynchronously creates and returns the PGVectorStore client.
    """
    return await PGVectorStore.create(
        engine=engine,
        embedding_service=embeddings,
        table_name=TABLE_NAME,
    )
