"""LifePilot Backend - FastAPI Application."""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from core.config import settings
from core.exceptions import LifePilotException
from database import init_db, get_connection
from routers import items, focus, decisions, bookmarks, search, reviews, contacts, energy, notifications, patterns, suggestions, calendar, auth, voice, push, agent, scheduler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and validate settings on startup."""
    # Validate required settings
    errors = settings.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        if settings.is_production:
            raise RuntimeError("Cannot start in production with configuration errors")
    
    init_db()
    logger.info(f"LifePilot API started in {settings.environment} mode")
    
    # Start background services
    from services.scheduler_service import get_scheduler
    from services.job_queue_service import get_job_queue
    from services.proactive_service import PROACTIVE_HANDLERS
    
    scheduler = get_scheduler()
    job_queue = get_job_queue()
    
    # Register task handlers
    for task_type, handler in PROACTIVE_HANDLERS.items():
        scheduler.register_handler(task_type, handler)
    
    # Start scheduler and job queue automatically
    scheduler.start()
    job_queue.start()
    logger.info("Background services started automatically")
    
    yield
    
    # Cleanup on shutdown
    scheduler.stop()
    job_queue.stop()
    logger.info("Background services stopped")


# Create FastAPI app
app = FastAPI(
    title="LifePilot API",
    description="Smart Personal Life OS with AI-powered categorization",
    version="2.4.0",
    lifespan=lifespan
)


# Custom exception handler for LifePilot exceptions
@app.exception_handler(LifePilotException)
async def lifepilot_exception_handler(request: Request, exc: LifePilotException):
    """Handle custom LifePilot exceptions with consistent response format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


# Configure CORS for frontend using settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(items.router)
app.include_router(focus.router)
app.include_router(decisions.router)
app.include_router(bookmarks.router)
app.include_router(search.router)
app.include_router(reviews.router)
app.include_router(contacts.router)
app.include_router(energy.router)
app.include_router(notifications.router)
app.include_router(patterns.router)
app.include_router(suggestions.router)
app.include_router(calendar.router)
app.include_router(auth.router)
app.include_router(voice.router)
app.include_router(push.router)
app.include_router(agent.router)
app.include_router(scheduler.router)


@app.get("/api/health")
async def health_check():
    """Check API and database status."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "LifePilot API",
        "version": "1.0.0",
        "docs": "/docs"
    }
