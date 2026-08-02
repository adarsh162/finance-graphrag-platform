# backend/api/routes_chat.py
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.graph.state import CompiledStateGraph

# Import your compiled graph from the previous step
from agent.graph import graph_app

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    thread_id: str

async def stream_langgraph_events(graph: CompiledStateGraph, question: str, thread_id: str):
    """
    An asynchronous generator that yields Server-Sent Events (SSE) 
    from the LangGraph execution.
    """
    # The configuration dict tells LangGraph which memory thread to use
    config = {"configurable": {"thread_id": thread_id}}
    initial_input = {"original_question": question}

    # astream_events is the recommended LangChain streaming API
    # We use version="v2" to get detailed node and token data
    async for event in graph.astream_events(initial_input, config, version="v2"):

        kind = event["event"]

        # 1. State Updates (e.g., "rewrite_query" finished)
        if kind == "on_chain_end" and not event.get("name") == "LangGraph":
            # Extract the output from the specific node
            output = event["data"].get("output", {})
            if output:
                yield f"data: {json.dumps({'type': 'node_update', 'node': event['name']})}\n\n"

        # 2. Token Streaming (As the LLM generates the final answer)
        elif kind == "on_chat_model_stream":
            token = event["data"]["chunk"].content
            if token:
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    # Signal the React frontend that the stream is complete
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    The FastAPI route that Next.js will connect to.
    It returns a StreamingResponse with media_type="text/event-stream" for SSE.
    """
    return StreamingResponse(
        stream_langgraph_events(graph_app, request.question, request.thread_id),
        media_type="text/event-stream"
    )
