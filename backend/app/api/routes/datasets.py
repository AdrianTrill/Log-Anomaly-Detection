from fastapi import APIRouter, HTTPException
from app.models.schemas import DatasetsListResponse, DatasetPreviewRequest, UploadResponse
from app.services.dataset_loader import list_datasets, load_and_parse

router = APIRouter(tags=["datasets"])


@router.get("/datasets", response_model=DatasetsListResponse)
async def get_datasets():
    """List all registered datasets that are present on disk."""
    return list_datasets()


@router.post("/datasets/preview", response_model=UploadResponse)
async def preview_dataset(request: DatasetPreviewRequest):
    """Parse a slice of a dataset and return the same UploadResponse
    the frontend already understands from the /upload endpoint."""
    try:
        return load_and_parse(
            request.dataset_name,
            max_lines=request.max_lines,
            start_line=request.start_line,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
