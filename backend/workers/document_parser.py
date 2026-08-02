# backend/workers/document_parser.py
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from services.pgvector_client import get_pgvector_client

llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0)

async def generate_chunk_context(doc_summary: str, chunk_text: str) -> str:
    """
    Prepends context to a chunk to prevent semantic detachment 
    (Anthropic Contextual Retrieval pattern).
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Here is the summary of the parent SEC filing: {doc_summary}"),
        ("human", "Here is a specific excerpt from that document: {chunk}\n"
                  "Please give a 1-sentence context prefix for this chunk.")
    ])

    context_chain = prompt | llm_fast | StrOutputParser()
    prefix = await context_chain.ainvoke({"doc_summary": doc_summary, "chunk": chunk_text})
    return f"[Context: {prefix}]\n\n{chunk_text}"

async def process_and_ingest_sec_filing(file_path: str, company_name: str, fiscal_year: str):
    """
    Asynchronously parses, contextually chunks, embeds with BGE, 
    and saves SEC 10-K documents to PostgreSQL.
    """
    print(f"---INGESTION: Processing {company_name} {fiscal_year} 10-K---")

    # 1. Load PDF
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    # 2. Recursive Chunking optimized for dense financial tables & text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )
    raw_chunks = text_splitter.split_documents(pages)

    # Generate quick summary for contextual prefixing
    doc_summary = f"{company_name} 10-K Annual Report for {fiscal_year}."

    processed_docs: List[Document] = []

    # 3. Enrich chunks with context asynchronously
    for chunk in raw_chunks:
        # enriched_content = await generate_chunk_context(doc_summary, chunk.page_content)

        # Attach critical metadata for metadata filtering in PGVector
        metadata = {
            "company": company_name,
            "year": fiscal_year,
            "page": chunk.metadata.get("page", 0),
            "source": file_path
        }
        text_content = chunk.page_content

        # Combine the chunk's original metadata with your new metadata
        combined_metadata = {**chunk.metadata, **metadata}

        # Create the new Document correctly
        processed_docs.append(Document(page_content=text_content, metadata=combined_metadata))

        # processed_docs.append(Document(page_content=enriched_content, metadata=metadata))

    # 4. Asynchronously push to PostgreSQL via PGVector Client
    # Uses BAAI/bge-large-en-v1.5 specified in pgvector_client.py
    pgvector_client = await get_pgvector_client()
    await pgvector_client.aadd_documents(processed_docs)
    print(f"---INGESTION COMPLETE: Inserted {len(processed_docs)} chunks into PostgreSQL---")
