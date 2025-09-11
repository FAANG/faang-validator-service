import asyncio
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


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


class FileProcessor:
    def __init__(self, hub: WSHub):
        self.hub = hub

    async def process(self, path: str, filename: str, total: int):
        try:
            await self.hub.broadcast({"type": "status", "stage": 1, "msg": f"Preparing to parse: {filename}"})
            await asyncio.sleep(1.0)

            await self.hub.broadcast({"type": "status", "stage": 2, "msg": "Scanning file structure..."})
            await asyncio.sleep(1.5)

            await self.hub.broadcast({"type": "status", "stage": 3, "msg": "Computing checksum & stats..."})
            sha, lines = hashlib.sha256(), 0
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    sha.update(chunk)
                    lines += chunk.count(b"\n")

            await self.hub.broadcast({"type": "status", "stage": 4, "msg": "Post-processing..."})
            await asyncio.sleep(1.0)

            await self.hub.broadcast({
                "type": "result",
                "filename": filename,
                "size": total,
                "lines_estimate": lines,
                "sha256": sha.hexdigest(),
            })

            await self.hub.broadcast({"type": "status", "stage": 5, "msg": "Done"})
        except Exception as e:
            await self.hub.broadcast({"type": "error", "detail": str(e)})
        finally:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


app = FastAPI()
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

hub = WSHub()
processor = FileProcessor(hub)


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

    await hub.broadcast({"type": "uploaded", "filename": filename, "size": size})
    asyncio.create_task(processor.process(tmp, filename, size))
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
