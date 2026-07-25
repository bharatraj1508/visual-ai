"""Live smoke test for the agent — requires a real GOOGLE_API_KEY in .env.

Runs the whole stack in-process (no server needed): register → upload a tiny
CSV → open a chat session → ask a question → stream the REAL Gemini agent and
print its tokens, tool calls, and any charts it produces.

    python scripts/smoke_chat.py

Prereqs: Postgres up (docker compose up -d db) and migrations applied
(alembic upgrade head).
"""
import asyncio
import csv
import io
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from httpx import ASGITransport  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

SAMPLE_ROWS = [
    {"student": n, "month": m, "present": p, "total": 20}
    for n, base in [("Aisha", 19), ("Ben", 12), ("Carlos", 16)]
    for m, p in [("Jan", base), ("Feb", base - 1), ("Mar", base - 2)]
]


def _csv_bytes() -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SAMPLE_ROWS[0].keys())
    w.writeheader()
    w.writerows(SAMPLE_ROWS)
    return buf.getvalue().encode()


async def main() -> None:
    key = settings.GOOGLE_API_KEY
    if key is None or key.get_secret_value().startswith("your-"):
        print("ERROR: set a real GOOGLE_API_KEY in .env first.")
        raise SystemExit(1)

    email = f"smoke_{uuid.uuid4().hex[:8]}@example.com"
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", timeout=120
    ) as c:
        await c.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
        tok = (await c.post("/api/v1/auth/login", data={"username": email, "password": "supersecret123"})).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}

        did = (await c.post("/api/v1/datasets", headers=h,
                            files={"file": ("attendance.csv", _csv_bytes(), "text/csv")})).json()["id"]
        sid = (await c.post("/api/v1/chat/sessions", headers=h, json={"dataset_id": did})).json()["id"]

        question = "Which student has the best average attendance percentage? Draw a bar chart of it."
        print(f"\n>>> {question}\n")
        charts = 0
        async with c.stream("POST", f"/api/v1/chat/sessions/{sid}/messages",
                            headers=h, json={"content": question}) as resp:
            event = None
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    data = line.split(":", 1)[1].strip()
                    if event == "token":
                        print(data, end="", flush=True)
                    elif event == "tool_start":
                        print(f"\n  [tool] {data}", flush=True)
                    elif event == "chart":
                        charts += 1
                        print(f"\n  [chart #{charts} received]", flush=True)
                    elif event == "error":
                        print(f"\n  [error] {data}", flush=True)
        print(f"\n\nDone. Charts produced: {charts}")


if __name__ == "__main__":
    asyncio.run(main())
