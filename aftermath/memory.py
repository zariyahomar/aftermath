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
        settings.checkpoints_path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(settings.checkpoints_path), check_same_thread=False)
        _checkpointer = SqliteSaver(_conn)
        if hasattr(_checkpointer, "setup"):
            _checkpointer.setup()
    return _checkpointer


def get_store() -> InMemoryStore:
    global _store
    if _store is None:
        _store = InMemoryStore()
    return _store
