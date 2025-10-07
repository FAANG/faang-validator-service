import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Set, Optional, Dict
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.organism_validation import PydanticValidator, process_validation_errors
from src.file_processor import parse_contents


class WSClient:
    def __init__(self, ws: WebSocket, client_id: str):
        self.ws = ws
        self.client_id = client_id
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=5000)
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
        self.by_id: Dict[str, WSClient] = {}
        self.lock = asyncio.Lock()

    async def register(self, client: WSClient):
        async with self.lock:
            self.clients.add(client)
            self.by_id[client.client_id] = client

    async def unregister(self, client: WSClient):
        async with self.lock:
            self.clients.discard(client)
            self.by_id.pop(client.client_id, None)

    async def broadcast(self, message: dict):
        async with self.lock:
            tasks = [c.send_dict(message) for c in list(self.clients)]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to(self, client_id: str, message: dict):
        async with self.lock:
            client = self.by_id.get(client_id)
        if client:
            await client.send_dict(message)


class FileProcessor:
    def __init__(self, hub: WSHub):
        self.hub = hub

    async def process_dataurl(self, contents_data_url: str, filename: str, client_id: Optional[str]):
        send = (lambda m: self.hub.send_to(client_id, m)) if client_id else self.hub.broadcast
        try:
            await send({"type": "status", "stage": 1, "msg": f"Parsing {filename}..."})
            records, sheet_name, error_message = parse_contents(contents_data_url, filename)
            if error_message:
                await send({"type": "error", "detail": error_message})
                await asyncio.sleep(0.1)
                await send({"type": "done", "ok": False})
                return

            await send({"type": "status", "stage": 2, "msg": "Validating..."})
            validator = PydanticValidator()
            validation_results = await asyncio.to_thread(validator.validate_with_pydantic, records)

            valid_organisms = validation_results.get('valid_organisms', []) or []
            invalid_organisms = validation_results.get('invalid_organisms', []) or []

            error_data = []
            if invalid_organisms:
                await send({"type": "status", "stage": 3, "msg": "Aggregating errors..."})
                error_data = process_validation_errors(invalid_organisms, sheet_name) or []

            cols = list(records[0].keys()) if records else []
            preview = []
            for r in records[:50]:
                row = {}
                for k, v in r.items():
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        row[k] = v
                    else:
                        row[k] = json.dumps(v, ensure_ascii=False, default=str)
                preview.append(row)

            await send({"type": "status", "stage": 4, "msg": "Sending result..."})

            try:
                await send({
                    "type": "result",
                    "filename": filename,
                    "valid_count": len(valid_organisms),
                    "invalid_count": len(invalid_organisms),
                    "error_table": error_data,
                    "columns": cols,
                    "data_preview": preview,
                })
            except Exception as e:
                await send({"type": "error", "detail": f"send(result) failed: {type(e).__name__}: {e}"})
                await asyncio.sleep(0.1)
                await send({"type": "done", "ok": False})
                return

            await asyncio.sleep(0.25)

            await send({"type": "done", "ok": True})

        except Exception as e:
            await send({"type": "error", "detail": f"{type(e).__name__}: {e}"})
            await asyncio.sleep(0.1)
            await send({"type": "done", "ok": False})


app = FastAPI()

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

hub = WSHub()
processor = FileProcessor(hub)


@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/upload")
async def upload(
    contents: str = Form(...),
    filename: str = Form("input.xlsx"),
    client_id: Optional[str] = Form(None),
):
    if client_id:
        await hub.send_to(client_id, {"type": "uploaded", "filename": filename})
    else:
        await hub.broadcast({"type": "uploaded", "filename": filename})
    asyncio.create_task(processor.process_dataurl(contents, filename, client_id))
    return Response(status_code=202)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    client_id = ws.query_params.get("client_id") or uuid4().hex
    client = WSClient(ws, client_id)
    await client.start()
    await hub.register(client)
    try:
        await client.recv_forever()
    finally:
        await hub.unregister(client)
        await client.close()
