# backend/routes/documents.py
import os
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

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
            MIN(langchain_metadata->>'source') AS source, 
            MAX(langchain_metadata->>'company') AS company, 
            MAX(langchain_metadata->>'year') AS year,
            MAX(langchain_metadata->>'upload_date') AS upload_date
        FROM finance_documents
        WHERE langchain_metadata->>'source' IS NOT NULL
        GROUP BY regexp_replace(langchain_metadata->>'source', '^.*[\\/]', '')
    """)
    
    documents = []
    try:
        async with engine.connect() as conn:
            result = await conn.execute(query)
            
            for row in result:
                source = row.source
                company = row.company or ""
                year = row.year or ""
                
                filename = os.path.basename(source)
                display_name = f"{company} {year}".strip()
                name = f"{display_name} ({filename})" if display_name else filename
                upload_date = row.upload_date or datetime.utcnow().isoformat()
                
                documents.append(
                    DocumentItem(
                        id=source,
                        name=name,
                        uploadDate=upload_date,
                        status="completed"
                    )
                )
        return {"documents": documents}
    
    except ProgrammingError as e:
        if "does not exist" in str(e):
            return {"documents": []}
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.delete("/{document_id:path}")
async def delete_document(document_id: str):
    # Match any chunk whose source ends with the target filename to clean up duplicates
    filename = os.path.basename(document_id)
    query = text("""
        DELETE FROM finance_documents 
        WHERE langchain_metadata->>'source' LIKE :filename_pattern
    """)
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(query, {"filename_pattern": f"%{filename}"})
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Document not found in vector store")
                
        return {"message": f"Successfully deleted {result.rowcount} vector chunks for filename '{filename}'"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")