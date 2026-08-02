# backend/api/routes_ingestion.py
import shutil
from tempfile import NamedTemporaryFile
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, HTTPException

# Import the background worker we built previously
from workers.document_parser import process_and_ingest_sec_filing

router = APIRouter()

@router.post("/ingest")
async def upload_sec_filing(
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    fiscal_year: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Accepts a 10-K PDF upload and offloads the heavy chunking, embedding, 
    and graph extraction to a background task.
    """
    print(f"---API: Received {file.filename} for {company_name}---")

    # 1. Validate the file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # 2. Save the uploaded file to a temporary location on disk
        # delete=False ensures the file persists long enough for the background worker to read it
        temp_pdf = NamedTemporaryFile(delete=False, suffix=".pdf")
        with temp_pdf as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_path = temp_pdf.name

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}") from e

    # 3. Schedule the background task
    # We pass the file path on disk, NOT the UploadFile object itself
    background_tasks.add_task(
        process_and_ingest_sec_filing,
        file_path=file_path,
        company_name=company_name,
        fiscal_year=fiscal_year
    )

    # 4. Return a 202 Accepted immediately so the UI does not hang
    return {
        "status": "processing",
        "message": f"Document {file.filename} accepted. Ingestion started in the background.",
        "company": company_name
    }
