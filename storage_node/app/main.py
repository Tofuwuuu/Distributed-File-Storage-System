from pathlib import Path
from typing import AsyncIterator

import os

import aiofiles
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from .config import settings


app = FastAPI(title="DFS Storage Node")


def _chunk_path(chunk_id: str) -> Path:
    # Store each chunk as a file named by its ID in the data directory
    return settings.data_dir / chunk_id


async def _iter_request_body(request: Request, buffer_size: int = 1024 * 64) -> AsyncIterator[bytes]:
    async for chunk in request.stream():
        if not chunk:
            continue
        yield chunk


@app.on_event("startup")
async def on_startup() -> None:
    # Ensure data directory exists
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Optionally register with coordinator if URL provided
    if settings.coordinator_url:
        register_url = settings.coordinator_url.rstrip("/") + "/nodes/register"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    register_url,
                    json={
                        "id": settings.node_id,
                        "base_url": os.getenv("BASE_URL", ""),
                    },
                )
        except Exception:
            # Registration failure should not prevent node from serving traffic
            pass


@app.put("/chunks/{chunk_id}", status_code=201)
async def put_chunk(chunk_id: str, request: Request) -> JSONResponse:
    target_path = _chunk_path(chunk_id)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(target_path, "wb") as f:
        async for body_chunk in _iter_request_body(request):
            await f.write(body_chunk)

    return JSONResponse({"chunk_id": chunk_id, "stored": True})


@app.get("/chunks/{chunk_id}")
async def get_chunk(chunk_id: str):
    target_path = _chunk_path(chunk_id)
    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="Chunk not found")

    return FileResponse(target_path, media_type="application/octet-stream", filename=chunk_id)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "node_id": settings.node_id}


@app.get("/stats")
async def stats() -> dict:
    total_bytes = 0
    total_chunks = 0

    if settings.data_dir.is_dir():
        for root, _, files in os.walk(settings.data_dir):
            for name in files:
                fp = Path(root) / name
                try:
                    total_bytes += fp.stat().st_size
                    total_chunks += 1
                except OSError:
                    continue

    return {
        "node_id": settings.node_id,
        "total_chunks": total_chunks,
        "total_bytes": total_bytes,
    }

