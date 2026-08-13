# backend/routes/documents.py
import os
import traceback
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from services.neo4j_client import get_graph_client

load_dotenv()

router = APIRouter(prefix="/documents", tags=["documents"])

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "postgres")

# Note: asyncpg driver
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL)

class DocumentItem(BaseModel):
    id: str
    name: str
    uploadDate: str
    status: str

class DocumentListResponse(BaseModel):
    documents: List[DocumentItem]

@router.get("", response_model=DocumentListResponse)
async def list_documents():
    # Group by filename so chunks of the same file collapse into one row
    query = text("""
            SELECT 
                COALESCE(
                    MAX(langchain_metadata->>'document_id'), 
                    regexp_replace(MIN(langchain_metadata->>'source'), '^.*[\\/]', '')
                ) AS doc_id,
                MAX(langchain_metadata->>'upload_date') AS upload_date
            FROM finance_documents
            WHERE langchain_metadata->>'source' IS NOT NULL
            GROUP BY 
                COALESCE(
                    langchain_metadata->>'document_id', 
                    regexp_replace(langchain_metadata->>'source', '^.*[\\/]', '')
                )
        """)
    documents = []
    try:
        async with engine.connect() as conn:
            result = await conn.execute(query)
            for row in result:
                display_name = row.doc_id
                # name = f"{display_name} ({filename})" if display_name else filename
                upload_date = row.upload_date or datetime.utcnow().isoformat()
                
                documents.append(
                    DocumentItem(
                        id=row.doc_id,
                        name=display_name,
                        uploadDate=upload_date,
                        status="completed"
                    )
                )
        return {"documents": documents}
    except Exception as e:
        print(f"Failed to fetch documents: {e}")
        return {"documents": []}

@router.delete("/{document_id:path}")
async def delete_document(document_id: str):
    # Match any chunk whose source ends with the target filename to clean up duplicates
    clean_filename = os.path.basename(document_id)
    filename_pattern = f"%{clean_filename}"
    pg_delete_query = text("""
        DELETE FROM finance_documents 
        WHERE langchain_metadata->>'document_id' = :clean_name
               OR langchain_metadata->>'source' LIKE :pattern
               OR langchain_metadata->>'document_id' = :raw_id
    """)

    try:
        async with engine.begin() as conn:
            result = await conn.execute(pg_delete_query, {
                    "clean_name": clean_filename, 
                    "pattern": filename_pattern,
                    "raw_id": document_id
                })
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Document not found in vector store")

        graph_client = get_graph_client()
        clean_filename = os.path.basename(document_id)
        # Cypher 1: Delete the Document node and any direct chunk/source references
        cascading_delete_query = """
        MATCH (d:Document)
        WHERE d.document_id = $doc_id 
           OR d.document_id = $clean_name
           OR d.source = $doc_id 
           OR d.source = $clean_name
           OR d.source ENDS WITH $clean_name
        OPTIONAL MATCH (d)-[:MENTIONS]->(e)
        WITH d, collect(e) AS entities
        DETACH DELETE d
        WITH entities
        UNWIND entities AS e
        WITH e  // <--- ADD THIS LINE HERE
        WHERE e IS NOT NULL AND NOT EXISTS {
            MATCH (:Document)-[:MENTIONS]->(e)
        }
        DETACH DELETE e
        """
        graph_client.query(cascading_delete_query, params={"doc_id": document_id, "clean_name": clean_filename})
        return {"message": f"Successfully deleted {result.rowcount} vector chunks for filename '{clean_filename}'"}
    except Exception as e:
        # 1. Print a highly visible header
        print("\n" + "="*50)
        print("🔥 DELETION CRASHED. FULL TRACEBACK BELOW:")
        print("="*50)
        # 2. Print the exact line number and underlying error to the terminal
        traceback.print_exc()
        print("="*50 + "\n")

        # 3. Raise the HTTP exception for the frontend
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete document: {str(e)}"
        )
