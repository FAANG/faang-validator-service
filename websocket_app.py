import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from celery.result import AsyncResult
from celery_app import celery_app
from tasks import process_file


class WSClient:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        self.sender_task: asyncio.Task | None = None

    async def start(self):
        await self.ws.accept()
        self.sender_task = asyncio.create_task(self._sender())

    async def _sender(self):
        try:
            while True:
                msg = await self.queue.get()
                await self.ws.send_text(msg)
        except Exception:
            pass

    async def recv_forever(self):
        try:
            while True:
                await self.ws.receive_text()
        except WebSocketDisconnect:
            pass

    async def send_dict(self, message: dict):
        try:
            message["ts"] = datetime.now(timezone.utc).isoformat()
            await self.queue.put(json.dumps(message, ensure_ascii=False))
        except asyncio.QueueFull:
            pass

    async def close(self):
        try:
            await self.ws.close()
        except Exception:
            pass
        if self.sender_task:
            self.sender_task.cancel()


class WSHub:
    def __init__(self):
        self.clients: Set[WSClient] = set()
        self.lock = asyncio.Lock()

    async def register(self, client: WSClient):
        async with self.lock:
            self.clients.add(client)

    async def unregister(self, client: WSClient):
        async with self.lock:
            self.clients.discard(client)

    async def broadcast(self, message: dict):
        async with self.lock:
            tasks = [client.send_dict(message) for client in list(self.clients)]
        await asyncio.gather(*tasks, return_exceptions=True)


async def watch_task(hub: "WSHub", task_id: str, poll_interval: float = 0.5):
    """
    """
    prev: Optional[tuple[str, str]] = None
    while True:
        r = AsyncResult(task_id, app=celery_app)
        state, meta = r.state, (r.info or {})
        cur = (state, json.dumps(meta, sort_keys=True, ensure_ascii=False))
        if cur != prev:
            if state == "PROGRESS":
                await hub.broadcast({"type": "status", **(meta or {}), "task_id": task_id})
            elif state == "SUCCESS":
                await hub.broadcast({"type": "result", **(meta or {}), "task_id": task_id})
            elif state in ("FAILURE", "REVOKED"):
                await hub.broadcast({
                    "type": "error",
                    "task_id": task_id,
                    "detail": getattr(r, "traceback", "") or (meta or {}).get("detail"),
                })
            else:
                await hub.broadcast({"type": "task", "task_id": task_id, "state": state, "meta": meta})
            prev = cur

        if state in ("SUCCESS", "FAILURE", "REVOKED"):
            break
        await asyncio.sleep(poll_interval)


app = FastAPI()
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

hub = WSHub()


@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/upload")
async def upload(text: str = Form(...), filename: str = Form("input.txt")):
    fd, tmp = tempfile.mkstemp(prefix="txt_", suffix=f"_{filename}")
    os.close(fd)

    data = text.encode("utf-8")
    with open(tmp, "wb") as f:
        f.write(data)
    size = len(data)

    async_result = process_file.delay(tmp, filename, size)
    task_id = async_result.id

    await hub.broadcast({"type": "uploaded", "filename": filename, "size": size, "task_id": task_id})
    asyncio.create_task(watch_task(hub, task_id))

    return Response(status_code=202)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client = WSClient(ws)
    await client.start()
    await hub.register(client)
    try:
        await client.recv_forever()
    finally:
        await hub.unregister(client)
        await client.close()
