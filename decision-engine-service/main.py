"""
Decision Engine Service - Python/FastAPI
REST API service for deterministic decision making in GenomAI
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.routes.decision import router as decision_router
from src.routes.learning import router as learning_router
from src.routes.idea_registry import router as idea_registry_router
from src.routes.recommendations import router as recommendations_router
from src.routes.schema import router as schema_router
from src.routes.outcomes import router as outcomes_router
from src.routes.premise import router as premise_router
from src.routes.telegram import router as telegram_router
from src.routes.historical import router as historical_router
from src.routes.schedules import router as schedules_router
from src.routes.knowledge import router as knowledge_router
from src.routes.transcripts import router as transcripts_router
from src.routes.dashboard import router as dashboard_router
from src.routes.auth import router as auth_router
from src.utils.errors import DecisionEngineError

# Environment variables
PORT = int(os.getenv("PORT", "10000"))

app = FastAPI(
    title="Decision Engine Service",
    description="Deterministic decision engine for GenomAI",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(decision_router, prefix="/api/decision", tags=["decision"])
app.include_router(learning_router, prefix="/learning", tags=["learning"])
app.include_router(idea_registry_router, prefix="/api/idea-registry", tags=["idea-registry"])
app.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
app.include_router(schema_router, prefix="/api/schema", tags=["schema"])
app.include_router(outcomes_router, prefix="/api/outcomes", tags=["outcomes"])
app.include_router(premise_router, prefix="/premise", tags=["premise"])
app.include_router(telegram_router, tags=["telegram"])
app.include_router(transcripts_router, tags=["transcripts"])
app.include_router(historical_router, prefix="/api/historical", tags=["historical"])
app.include_router(schedules_router, prefix="/api/schedules", tags=["schedules"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["knowledge"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


@app.get("/health")
async def health_check():
    """
    Health check endpoint with service status details.

    Returns status of:
    - API: always ok if this endpoint responds
    - Database: Supabase connection check
    - Temporal: Temporal Cloud connection check
    """
    from datetime import datetime
    import httpx

    from src.core.supabase import get_supabase
    from temporal.client import get_temporal_client

    timestamp = datetime.now().isoformat()

    # API is always ok if we got here
    api_status = {"status": "ok"}

    # Check Database (Supabase)
    database_status = {"status": "unknown"}
    try:
        sb = get_supabase()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{sb.rest_url}/creatives?select=id&limit=1",
                headers=sb.get_headers(),
            )
            if response.status_code == 200:
                database_status = {"status": "ok"}
            else:
                database_status = {"status": "degraded", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        database_status = {"status": "down", "message": str(e)[:100]}

    # Check Temporal
    temporal_status = {"status": "unknown"}
    try:
        client = await get_temporal_client()
        # Simple check - if we can get the client, it's connected
        if client:
            temporal_status = {"status": "ok"}
    except Exception as e:
        temporal_status = {"status": "down", "message": str(e)[:100]}

    # Calculate overall status
    statuses = [api_status["status"], database_status["status"], temporal_status["status"]]
    if "down" in statuses:
        overall = "degraded"
    elif "degraded" in statuses or "unknown" in statuses:
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "status": overall,
        "timestamp": timestamp,
        "services": {
            "api": api_status,
            "database": database_status,
            "temporal": temporal_status,
        },
    }


@app.get("/health/metrics")
async def metrics_health_check():
    """
    Metrics health check endpoint (Issue #474)

    Returns metrics staleness information and circuit breaker state.
    Use this to monitor if the metrics pipeline is healthy.

    Response:
    - status: "healthy" | "degraded" | "error"
    - metrics_staleness_minutes: minutes since last metrics update
    - is_stale: true if metrics are older than 30 minutes
    - circuit_breaker: current circuit breaker state

    Alert if:
    - status != "healthy"
    - is_stale == true
    - circuit_breaker.state == "open"
    """
    from temporal.circuit_breaker import get_metrics_staleness

    return await get_metrics_staleness()


@app.exception_handler(DecisionEngineError)
async def decision_engine_error_handler(request, exc: DecisionEngineError):
    """Handle DecisionEngineError exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": exc.code, "message": exc.message, "details": exc.details},
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": str(exc), "details": {}},
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
