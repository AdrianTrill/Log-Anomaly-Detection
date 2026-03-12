from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalysisRequest, AnalysisResponse, LogEntry
from app.services.model_registry import registry

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_logs(request: AnalysisRequest):
    analyzer = registry.get_analyzer(request.model_name)
    if not analyzer:
        available = registry.available_model_names()
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.model_name}' not found. Available: {available}",
        )

    placeholder_entries = [
        LogEntry(
            id=eid,
            line_number=0,
            raw_line="",
            parse_status="parsed",
        )
        for eid in request.entry_ids
    ]

    results = analyzer.analyze(placeholder_entries)
    info = analyzer.model_info()

    return AnalysisResponse(
        model_name=info.model_name,
        status=info.status,
        entries=results,
        message="Model inference is not yet implemented. This is a placeholder response.",
    )
