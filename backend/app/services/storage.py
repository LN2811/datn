from pathlib import Path
import uuid

from fastapi import HTTPException, UploadFile

upload_dir = Path(__file__).resolve().parents[1] / "storage"
upload_dir.mkdir(parents=True, exist_ok=True)
allowed_extensions = {".pdf", ".docx", ".pptx", ".txt", ".jpg", ".jpeg", ".png"}

def save_uploaded_file(upload_file: UploadFile) -> str:
    ext = Path(upload_file.filename or "").suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File type not allowed")

    filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / filename
    with file_path.open("wb") as buffer:
        content = upload_file.file.read()
        buffer.write(content)
    return {
        "file_path": str(file_path),
        "filename": filename,
    }
