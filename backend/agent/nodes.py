import os, asyncio
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers import EnsembleRetriever
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

# Import our custom state and services
from .state import GraphState
from services.neo4j_client import get_graph_context
from services.pgvector_client import get_pgvector_client

def get_llm(model_type: str = "fast", temperature: float = 0):
    """
    Dynamically loads the LLM based on the LLM_PROVIDER environment variable.
    Selects the appropriate tier (fast vs. reasoning) for the chosen provider.
    """
    provider = os.getenv("LLM_PROVIDER", "google").lower()

    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Update these strings to the active models
        model_name = "gemini-2.0-flash" if model_type == "fast" else "gemini-2.0-flash"
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)

    elif provider == "groq":
        from langchain_groq import ChatGroq
        # Llama 3.1 8B for speed, Llama 3.3 70B for complex Graph reasoning
        model_name = "llama-3.1-8b-instant" if model_type == "fast" else "llama-3.1-8b-instant"
        return ChatGroq(model=model_name, temperature=temperature)

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        # GPT-4o-mini for speed, GPT-4o for complex Graph reasoning
        model_name = "gpt-4o-mini" if model_type == "fast" else "gpt-4o"
        return ChatOpenAI(model=model_name, temperature=temperature)

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER configuration: {provider}")

llm_fast = get_llm(model_type="fast", temperature=0)
llm_reasoning = get_llm(model_type="reasoning", temperature=0)

# Initialize the Cross-Encoder for Re-ranking
cross_encoder_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
reranker = CrossEncoderReranker(model=cross_encoder_model, top_n=8)



async def rewrite_query(state: GraphState):
    """
    Node 1: Asynchronously rewrites the user's raw input to optimize it for 
    retrieval against SEC filings.
    """
    print("---NODE: REWRITE QUERY---")
    original_question = state["original_question"]

    # system_prompt = (
    #     "You are an expert financial AI. Rewrite the following input into a highly "
    #     "optimized search query that targets SEC 10-K filings, focusing on "
    #     "entities, revenue streams, and risk factors."
    # )

    # prompt = ChatPromptTemplate.from_messages([
    #     ("system", system_prompt),
    #     ("human", "Original Question: {question}\nOptimized Query:")
    # ])

    # rewriter_chain = prompt | llm_fast | StrOutputParser()

    # # Use asynchronous invocation
    # optimized_query = await rewriter_chain.ainvoke({"question": original_question})

    return {"optimized_query": original_question}


async def hybrid_retrieve(state: dict):
    print("---NODE: HYBRID RETRIEVE---")
    query = state["original_question"]

    # 1. Get Vector Client (Assuming you have get_pgvector_client from previous steps)
    pgvector_client = await get_pgvector_client()
    pg_vector_retriever = pgvector_client.as_retriever(search_kwargs={"k": 15})

    # 2. Setup BM25 Retriever
    dynamic_docs = state.get("documents", [])
    if dynamic_docs:
        bm25_retriever = BM25Retriever.from_documents(dynamic_docs)
        bm25_retriever.k = 15

        # Combine BM25 and Vector Search
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, pg_vector_retriever],
            weights=[0.4, 0.6]
        )
    else:
        # Fallback to pure vector search if BM25 isn't initialized
        ensemble_retriever = pg_vector_retriever

    # 3. Context Compression & Re-ranking
    # This uses the reranker we initialized above
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=ensemble_retriever
    )

    # 4. Execute the full pipeline asynchronously
    compressed_docs = await compression_retriever.ainvoke(query)
    
    print(f"\n✅ HYBRID SEARCH FOUND {len(compressed_docs)} RELEVANT DOCUMENTS:")
    for i, doc in enumerate(compressed_docs):
        score = doc.metadata.get('relevance_score', 'N/A')
        print(f"\n--- 📄 DOC {i+1} | Score: {score} ---")
        # Print the first 300 characters to keep the terminal readable
        print(doc.page_content[:300] + "...\n")

    # Neo4j graph context retrieval
    try:
        # Extract keywords/entities using the fast LLM
        entity_extract_prompt = ChatPromptTemplate.from_template(
            "Extract 1 to 3 key entity names (companies, subsidiaries, financial metrics) "
            "from this question. Return ONLY a comma-separated list: {question}"
        )
        entity_chain = entity_extract_prompt | llm_fast | StrOutputParser()
        raw_entities = await entity_chain.ainvoke({"question": query})
        entities = [e.strip() for e in raw_entities.split(",") if e.strip()]

        # Fetch knowledge graph facts from Neo4j
        graph_facts = get_graph_context(entities)
        print("graph_facts")
        print(graph_facts)

        if graph_facts:
            print(f"🕸️ NEO4J GRAPH FACTS FOUND:\n{graph_facts}\n")
            # Create a synthetic document containing the graph structure
            graph_doc = Document(
                page_content=f"KNOWLEDGE GRAPH RELATIONSHIPS:\n{graph_facts}",
                metadata={"source": "neo4j_knowledge_graph", "relevance_score": 1.0}
            )
            # Insert the graph doc at the very top of context
            compressed_docs.insert(0, graph_doc)

    except Exception as e:
        print(f"⚠️ Failed to fetch from Neo4j: {e}")

    return {"documents": compressed_docs}

async def generate_response(state: GraphState):
    """
    Node 3: Synthesizes the final answer asynchronously. 
    When executed via LangGraph's astream_events API, this node's token 
    generation will stream directly to the FastAPI client.
    """
    print("---NODE: GENERATE RESPONSE---")
    question = state["original_question"]
    documents = state.get("documents", [])

    vector_text = "\n\n".join([doc.page_content for doc in documents])
    graph_text = state.get("graph_facts", "")
    full_context = f"--- TEXT DOCUMENTS ---\n{vector_text}\n\n--- GRAPH FACTS ---\n{graph_text}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a strict financial analyst assistant. Answer the user's question "
            "using ONLY the facts explicitly stated in the context below.\n\n"
            "CRITICAL RULES:\n"
            "1. If the provided context does not explicitly state a relationship or fact, "
            "you MUST state: 'The provided context does not contain sufficient information to answer this.'\n"
            "2. NEVER use words like 'infer', 'assume', 'likely', 'suggests', or 'possible mapping'.\n"
            "3. Do NOT attempt to fill in missing gaps with logical assumptions.\n\n"
            "Context:\n{context}"
        )),
        ("human", "{question}")
    ])

    rag_chain = prompt | llm_reasoning | StrOutputParser()

    # In LangGraph, we just call ainvoke here.
    # The actual streaming to the UI is handled by FastAPI capturing the
    # 'on_chat_model_stream' events generated by this invocation.
    generation = await rag_chain.ainvoke({"context": full_context, "question": question})

    return {"generation": generation}
