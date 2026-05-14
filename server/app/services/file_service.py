import io
import os
import requests
from dotenv import load_dotenv
from fastapi import UploadFile, HTTPException
import PyPDF2
from docx import Document

# Load env variables to get Supabase credentials
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

BUCKET_NAME = "resumes"

async def extract_text_from_file(file: UploadFile) -> str:
    """
    Extracts text from an uploaded PDF or DOCX file.
    Returns the extracted text (used for ML scoring).
    Call save_upload_file() separately to persist the raw bytes.
    """
    text = ""
    content = await file.read()

    # Store raw bytes on the UploadFile object so the router can save them
    # without seeking (SpooledTemporaryFile doesn't always support seek).
    file._saved_bytes = content  # type: ignore[attr-defined]

    if file.filename and file.filename.endswith(".pdf"):
        # Process PDF
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    elif file.filename and file.filename.endswith(".docx"):
        # Process DOCX
        doc = Document(io.BytesIO(content))
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"

    else:
        # Fallback for plain text or unsupported formats (just decode)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            pass

    # Canva PDFs often export with letter-spacing that PyPDF2 reads as "C o m p u t e r".
    # This safely collapses sequences of 4+ spaced single characters back into words.
    import re
    def replacer(match):
        return match.group(0).replace(" ", "")
    text = re.sub(r"(?<![A-Za-z0-9])(?:[A-Za-z0-9] ){3,}[A-Za-z0-9](?![A-Za-z0-9])", replacer, text)

    return text.strip()


def save_resume_bytes(candidate_id: str, filename: str, data: bytes) -> str:
    """
    Saves raw file bytes to Supabase Storage.
    Returns the storage path (e.g. 'candidate_id/filename').
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials are not configured.")
        
    safe_filename = f"{candidate_id}/{os.path.basename(filename)}"
    url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{safe_filename}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/octet-stream"
    }
    
    response = requests.post(url, headers=headers, data=data)
    
    # HTTP 200 format is successful upload. 400+ means failure.
    if response.status_code >= 400:
        raise Exception(f"Failed to upload to Supabase: {response.text}")

    return safe_filename
