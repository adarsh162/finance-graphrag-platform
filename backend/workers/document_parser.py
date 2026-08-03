# backend/workers/document_parser.py
import json
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
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


def load_json(file_path: Path) -> Tuple[List[Document], dict]:
    """
    Parses a JSON SEC filing file and automatically extracts metadata
    (Company, Year, CIK, Ticker, etc.) from top-level keys.
    """
    docs = []
    extracted_metadata = {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            # 1. Auto-extract company and year from JSON top-level keys
            company = data.get("company") or data.get("ticker") or "UNKNOWN"

            period_of_report = data.get("period_of_report", "")
            if period_of_report and "-" in period_of_report:
                year = period_of_report.split("-")[0]
            else:
                year = data.get("fiscal_year_end") or "UNKNOWN"

            extracted_metadata = {
                "company": company,
                "year": year,
                "cik": data.get("cik", ""),
                "filing_type": data.get("filing_type", "10-K"),
            }

            # 2. Iterate through items (e.g. item_1, item_1A, item_7...)
            for key, val in data.items():
                if key.startswith("item_") and isinstance(val, str) and len(val.strip()) > 50:
                    section_title = val.split("\n")[0] if "\n" in val else key
                    doc_metadata = {
                        "source": file_path.name,
                        "section": key,
                        "section_title": section_title[:100],
                    }
                    docs.append(Document(page_content=val, metadata=doc_metadata))

    except Exception as e:
        print(f"⚠️ Warning: Failed to parse JSON {file_path.name}: {e}")

    return docs, extracted_metadata

async def process_and_ingest_sec_filing(file_path_str: str, company_name: str, fiscal_year: str):
    """
    Asynchronously parses, contextually chunks, embeds with BGE, 
    and saves SEC 10-K documents (PDF or JSON) to PostgreSQL.
    """
    print(f"---INGESTION: Processing {company_name} {fiscal_year} 10-K---")

    file_path = Path(file_path_str)
    raw_docs = []

    # 1. Route based on file extension
    if file_path.suffix.lower() == '.pdf':
        loader = PyPDFLoader(file_path_str)
        raw_docs = loader.load()
        # Fallbacks for PDF if not passed explicitly
        company_name = company_name or file_path.stem
        fiscal_year = fiscal_year or "UNKNOWN"

    elif file_path.suffix.lower() == '.json':
        raw_docs, extracted_meta = load_json(file_path)
        # Auto-populate missing company/year from the JSON content
        company_name = company_name or extracted_meta.get("company", "UNKNOWN")
        fiscal_year = fiscal_year or extracted_meta.get("year", "UNKNOWN")
    else:
        print(f"❌ Unsupported file type: {file_path.suffix}")
        return

    if not raw_docs:
        print(f"⚠️ No content extracted from {file_path.name}")
        return

    # 2. Recursive Chunking optimized for dense financial tables & text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=300,
        separators=["\n\n", "\n", "•", " ", ""]
    )
    raw_chunks = text_splitter.split_documents(raw_docs)

    # Generate quick summary for contextual prefixing
    doc_summary = f"{company_name} 10-K Annual Report for {fiscal_year}."

    processed_docs: List[Document] = []

    # 3. Enrich chunks with context asynchronously
    for chunk in raw_chunks:
        # enriched_content = await generate_chunk_context(doc_summary, chunk.page_content)

        # Attach critical metadata for metadata filtering in PGVector
        section_name = chunk.metadata.get("section", "SEC Filing")
        company = chunk.metadata.get("company", "")
        metadata = {
            "company": company_name or company,
            "year": fiscal_year,
            "page": chunk.metadata.get("page", 0), # Will default to 0 for JSON files
            "source": file_path_str,
            "upload_date": datetime.utcnow().isoformat()
        }
        context_prefix = f"[Company: {company} | Section: {section_name}]\n"
        chunk.page_content = context_prefix + chunk.page_content
        text_content = chunk.page_content

        # Combine the chunk's original metadata (like JSON sections) with your base metadata
        combined_metadata = {**chunk.metadata, **metadata}

        # Create the new Document correctly
        processed_docs.append(Document(page_content=text_content, metadata=combined_metadata))
        # processed_docs.append(Document(page_content=enriched_content, metadata=metadata))

    # 4. Asynchronously push to PostgreSQL via PGVector Client
    # Uses BAAI/bge-large-en-v1.5 specified in pgvector_client.py
    pgvector_client = await get_pgvector_client()
    await pgvector_client.aadd_documents(processed_docs)
    print(f"---INGESTION COMPLETE: Inserted {len(processed_docs)} chunks into PostgreSQL---")
