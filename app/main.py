"""
FastAPI application entry point.

The voice agent backend exposes REST APIs for Vapi AI to call.
All endpoints return JSON responses optimized for AI function calling.

Key features:
- CORS middleware (Vapi AI frontend calls from different domains)
- Structured JSON logging
- Health check endpoint
- Global exception handlers
- Automatic OpenAPI documentation
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.logger import get_logger
from app.database import check_db_connection
from app.api import doctors, appointments

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    
    Startup:
    - Check database connectivity (fail fast if DB is down)
    - Log application start with configuration
    
    Shutdown:
    - Clean shutdown logging
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} (env: {settings.APP_ENV})")
    
    # Check database connection - fail fast if unreachable
    if not await check_db_connection():
        logger.critical("Database connection failed on startup! Exiting.")
        raise RuntimeError("Database connection failed. Check DATABASE_URL.")
    
    logger.info("Database connection verified successfully")
    logger.info(f"CORS allowed origins: {settings.cors_origins}")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production-grade Voice AI Receptionist API for Ruby Hall Clinic, Pune.\n\n"
        "Vapi AI connects to these endpoints for:\n"
        "- Booking appointments\n"
        "- Canceling appointments\n"
        "- Rescheduling appointments\n"
        "- Checking doctor availability"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware - Vapi AI may call from different origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with JSON responses"""
    logger.warning(
        f"HTTP exception on {request.url.path}",
        extra={"context": {"status_code": exc.status_code, "detail": exc.detail}}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict) else {
            "status": "error",
            "message": exc.detail
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to prevent exposing internals"""
    logger.error(
        f"Unhandled exception on {request.url.path}",
        extra={"context": {"error": str(exc)}},
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal server error occurred. Please try again."
        }
    )


# Include API routers
app.include_router(doctors.router)
app.include_router(appointments.router)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Used by:
    - Docker health checks
    - Railway/Render load balancers
    - Monitoring systems (e.g., UptimeRobot)
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with basic info"""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs" if settings.DEBUG else None,
        "timezone": settings.TIMEZONE
    }