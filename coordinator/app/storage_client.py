from typing import Iterable

import httpx


async def store_chunk(node_base_url: str, chunk_id: str, data_iter: Iterable[bytes]) -> None:
    url = node_base_url.rstrip("/") + f"/chunks/{chunk_id}"
    async with httpx.AsyncClient(timeout=None) as client:
        await client.put(url, content=b"".join(data_iter))


async def fetch_chunk(node_base_url: str, chunk_id: str) -> bytes:
    url = node_base_url.rstrip("/") + f"/chunks/{chunk_id}"
    async with httpx.AsyncClient(timeout=None) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content

