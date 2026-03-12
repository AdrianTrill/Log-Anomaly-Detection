from fastapi import APIRouter, UploadFile, File
from app.models.schemas import UploadResponse
from app.services.parser import parse_log_lines
from app.services.normalizer import normalize_entries
from app.services.summarizer import generate_summary
from app.utils.file_utils import validate_file_extension, read_lines_from_upload

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_and_parse(file: UploadFile = File(...)):
    validate_file_extension(file.filename or "unknown")

    lines = await read_lines_from_upload(file)
    total_lines = len(lines)

    entries = parse_log_lines(lines)
    entries, normalization_info = normalize_entries(entries)
    response = generate_summary(entries, file.filename or "unknown", total_lines, normalization_info)

    return response
