"""FGC Flow API — FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fgc_flow_api.config import settings
from fgc_flow_api.database import init_jobs_db
from fgc_flow_api.exceptions import FGCFlowException
from fgc_flow_api.routers import auth_router
from fgc_flow_api.schemas.error import ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database connections on startup."""
    await init_jobs_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="RESTful API for power flow simulations using FGC-Flow solvers.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)

# ── Global Exception Handlers ─────────────────────────────────────────


@app.exception_handler(FGCFlowException)
async def fgc_flow_exception_handler(request: Request, exc: FGCFlowException):
    """Handle custom fgc_flow_api exceptions with structured error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_code=exc.error_code,
            extra=exc.extra if exc.extra else None,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """Handle Pydantic/FastAPI validation errors with structured format."""
    errors = exc.errors()
    field_errors = [
        {
            "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in errors
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            detail="Validation error",
            error_code="validation-error",
            extra={"field_errors": field_errors},
        ).model_dump(),
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors with structured format."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            detail="The requested resource was not found",
            error_code="not-found",
        ).model_dump(),
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc):
    """Handle 405 errors with structured format."""
    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content=ErrorResponse(
            detail="Method not allowed",
            error_code="method-not-allowed",
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions (500)."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="An internal error occurred",
            error_code="internal-error",
        ).model_dump(),
    )


# ── Health Check ──────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health():
    """Health check endpoint — returns status ok if the app is running."""
    return {"status": "ok"}
