# backend/api/routes_chat.py
import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.graph.state import CompiledStateGraph
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Import your compiled graph and evaluator
from agent.graph import graph_app
from services.evaluator import save_and_evaluate_trace

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    thread_id: str

async def stream_langgraph_events(graph: CompiledStateGraph, question: str, thread_id: str):
    """
    An asynchronous generator that yields Server-Sent Events (SSE) 
    from the LangGraph execution and triggers evaluation on completion.
    """
    config = {"configurable": {"thread_id": thread_id}}
    initial_input = {"original_question": question}
    is_unsafe = await run_all_guardrails(question)
    if is_unsafe:
        rejection_msg = "I cannot fulfill this request as it violates our safety policies."
        
        # Stream the rejection message directly to the frontend
        yield f"data: {json.dumps({'type': 'token', 'content': rejection_msg})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        # Save the flagged trace, skipping the LLM evaluation
        asyncio.create_task(
            save_and_evaluate_trace(
                thread_id=thread_id,
                query=question,
                context=[],
                response=rejection_msg,
                total_tokens=0,
                guardrail_flagged=True
            )
        )
        return
    # Tracking variables for LLM observability
    full_response = ""
    retrieved_context = []
    total_tokens = 0
    async for event in graph.astream_events(initial_input, config, version="v2"):

        kind = event["event"]
        name = event.get("name", "")

        # 1. State Updates (e.g., node finishes)
        if kind == "on_chain_end" and name != "LangGraph":
            output = event["data"].get("output", {})
            if output:
                # Capture retrieved documents from the state output. 
                # (Assumes your state has a 'documents' key holding the chunks)
                if isinstance(output, dict) and "documents" in output:
                    docs = output["documents"]
                    if isinstance(docs, list):
                        # Safely extract text whether it is a LangChain Document or plain string
                        retrieved_context.extend([
                            getattr(doc, "page_content", str(doc)) for doc in docs
                        ])

                yield f"data: {json.dumps({'type': 'node_update', 'node': name})}\n\n"

        # 2. Token Streaming
        elif kind == "on_chat_model_stream":
            token = event["data"]["chunk"].content
            if token:
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        elif kind == "on_chat_model_end":
            output_msg = event["data"].get("output")
            print("\n" + "="*50)
            print("🕵️ RAW LLM OUTPUT METADATA:")
   
            if output_msg:
                if hasattr(output_msg, "usage_metadata"):
                    print(f"usage_metadata: {output_msg.usage_metadata}")
                    print(output_msg.usage_metadata)
                if hasattr(output_msg, "response_metadata"):
                    print(f"response_metadata: {output_msg.response_metadata}")
            else:
                print("No output message found in event.")
            print("="*50 + "\n")

            if output_msg:
                # Attempt 1: Standard LangChain v0.2+ usage_metadata
                if hasattr(output_msg, "usage_metadata") and output_msg.usage_metadata:
                    print("identified tokens in usage_metadata")
                    total_tokens += output_msg.usage_metadata.get("total_tokens", 0)
                
                # Attempt 2: Dig into response_metadata (Common for Groq & Gemini streaming)
                elif hasattr(output_msg, "response_metadata") and output_msg.response_metadata:
                    resp_meta = output_msg.response_metadata
                    print("identified tokens in response_metadata")
                    
                    # Groq specific mapping
                    if "x_groq" in resp_meta and "usage" in resp_meta["x_groq"]:
                        total_tokens += resp_meta["x_groq"]["usage"].get("total_tokens", 0)
                    
                    # Gemini/OpenAI legacy mapping
                    elif "token_usage" in resp_meta:
                        total_tokens += resp_meta["token_usage"].get("total_tokens", 0)
                
                # Debugging log so you can see exactly what the LLM returned
                if total_tokens == 0:
                    print(f"⚠️ Could not find token usage. Raw metadata: {getattr(output_msg, 'response_metadata', 'None')}")
                else:
                    print(f"✅ Captured {total_tokens} tokens for this generation.")

    # Signal the React frontend that the stream is complete
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
    # 3. Fire off the evaluation in the background right before the stream closes
    asyncio.create_task(
        save_and_evaluate_trace(
            thread_id=thread_id,
            query=question,
            context=retrieved_context,
            response=full_response,
            total_tokens=total_tokens,
            guardrail_flagged=False
        )
    )


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
 
async def check_safety_groq(query: str) -> bool:
    """
    Evaluates a user prompt using Groq's Llama Guard 3.
    Returns True if the prompt is flagged as unsafe, False if safe.
    """
    try:
        # We use temperature 0 for strict, deterministic safety classification
        guard_llm = ChatGroq(
            model="meta-llama/llama-prompt-guard-2-86m",
            temperature=0.0,
        )
        response = await guard_llm.ainvoke([HumanMessage(content=query)])
        output = response.content.strip().lower()
        # Llama Guard outputs "safe" or "unsafe\n[category_code]"
        try:
            score = float(output)
            # If the model is more than 50% sure it's an injection/unsafe, flag it.
            if score > 0.5:
                print(f"🚨 Guardrail triggered! Confidence Score: {score}")
                return True
            return False
            
        # ATTEMPT 2: Handle text-based labels (like "unsafe" or "injection")
        except ValueError:
            output_lower = output.lower()
            if "unsafe" in output_lower or "injection" in output_lower or "jailbreak" in output_lower:
                print(f"🚨 Guardrail triggered! Text matched: {output}")
                return True
 
        return False
    except Exception as e:
        print(f"⚠️ Groq guardrail check failed, defaulting to safe: {e}")
        return False

async def check_toxicity(query: str) -> bool:
    try:
        guard_llm = ChatGroq(model="llama-guard-3-8b", temperature=0.0)
        response = await guard_llm.ainvoke([HumanMessage(content=query)])
        output = response.content.strip().lower()

        try:
            score = float(output)
            # If the model is more than 50% sure it's an injection/unsafe, flag it.
            if score > 0.5:
                print(f"🚨 Guardrail triggered! Confidence Score: {score}")
                return True
            return False
        except ValueError:
            output_lower = output.lower()
            if "unsafe" in output_lower or "injection" in output_lower or "jailbreak" in output_lower:
                print(f"🚨 Guardrail triggered! Text matched: {output}")
                return True
        return False
    except Exception as e:
        print(f"⚠️ Groq guardrail check failed, defaulting to safe: {e}")
        return False

async def run_all_guardrails(query: str) -> bool:
    """Runs both checks concurrently. Returns True if EITHER fails."""

    # asyncio.gather runs them at the exact same time
    results = await asyncio.gather(
        check_safety_groq(query),
        check_toxicity(query)
    )

    # results will be a list like [False, True]
    is_injection, is_toxic = results

    return is_injection or is_toxic
