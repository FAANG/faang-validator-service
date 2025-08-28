import asyncio
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Set

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")

clients: Set[WebSocket] = set()


async def broadcast(message: dict) -> None:
    data = json.dumps(
        {**message, "ts": datetime.now(timezone.utc).isoformat()},
        ensure_ascii=False,
    )
    dead = []
    for ws in list(clients):
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


async def process_file(path: str, filename: str, total: int):
    try:
        await broadcast({"type": "status", "stage": 1, "msg": f"Preparing to parse: {filename}"})
        await asyncio.sleep(1.0)

        await broadcast({"type": "status", "stage": 2, "msg": "Scanning file structure..."})
        await asyncio.sleep(1.5)

        await broadcast({"type": "status", "stage": 3, "msg": "Computing checksum & stats..."})
        sha, lines, processed = hashlib.sha256(), 0, 0
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                sha.update(chunk)
                processed += len(chunk)
                lines += chunk.count(b"\n")

        await broadcast({"type": "status", "stage": 4, "msg": "Post-processing..."})
        await asyncio.sleep(1.0)

        await broadcast({
            "type": "result",
            "filename": filename,
            "size": total,
            "lines_estimate": int(lines),
            "sha256": sha.hexdigest(),
        })
        await broadcast({"type": "status", "stage": 5, "msg": "Done"})
    except Exception as e:
        await broadcast({"type": "error", "detail": str(e)})
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    fd, tmp = tempfile.mkstemp(prefix="up_", suffix=f"_{file.filename or 'file'}")
    os.close(fd)

    size = 0
    with open(tmp, "wb") as out:
        while True:
            chunk = await file.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            size += len(chunk)
    await file.close()

    await broadcast({"type": "uploaded", "filename": file.filename, "size": size})

    asyncio.create_task(process_file(tmp, file.filename or "file", size))
    return Response(status_code=202)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)
