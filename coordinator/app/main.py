import os
from typing import List

from fastapi import Depends, FastAPI, File as FastAPIFile, HTTPException, UploadFile
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session

from .chunking import iter_file_chunks
from .db import Base, engine, get_db
from .models import Chunk, ChunkLocation, File, StorageNode
from .node_selector import select_nodes
from .storage_client import fetch_chunk, store_chunk


CHUNK_SIZE_BYTES = int(os.getenv("CHUNK_SIZE_BYTES", "1048576"))
REPLICATION_FACTOR = int(os.getenv("REPLICATION_FACTOR", "2"))

app = FastAPI(title="DFS Coordinator")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    # Seed known storage nodes from environment if provided
    seed_nodes = os.getenv("STORAGE_NODES", "")
    if not seed_nodes:
        return
    with engine.begin() as conn:
        for raw in seed_nodes.split(","):
            raw = raw.strip()
            if not raw:
                continue
            node_id, base_url = raw.split("=", 1)
            conn.execute(
                StorageNode.__table__.insert()
                .values(id=node_id, base_url=base_url, is_active=True)
                .prefix_with("ON CONFLICT (id) DO UPDATE SET base_url = EXCLUDED.base_url, is_active = TRUE")
            )


@app.post("/nodes/register")
def register_node(payload: dict, db: Session = Depends(get_db)) -> JSONResponse:
    node_id = payload.get("id")
    base_url = payload.get("base_url")
    if not node_id or not base_url:
        raise HTTPException(status_code=400, detail="id and base_url are required")

    node = db.get(StorageNode, node_id)
    if node is None:
        node = StorageNode(id=node_id, base_url=base_url, is_active=True)
        db.add(node)
    else:
        node.base_url = base_url
        node.is_active = True
    db.commit()
    db.refresh(node)
    return JSONResponse({"id": node.id, "base_url": node.base_url})


@app.post("/files")
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Create File record
    file_record = File(original_name=file.filename or "uploaded", size_bytes=len(content))
    db.add(file_record)
    db.flush()  # get file_record.id

    # Prepare chunking
    from io import BytesIO

    bio = BytesIO(content)
    index = 0

    for data, size, chunk_id in iter_file_chunks(bio, CHUNK_SIZE_BYTES):
        # Check if chunk already exists (dedup within this prototype)
        chunk = db.get(Chunk, chunk_id)
        if chunk is None:
            chunk = Chunk(id=chunk_id, file_id=file_record.id, index=index, size_bytes=size)
            db.add(chunk)
        else:
            # create a new association with correct index for this file
            chunk.file_id = file_record.id
            chunk.index = index

        # Select nodes and store replicas
        nodes: List[StorageNode] = select_nodes(db, REPLICATION_FACTOR)
        for node in nodes:
            await store_chunk(node.base_url, chunk_id, [data])
            db.add(ChunkLocation(chunk_id=chunk_id, node_id=node.id))

        index += 1

    db.commit()
    return {"file_id": file_record.id, "original_name": file_record.original_name}


@app.get("/files/{file_id}/metadata")
def file_metadata(file_id: str, db: Session = Depends(get_db)):
    file_record = db.get(File, file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail="File not found")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.file_id == file_id)
        .order_by(Chunk.index.asc())
        .all()
    )

    result = []
    for chunk in chunks:
        locations = [loc.node_id for loc in chunk.locations]
        result.append(
            {
                "chunk_id": chunk.id,
                "index": chunk.index,
                "size_bytes": chunk.size_bytes,
                "nodes": locations,
            }
        )

    return {
        "file_id": file_record.id,
        "original_name": file_record.original_name,
        "size_bytes": file_record.size_bytes,
        "chunks": result,
    }


@app.get("/files/{file_id}")
async def download_file(file_id: str, db: Session = Depends(get_db)):
    file_record = db.get(File, file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail="File not found")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.file_id == file_id)
        .order_by(Chunk.index.asc())
        .all()
    )

    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for file")

    async def chunk_stream():
        for chunk in chunks:
            # pick first available node
            if not chunk.locations:
                raise HTTPException(status_code=500, detail=f"No locations for chunk {chunk.id}")
            node = chunk.locations[0].node
            data = await fetch_chunk(node.base_url, chunk.id)
            yield data

    return StreamingResponse(chunk_stream(), media_type="application/octet-stream")

