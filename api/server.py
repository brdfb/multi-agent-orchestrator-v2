"""FastAPI server for multi-agent orchestration."""

import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_env_source, get_provider_status, get_available_providers
from core.agent_runtime import AgentRuntime
from core.logging_utils import get_metrics, read_logs
from core.memory_engine import MemoryEngine
from core.session_manager import get_session_manager

# Server state tracking
SERVER_START_TIME = time.time()
LAST_REQUEST_TIME = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    # Startup logic
    env_source = get_env_source()
    if env_source == "environment":
        print("🔑 API keys loaded from environment variables (shell/CI)")
    elif env_source == "dotenv":
        print("📁 API keys loaded from .env file (development mode)")
    else:
        print("⚠️  No API keys detected - requests will fail")

    # Show available providers
    available = get_available_providers()
    if available:
        print(f"✓ Available providers: {', '.join(available)}")
    else:
        print("⚠️  No providers available!")

    # Show disabled providers
    all_providers = ["openai", "anthropic", "google", "openrouter"]
    disabled = [p for p in all_providers if p not in available]
    if disabled:
        print(f"✗ Disabled providers: {', '.join(disabled)}")

    yield  # Application runs here

    # Shutdown logic (if needed in future)
    # print("🛑 Server shutting down...")


# Initialize FastAPI with lifespan
app = FastAPI(
    title="Multi-Agent Orchestrator",
    description="Multi-LLM agent system with CLI, API, and UI",
    version="1.0.1",  # Updated to reflect current version
    lifespan=lifespan,
)


# Middleware to track last request time
@app.middleware("http")
async def track_request_time(request: Request, call_next):
    """Track last request timestamp for health monitoring."""
    global LAST_REQUEST_TIME
    LAST_REQUEST_TIME = time.time()
    response = await call_next(request)
    return response


# Setup templates and static files
BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "ui" / "templates"))

# Mount static files if directory exists
static_dir = BASE_DIR / "ui" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize runtime and memory
runtime = AgentRuntime()
memory = MemoryEngine()


# Request/Response models
class AskRequest(BaseModel):
    agent: str
    prompt: str
    override_model: Optional[str] = None
    mock_mode: Optional[bool] = None
    session_id: Optional[str] = None  # v0.11.0: Session tracking


class ChainRequest(BaseModel):
    prompt: str
    stages: Optional[List[str]] = None
    mock_mode: Optional[bool] = None
    session_id: Optional[str] = None  # v0.11.0: Session tracking


class RunResultResponse(BaseModel):
    agent: str
    model: str
    provider: str
    prompt: str
    response: Optional[str] = None  # Can be None when error occurs
    duration_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: str
    log_file: str
    error: Optional[str] = None
    original_model: Optional[str] = None  # If fallback was used
    fallback_reason: Optional[str] = None  # Why fallback was triggered
    fallback_used: bool = False


# API endpoints
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render main UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/ask", response_model=RunResultResponse)
async def ask(request: AskRequest):
    """
    Execute single agent request.

    Args:
        request: Agent, prompt, and optional model override

    Returns:
        RunResult with response and metadata
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt cannot be empty")

    valid_agents = ["auto", "builder", "critic", "closer"]
    if request.agent not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent: {request.agent}. Valid: {valid_agents}",
        )

    try:
        # Get or create session (v0.11.0)
        session_id = request.session_id
        if session_id:
            # Validate user-provided session_id
            session_manager = get_session_manager()
            session_manager.validate_session_id(session_id)
            # Save/update session
            session_manager.save_session(
                session_id=session_id,
                source="api",
                metadata={"user_agent": request.headers.get("User-Agent", "unknown") if hasattr(request, 'headers') else "unknown"}
            )
        # If no session_id provided, system works in stateless mode (backward compatible)

        result = runtime.run(
            agent=request.agent,
            prompt=request.prompt,
            override_model=request.override_model,
            mock_mode=request.mock_mode,
            session_id=session_id,  # v0.11.0
        )

        if result.error:
            raise HTTPException(status_code=500, detail=result.error)

        return RunResultResponse(**result.to_dict())

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/chain", response_model=List[RunResultResponse])
async def chain(request: ChainRequest):
    """
    Execute multi-agent chain.

    Args:
        request: Prompt and optional stages

    Returns:
        List of RunResults from each stage
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt cannot be empty")

    try:
        # Get or create session (v0.11.0)
        session_id = request.session_id
        if session_id:
            # Validate user-provided session_id
            session_manager = get_session_manager()
            session_manager.validate_session_id(session_id)
            # Save/update session
            session_manager.save_session(
                session_id=session_id,
                source="api",
                metadata={"user_agent": request.headers.get("User-Agent", "unknown") if hasattr(request, 'headers') else "unknown"}
            )
        # If no session_id provided, system works in stateless mode (backward compatible)

        results = runtime.chain(
            prompt=request.prompt,
            stages=request.stages,
            mock_mode=request.mock_mode,
            session_id=session_id,  # v0.11.0
        )

        # Check for errors
        errors = [r for r in results if r.error]
        if errors:
            raise HTTPException(
                status_code=500, detail=f"Chain failed: {errors[0].error}"
            )

        return [RunResultResponse(**r.to_dict()) for r in results]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/logs")
async def logs(limit: int = 20):
    """
    Get recent conversation logs.

    Args:
        limit: Maximum number of logs to return

    Returns:
        List of log records
    """
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")

    try:
        return read_logs(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {str(e)}")


@app.get("/metrics")
async def metrics():
    """
    Get aggregate metrics.

    Returns:
        Metrics dictionary
    """
    try:
        return get_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to calculate metrics: {str(e)}"
        )


