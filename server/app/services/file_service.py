import io
import os
from pathlib import Path
from fastapi import UploadFile
import PyPDF2
from docx import Document

# Directory where uploaded resume files are persisted
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


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

    return text.strip()


def save_resume_bytes(candidate_id: str, filename: str, data: bytes) -> str:
    """
    Saves raw file bytes to the uploads directory.
    Returns the relative path stored in the DB (e.g. 'uploads/<id>_<filename>').
    """
    safe_filename = f"{candidate_id}_{os.path.basename(filename)}"
    dest = UPLOADS_DIR / safe_filename
    dest.write_bytes(data)
    return f"uploads/{safe_filename}"
