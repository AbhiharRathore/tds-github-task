import logging
import time
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint

STUDENT_EMAIL = "23f2003903@ds.study.iitm.ac.in"
ALLOWED_ORIGIN = "https://dash-78863e.example.com"

logger = logging.getLogger(__name__)


class StatsResponse(BaseModel):
    email: str
    count: int
    sum: int
    min: int
    max: int
    mean: float


app = FastAPI(
    title="FastAPI Statistics API",
    description="Calculates statistics for comma-separated integers.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET"],
    allow_headers=[],
)


@app.middleware("http")
async def add_response_metadata(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    request_id = str(uuid4())
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error while processing request %s", request_id)
        response = Response(
            content='{"detail":"Internal Server Error"}',
            status_code=500,
            media_type="application/json",
        )

    elapsed = max(time.perf_counter() - started_at, 0.0)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{elapsed:.9f}"
    return response


def calculate_stats(values: str) -> StatsResponse:
    try:
        numbers = [int(value.strip()) for value in values.split(",")]
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="values must be a comma-separated list of integers",
        ) from exc

    count = len(numbers)
    if count == 0:
        raise HTTPException(status_code=422, detail="values must not be empty")

    total = sum(numbers)
    return StatsResponse(
        email=STUDENT_EMAIL,
        count=count,
        sum=total,
        min=min(numbers),
        max=max(numbers),
        mean=total / count,
    )


@app.get("/stats", response_model=StatsResponse)
def stats(values: str = Query(..., description="Comma-separated integers")) -> StatsResponse:
    return calculate_stats(values)
