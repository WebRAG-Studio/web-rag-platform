from fastapi import APIRouter

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/status")
def voice_status() -> dict:
    return {
        "available": True,
        "mode": "browser",
        "message": "Speech recognition and synthesis use supported browser capabilities.",
    }
