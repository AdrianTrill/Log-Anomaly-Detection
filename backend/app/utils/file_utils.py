from fastapi import UploadFile, HTTPException

ALLOWED_EXTENSIONS = {".log", ".txt", ".csv"}


def validate_file_extension(filename: str) -> None:
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


async def read_lines_from_upload(file: UploadFile) -> list[str]:
    content = await file.read()
    # errors="replace" substitutes invalid bytes with U+FFFD so parsing
    # never fails on binary-corrupted log segments.
    text = content.decode("utf-8", errors="replace")
    return text.splitlines()
