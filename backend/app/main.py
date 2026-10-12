```python
"""FastAPI backend. Run: uvicorn app.main:app --reload --port 8000"""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .extract import ExtractError, extract_text
from .pipeline import Pipeline
from .samples import SAMPLES

load_dotenv()

app = FastAPI(title="MedTruth AI", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = Pipeline()


class AnalyzeRequest(BaseModel):
    report_text: str = Field(..., min_length=10, max_length=20000)
    use_llm: bool = True


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_enabled": pipeline.llm.enabled,
        "knowledge_base": pipeline.kb.meta["name"],
    }


@app.get("/api/samples")
def samples():
    return SAMPLES


@app.post("/api/analyze")
def analyze_report(req: AnalyzeRequest):
    try:
        return pipeline.run(req.report_text, req.use_llm)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))


@app.post("/api/extract")
async def extract(request: Request, filename: str = ""):
    """Extract text from an uploaded report."""
    data = await request.body()

    try:
        extracted_text = await run_in_threadpool(
            extract_text, data, filename
        )
    except ExtractError as err:
        raise HTTPException(status_code=422, detail=str(err))

    return {"text": extracted_text}


# Mount the frontend LAST so the API routes remain accessible.
frontend_dist = Path("/app/frontend/dist")

if frontend_dist.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(frontend_dist), html=True),
        name="frontend",
    )
```
