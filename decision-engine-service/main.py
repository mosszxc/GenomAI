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
app.include_router(
    idea_registry_router, prefix="/api/idea-registry", tags=["idea-registry"]
)
app.include_router(
    recommendations_router, prefix="/recommendations", tags=["recommendations"]
)
app.include_router(schema_router, prefix="/api/schema", tags=["schema"])
app.include_router(outcomes_router, prefix="/api/outcomes", tags=["outcomes"])
app.include_router(premise_router, prefix="/premise", tags=["premise"])
app.include_router(telegram_router, tags=["telegram"])
app.include_router(historical_router, prefix="/api/historical", tags=["historical"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime

    return {"status": "ok", "timestamp": datetime.now().isoformat()}


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
