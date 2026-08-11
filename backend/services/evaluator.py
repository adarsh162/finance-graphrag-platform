# backend/services/evaluator.py
import os
import sys
import json
import uuid
from typing import Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Import your existing LLM factory from agent/nodes.py
from agent.nodes import get_llm

load_dotenv()

# Database engine setup
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "postgres")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL)

# Initialize fast LLM via existing provider (Groq / Google / OpenAI)
eval_llm = get_llm(model_type="fast", temperature=0)

# Define output schema for the evaluator
class EvaluationResult(BaseModel):
    hallucination_score: int = Field(description="1 if assistant response is strictly grounded in context, 0 if it invents facts")
    relevance_score: int = Field(description="Integer from 1 (irrelevant) to 5 (perfectly answers user query)")
    reasoning: str = Field(description="1-2 sentence explanation of the evaluation scores")

eval_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "You are an expert AI evaluator for a financial RAG system.\n"
        "Evaluate the Assistant Response against the Context and User Query.\n\n"
        "{format_instructions}"
    )),
    ("human", (
        "User Query: {query}\n\n"
        "Context:\n{context}\n\n"
        "Assistant Response: {response}"
    ))
])

parser = JsonOutputParser(pydantic_object=EvaluationResult)
eval_chain = eval_prompt | eval_llm | parser


async def save_and_evaluate_trace(thread_id: str, query: str, context: list, response: str, total_tokens: int = 0, guardrail_flagged: bool = False):
    """
    Saves the initial chat trace to PostgreSQL, queries the cloud LLM judge,
    and updates the row with the evaluation scores.
    """
    print("Identified tokens from evaluator.py before inserting in db")
    print(total_tokens)
    trace_id = str(uuid.uuid4())
    MAX_CHARS_PER_CHUNK = 500
    truncated_context = []
    for chunk in context:
        if len(chunk) > MAX_CHARS_PER_CHUNK:
            truncated_context.append(chunk[:MAX_CHARS_PER_CHUNK] + "... [truncated]")
        else:
            truncated_context.append(chunk)
    context_json = json.dumps(truncated_context) if truncated_context else json.dumps([])

    # 1. Insert Initial Trace via Raw SQL
    insert_query = text("""
        INSERT INTO chat_traces (id, thread_id, user_query, retrieved_context, llm_response, total_tokens, guardrail_flagged)
        VALUES (:id, :thread_id, :query, CAST(:context AS JSONB), :response, :total_tokens, :guardrail_flagged)
    """)

    try:
        async with engine.begin() as conn:
            await conn.execute(insert_query, {
                "id": trace_id,
                "thread_id": thread_id,
                "query": query,
                "context": context_json,
                "response": response,
                "total_tokens": total_tokens,
                "guardrail_flagged": guardrail_flagged
            })
    except Exception as e:
        print(f"⚠️ Failed to insert initial trace: {e}")
        return

    # 2. Query Cloud Judge (Groq / Gemini via get_llm)
    context_text = "\n\n".join(context) if context else "No context provided."

    try:
        eval_data = await eval_chain.ainvoke({
            "query": query,
            "context": context_text,
            "response": response,
            "format_instructions": parser.get_format_instructions()
        })

        hallucination = eval_data.get("hallucination_score", 0)
        relevance = eval_data.get("relevance_score", 1)
        reasoning = eval_data.get("reasoning", "No explanation provided.")

        # 3. Update Trace with Scores via Raw SQL
        update_query = text("""
            UPDATE chat_traces
            SET hallucination_score = :hallucination,
                relevance_score = :relevance,
                eval_reasoning = :reasoning
            WHERE id = :id
        """)

        async with engine.begin() as conn:
            await conn.execute(update_query, {
                "hallucination": hallucination,
                "relevance": relevance,
                "reasoning": reasoning,
                "id": trace_id
            })

        print(f"✅ Trace {trace_id} evaluated via cloud provider ({os.getenv('LLM_PROVIDER', 'google')}) successfully!")

    except Exception as e:
        print(f"⚠️ Trace evaluation failed: {e}")
