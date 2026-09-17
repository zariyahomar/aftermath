from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.store.memory import InMemoryStore

from aftermath.config import settings


_checkpointer: SqliteSaver | None = None
_store: InMemoryStore | None = None
_conn: sqlite3.Connection | None = None


def get_checkpointer() -> SqliteSaver:
    global _checkpointer, _conn

    if _checkpointer is None:
        settings.checkpoints_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        _conn = sqlite3.connect(
            str(settings.checkpoints_path),
            check_same_thread=False,
        )

        _checkpointer = SqliteSaver(_conn)

        if hasattr(_checkpointer, "setup"):
            _checkpointer.setup()

    return _checkpointer


def clear_thread(thread_id: str) -> None:
    """
    Remove a LangGraph checkpoint thread if the installed
    LangGraph version supports thread deletion.
    """

    checkpointer = get_checkpointer()

    delete_thread = getattr(
        checkpointer,
        "delete_thread",
        None,
    )

    if delete_thread is not None:
        delete_thread(thread_id)


def get_store() -> InMemoryStore:
    global _store

    if _store is None:
        _store = InMemoryStore()

    return _store