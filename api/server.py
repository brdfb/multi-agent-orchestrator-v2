"""FastAPI server for multi-agent orchestration."""

import sys
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

# Initialize FastAPI
app = FastAPI(
    title="Multi-Agent Orchestrator",
    description="Multi-LLM agent system with CLI, API, and UI",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event():
    """Log environment source and provider status on startup."""
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


# Setup templates and static files
BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "ui" / "templates"))

# Mount static files if directory exists
static_dir = BASE_DIR / "ui" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize runtime
runtime = AgentRuntime()


# Request/Response models
class AskRequest(BaseModel):
    agent: str
    prompt: str
    override_model: Optional[str] = None


class ChainRequest(BaseModel):
    prompt: str
    stages: Optional[List[str]] = None


class RunResultResponse(BaseModel):
    agent: str
    model: str
    provider: str
    prompt: str
    response: str
    duration_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: str
    log_file: str
    error: Optional[str] = None


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
        result = runtime.run(
            agent=request.agent,
            prompt=request.prompt,
            override_model=request.override_model,
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
        results = runtime.chain(prompt=request.prompt, stages=request.stages)

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


@app.get("/health")
async def health():
    """Health check endpoint with provider status."""
    provider_status = get_provider_status()
    available_providers = get_available_providers()

    return {
        "status": "ok",
        "service": "multi-agent-orchestrator",
        "providers": provider_status,
        "available_providers": available_providers,
        "total_available": len(available_providers),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5050)
