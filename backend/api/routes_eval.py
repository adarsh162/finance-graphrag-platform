# backend/api/routes_eval.py
import os
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

# We set prefix to "/eval" because main.py already adds "/api"
router = APIRouter(prefix="/eval", tags=["evaluation"])

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "postgres")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL)

class TraceItem(BaseModel):
    id: str
    threadId: str
    userQuery: str
    llmResponse: str
    hallucinationScore: Optional[int]
    relevanceScore: Optional[int]
    evalReasoning: Optional[str]
    guardrailFlagged: bool
    totalTokens: Optional[int]
    createdAt: str

@router.get("/traces", response_model=List[TraceItem])
async def get_recent_traces():
    query = text("""
        SELECT 
            id, thread_id, user_query, llm_response, 
            hallucination_score, relevance_score, eval_reasoning, 
            total_tokens, guardrail_flagged, created_at
        FROM chat_traces
        ORDER BY created_at DESC
        LIMIT 50
    """)

    traces = []
    try:
        async with engine.connect() as conn:
            result = await conn.execute(query)
            for row in result:
                traces.append(
                    TraceItem(
                        id=row.id,
                        threadId=row.thread_id or "",
                        userQuery=row.user_query,
                        llmResponse=row.llm_response,
                        hallucinationScore=row.hallucination_score,
                        relevanceScore=row.relevance_score,
                        evalReasoning=row.eval_reasoning,
                        guardrailFlagged=getattr(row, 'guardrail_flagged', False) or False,
                        totalTokens=row.total_tokens or 0,
                        createdAt=row.created_at.isoformat() if row.created_at else ""
                    )
                )
        return traces
    except Exception as e:
        print(f"🔥 ERROR in /traces: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch traces: {str(e)}")

@router.get("/metrics")
async def get_dashboard_metrics():
    query = text("""
        SELECT 
            COUNT(*) AS total_requests,
            ROUND(AVG(relevance_score), 2) AS avg_relevance,
            ROUND(SUM(CASE WHEN hallucination_score = 1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS faithfulness_rate,
            SUM(CASE WHEN hallucination_score = 0 OR relevance_score <= 2 THEN 1 ELSE 0 END) AS flagged_count
        FROM chat_traces
    """)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(query)
            row = result.fetchone()

            return {
                "totalRequests": row.total_requests or 0,
                "avgRelevance": float(row.avg_relevance or 0.0),
                "faithfulnessRate": f"{row.faithfulness_rate or 0}%",
                "flaggedCount": row.flagged_count or 0
            }
    except Exception as e:
        print(f"🔥 ERROR in /traces: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")
