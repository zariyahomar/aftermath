
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from langchain_core.messages import HumanMessage

from aftermath.config import ROOT, settings
from aftermath.data_loader import load_pdf
from aftermath.graph import get_graph
from aftermath.memory import clear_thread
from aftermath.repository import (
    clear_obligations,
    clear_profile,
    init_db,
    list_obligations,
    upsert_profile,
)
from aftermath.schemas import IngestRequest, ProfileUpdate, RunRequest
from aftermath.vector_store import (
    clear_user_uploads,
    ensure_knowledge_indexed,
)


STATIC = ROOT / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()

    try:
        if settings.gemini_api_key:
            ensure_knowledge_indexed()
    except Exception:
        pass

    yield


app = FastAPI(
    title="AfterMath",
    version="0.1.0",
    lifespan=lifespan,
)


if STATIC.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC),
        name="assets",
    )


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": settings.gemini_model,
        "has_key": bool(settings.gemini_api_key),
    }


@app.get("/obligations/{user_id}")
def get_obligations(user_id: str):
    return {
        "obligations": list_obligations(user_id)
    }


@app.post("/profile/{user_id}")
def update_profile(user_id: str, body: ProfileUpdate):
    return upsert_profile(
        user_id,
        payday_day=body.payday_day,
        available_cash=body.available_cash,
        currency=body.currency,
    )

@app.delete("/user/{user_id}/data")
def clear_user_data(
    user_id: str,
    thread_id: str | None = None,
):
    """
    Delete all persisted user-specific AfterMath data.
    """

    clear_obligations(user_id)
    clear_profile(user_id)

    deleted_vectors = clear_user_uploads(user_id)

    # The ingest thread is deterministic.
    clear_thread(f"{user_id}-ingest")

    # Also clear the current browser/session thread.
    if thread_id:
        clear_thread(thread_id)

    return {
        "ok": True,
        "user_id": user_id,
        "deleted_vectors": deleted_vectors,
    }

def _require_key():
    if not settings.gemini_api_key:
        raise HTTPException(
            503,
            "Set GOOGLE_API_KEY in .env.",
        )


def _invoke(
    body: RunRequest,
    raw_text: str | None = None,
) -> dict:

    _require_key()

    graph = get_graph()

    intent = None if body.intent == "auto" else body.intent

    state: dict = {
        "user_id": body.user_id,
        "messages": [
            HumanMessage(content=body.message)
        ],
        "available_cash": body.available_cash,
    }

    if intent:
        state["intent"] = intent

    if raw_text:
        state["raw_text"] = raw_text

    config = {
        "configurable": {
            "thread_id": body.thread_id[:255],
            "user_id": body.user_id,
        }
    }

    out = graph.invoke(
        state,
        config=config,
    )

    return {
        "answer": out.get("answer"),
        "intent": out.get("intent"),
        "obligations": (
            out.get("accounts")
            or list_obligations(body.user_id)
        ),
        "extracted": out.get("extracted"),
        "plan": out.get("plan"),
        "evaluation": out.get("evaluation"),
        "citations": out.get("citations") or [],
        "warnings": out.get("warnings") or [],
    }


@app.post("/run")
def run(body: RunRequest):
    return _invoke(body)


@app.post("/ingest")
def ingest(body: IngestRequest):

    _require_key()

    if not body.text:
        raise HTTPException(
            400,
            "Provide statement text.",
        )

    req = RunRequest(
        user_id=body.user_id,
        thread_id=f"{body.user_id}-ingest",
        message="Extract obligations from this statement.",
        intent="ingest",
    )

    return _invoke(
        req,
        raw_text=body.text,
    )


@app.post("/ingest/file")
async def ingest_file(
    user_id: str = "demo",
    file: UploadFile = File(...),
):

    _require_key()

    print("PDF UPLOAD RECEIVED:", file.filename)

    filename = file.filename or "upload.txt"
    filename = Path(filename).name

    suffix = Path(filename).suffix.lower()

    data = await file.read()

    print("FILE TYPE:", suffix)
    print("FILE SIZE:", len(data))

    tmp = settings.data_dir / f"upload-{filename}"
    tmp.write_bytes(data)

    try:
        if suffix == ".pdf":
            text = load_pdf(tmp)
        else:
            text = data.decode(
                "utf-8",
                errors="replace",
            )
    finally:
        tmp.unlink(missing_ok=True)

    print("EXTRACTED TEXT LENGTH:", len(text))
    print("EXTRACTED TEXT:", repr(text[:2000]))

    req = RunRequest(
        user_id=user_id,
        thread_id=f"{user_id}-ingest",
        message=f"Extract obligations from {filename}.",
        intent="ingest",
    )

    return _invoke(
        req,
        raw_text=text,
    )

@app.websocket("/ws/run")
async def ws_run(ws: WebSocket):

    await ws.accept()

    try:
        payload = await ws.receive_json()

        body = RunRequest(**payload)

        _require_key()

        graph = get_graph()

        intent = (
            None
            if body.intent == "auto"
            else body.intent
        )

        state: dict = {
            "user_id": body.user_id,
            "messages": [
                HumanMessage(content=body.message)
            ],
            "available_cash": body.available_cash,
        }

        if intent:
            state["intent"] = intent

        config = {
            "configurable": {
                "thread_id": body.thread_id[:255],
                "user_id": body.user_id,
            }
        }

        async for event in graph.astream(
            state,
            config=config,
            stream_mode="updates",
        ):

            node = next(iter(event))

            await ws.send_json(
                {
                    "node": node,
                    "keys": list(
                        event[node].keys()
                    ),
                }
            )

        final = graph.get_state(
            config
        ).values

        await ws.send_json(
            {
                "done": True,
                "answer": final.get("answer"),
                "intent": final.get("intent"),
                "plan": final.get("plan"),
                "citations": final.get("citations") or [],
            }
        )

    except HTTPException as exc:

        await ws.send_json(
            {
                "error": exc.detail
            }
        )

    except WebSocketDisconnect:

        return

    except Exception as exc:

        await ws.send_json(
            {
                "error": str(exc)
            }
        )

    finally:

        await ws.close()

