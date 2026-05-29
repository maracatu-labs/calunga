from fastapi import APIRouter

from app.database import get_pool

router = APIRouter(tags=["health"])

@router.api_route("/health", methods=["GET", "HEAD"])
async def health():
    """Liveness + database probe. Accepts HEAD for monitors that probe with HEAD
    (e.g. UptimeRobot default) and GET for monitors that want the JSON body.
    """
    pool = get_pool()
    db_ok = False
    try:
        row = await pool.fetchval("SELECT 1")
        db_ok = row == 1
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }
