import asyncio
import argparse
import json
import random
import string
import time
import uuid
import hashlib
import httpx
import websockets
import contextlib


def make_text(user_id: int, size: int) -> str:
    prefix = f"USER:{user_id};UUID:{uuid.uuid4()}\n"
    remaining = max(size - len(prefix), 0)
    body = "".join(random.choice(string.ascii_letters + string.digits + " \n")
                   for _ in range(remaining))
    return prefix + body


async def one_user(user_id: int, http_url: str, ws_url: str, payload_size: int, timeout: float):
    client_id = f"cid-{user_id}-{uuid.uuid4().hex[:8]}"
    filename = f"input_{user_id}_{uuid.uuid4().hex[:8]}.txt"
    text = make_text(user_id, payload_size)

    expected_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    expected_lines = text.count("\n")

    msg_queue: asyncio.Queue[str] = asyncio.Queue()

    async def ws_listener():
        try:
            async with websockets.connect(f"{ws_url}?client_id={client_id}", max_size=None) as ws:
                while True:
                    msg = await ws.recv()
                    await msg_queue.put(msg)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await msg_queue.put(json.dumps({"type": "__ws_error__", "detail": str(e)}))

    listener_task = asyncio.create_task(ws_listener())

    ack_ms = None
    t0 = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{http_url}/upload",
                data={"text": text, "filename": filename, "client_id": client_id},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            ack_ms = (time.perf_counter() - t0) * 1000.0
            if resp.status_code != 202:
                return {"ok": False, "ack_ms": ack_ms, "e2e_ms": None,
                        "error": f"HTTP {resp.status_code}"}

        end_deadline = time.perf_counter() + timeout
        while True:
            remaining = end_deadline - time.perf_counter()
            if remaining <= 0:
                return {"ok": False, "ack_ms": ack_ms, "e2e_ms": None, "error": "timeout waiting result"}

            try:
                raw = await asyncio.wait_for(msg_queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                return {"ok": False, "ack_ms": ack_ms, "e2e_ms": None, "error": "timeout waiting ws message"}

            try:
                msg = json.loads(raw)
            except Exception:
                continue

            if msg.get("type") == "__ws_error__":
                return {"ok": False, "ack_ms": ack_ms, "e2e_ms": None, "error": f"ws error: {msg.get('detail')}"}

            if msg.get("type") == "result":
                if (
                    msg.get("filename") == filename
                    and msg.get("sha256") == expected_sha
                    and int(msg.get("lines_estimate", -1)) == expected_lines
                ):
                    e2e_ms = (time.perf_counter() - t0) * 1000.0
                    return {"ok": True, "ack_ms": ack_ms, "e2e_ms": e2e_ms, "error": None}

    except Exception as e:
        return {"ok": False, "ack_ms": ack_ms, "e2e_ms": None, "error": repr(e)}
    finally:
        listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener_task


async def run_load(users: int, concurrency: int, http_url: str, ws_url: str,
                   payload_size: int, timeout: float):
    sem = asyncio.Semaphore(concurrency)
    results = []

    async def run_one(i: int):
        async with sem:
            return await one_user(i, http_url, ws_url, payload_size, timeout)

    def fmt_ms(x):
        return f"{x:.1f}ms" if isinstance(x, (int, float)) else "-"

    tasks = [asyncio.create_task(run_one(i)) for i in range(users)]
    for t in asyncio.as_completed(tasks):
        try:
            res = await t
        except asyncio.CancelledError:
            res = {"ok": False, "ack_ms": None, "e2e_ms": None, "error": "task cancelled"}

        results.append(res)
        ok = "OK" if res["ok"] else "ERR"
        extra = "" if res["ok"] else f" ({res['error']})"
        print(f"[{ok}] ack={fmt_ms(res['ack_ms'])} e2e={fmt_ms(res['e2e_ms'])}{extra}")

    oks = [r for r in results if r["ok"]]
    errs = [r for r in results if not r["ok"]]

    def avg(vals):
        return sum(vals) / len(vals) if vals else None

    ack_avg = avg([r["ack_ms"] for r in oks if r["ack_ms"] is not None])
    e2e_avg = avg([r["e2e_ms"] for r in oks if r["e2e_ms"] is not None])

    print("\n=== SUMMARY ===")
    print(f"Users: {users}, Concurrency: {concurrency}, Payload: {payload_size} bytes")
    print(f"Success: {len(oks)} / {users}")
    print(f"Avg HTTP ack: {ack_avg and round(ack_avg, 1)} ms")
    print(f"Avg end-to-end (ack→result via WS): {e2e_avg and round(e2e_avg, 1)} ms")
    if errs:
        print(f"Errors ({len(errs)}):")
        for e in errs[:10]:
            print("  -", e["error"])


def parse_args():
    p = argparse.ArgumentParser(description="Stress test for /upload + /ws")
    p.add_argument("--server", default="http://localhost:8000",
                   help="Base HTTP URL of server, e.g. http://localhost:8000")
    p.add_argument("--ws", default="ws://localhost:8000/ws",
                   help="WebSocket URL, e.g. ws://localhost:8000/ws")
    p.add_argument("--users", type=int, default=100, help="Total virtual users")
    p.add_argument("--concurrency", type=int, default=20, help="Max concurrent users")
    p.add_argument("--payload-size", type=int, default=64_000,
                   help="Size of 'text' payload in bytes per user")
    p.add_argument("--timeout", type=float, default=30.0, help="Per-user timeout in seconds")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_load(
        users=args.users,
        concurrency=args.concurrency,
        http_url=args.server,
        ws_url=args.ws,
        payload_size=args.payload_size,
        timeout=args.timeout,
    ))