def get_memory_health():
    """Get memory system health information."""
    import sqlite3

    try:
        # Database path
        db_path = Path("data/MEMORY/conversations.db")

        if not db_path.exists():
            return {
                "enabled": False,
                "database_connected": False,
                "error": "Database file not found",
            }

        # Connect directly to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Total conversations
        total = cursor.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]

        # Last conversation timestamp
        last_conv = cursor.execute(
            "SELECT timestamp FROM conversations ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        last_timestamp = last_conv[0] if last_conv else None

        # Database size
        db_size_mb = db_path.stat().st_size / (1024 * 1024)

        conn.close()

        return {
            "enabled": True,
            "database_connected": True,
            "total_conversations": total,
            "database_size_mb": round(db_size_mb, 2),
            "last_conversation": last_timestamp,
        }
    except Exception as e:
        return {
            "enabled": False,
            "database_connected": False,
            "error": str(e),
        }


def get_system_metrics():
    """Get system-level metrics."""
    try:
        # Calculate uptime
        uptime_seconds = int(time.time() - SERVER_START_TIME)

        # Get data directory size
        data_path = Path("data/CONVERSATIONS")
        total_size = sum(f.stat().st_size for f in data_path.glob("*.json") if f.is_file())
        data_size_mb = total_size / (1024 * 1024)

        # Count conversations
        conversation_count = len(list(data_path.glob("*.json")))

        # Last request time
        last_request = None
        if LAST_REQUEST_TIME:
            last_request = datetime.fromtimestamp(LAST_REQUEST_TIME, tz=timezone.utc).isoformat()

        return {
            "uptime_seconds": uptime_seconds,
            "data_directory_size_mb": round(data_size_mb, 2),
            "conversations_count": conversation_count,
            "last_request": last_request,
        }
    except Exception as e:
        return {
            "error": str(e),
        }


def get_24h_stats():
    """Get 24-hour statistics from logs."""
    try:
        metrics = get_metrics()

        # Get only last 24h worth of data
        # Since get_metrics() already filters last 1000, we'll use that
        # In a real implementation, you'd filter by timestamp

        return {
            "total_requests": metrics.get("total_conversations", 0),
            "total_tokens": metrics.get("total_tokens", 0),
            "estimated_cost_usd": metrics.get("total_cost", 0.0),
            "errors": 0,  # Would need error tracking in logs
        }
    except Exception:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "errors": 0,
        }


def calculate_health_status(available_providers, memory_health):
    """Calculate overall health status."""
    if len(available_providers) == 0:
        return "unhealthy"
    elif len(available_providers) < 2 and not memory_health.get("database_connected"):
        return "degraded"
    else:
        return "healthy"


@app.get("/health")
async def health():
    """
    Comprehensive health check endpoint.

    Returns detailed system status including:
    - Provider availability
    - Memory system health
    - System metrics (uptime, disk usage)
    - 24-hour statistics
    """
    # Provider status
    provider_status = get_provider_status()
    available_providers = get_available_providers()

    # Memory health
    memory_health = get_memory_health()

    # System metrics
    system_metrics = get_system_metrics()

    # 24h statistics
    stats_24h = get_24h_stats()

    # Calculate overall health
    overall_status = calculate_health_status(available_providers, memory_health)

    return {
        "status": overall_status,
        "service": "multi-agent-orchestrator",
        "version": "1.0.1",  # Updated to reflect v1.0.1 hotfixes
        "timestamp": datetime.now(timezone.utc).isoformat(),

        "providers": provider_status,
        "available_providers": available_providers,
        "total_available": len(available_providers),

        "memory": memory_health,
        "system": system_metrics,
        "stats_24h": stats_24h,
    }


# Memory API endpoints
@app.get("/memory/search")
async def memory_search(
    q: str,
    agent: Optional[str] = None,
    model: Optional[str] = None,
    limit: int = 10,
):
    """
    Search conversations by keyword.

    Args:
        q: Search query
        agent: Filter by agent (optional)
        model: Filter by model (optional)
        limit: Maximum results (1-100)

    Returns:
        List of matching conversations
    """
    if not q.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty")

    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    try:
        results = memory.search_conversations(
            query=q, agent=agent, model=model, limit=limit
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/memory/recent")
async def memory_recent(agent: Optional[str] = None, limit: int = 10):
    """
    Get recent conversations.

    Args:
        agent: Filter by agent (optional)
        limit: Maximum results (1-100)

    Returns:
        List of recent conversations
    """
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    try:
        results = memory.get_recent_conversations(limit=limit, agent=agent)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent: {str(e)}")


@app.get("/memory/stats")
async def memory_stats():
    """
    Get memory statistics.

    Returns:
        Statistics about stored conversations
    """
    try:
        stats = memory.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.delete("/memory/{conversation_id}")
async def memory_delete(conversation_id: int):
    """
    Delete a conversation by ID.

    Args:
        conversation_id: Conversation ID to delete

    Returns:
        Success status
    """
    try:
        deleted = memory.delete_conversation(conversation_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"success": True, "message": f"Deleted conversation {conversation_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


if __name__ == "__main__":
    import os
    import uvicorn

    # Read port from environment variable (default: 5050)
    port = int(os.getenv("PORT", "5050"))

    print(f"🚀 Starting Multi-Agent Orchestrator on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
