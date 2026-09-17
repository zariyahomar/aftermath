from __future__ import annotations

import sqlite3
import uuid

from aftermath.config import settings
from aftermath.schemas import Obligation


def _connect() -> sqlite3.Connection:
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row

    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS obligations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                merchant TEXT NOT NULL,
                provider TEXT NOT NULL,
                original_total REAL,
                installment_amount REAL NOT NULL,
                remaining_balance REAL NOT NULL,
                remaining_installments INTEGER,
                next_due_date TEXT NOT NULL,
                late_fee REAL,
                currency TEXT NOT NULL DEFAULT 'USD',
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT PRIMARY KEY,
                payday_day INTEGER,
                available_cash REAL,
                currency TEXT DEFAULT 'USD'
            );
            """
        )


def upsert_profile(
    user_id: str,
    *,
    payday_day: int | None = None,
    available_cash: float | None = None,
    currency: str | None = None,
) -> dict:
    current = get_profile(user_id)

    payday = (
        payday_day
        if payday_day is not None
        else current.get("payday_day")
    )

    cash = (
        available_cash
        if available_cash is not None
        else current.get("available_cash")
    )

    cur = currency or current.get("currency") or "USD"

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO profiles (
                user_id,
                payday_day,
                available_cash,
                currency
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                payday_day = excluded.payday_day,
                available_cash = excluded.available_cash,
                currency = excluded.currency
            """,
            (
                user_id,
                payday,
                cash,
                cur,
            ),
        )

    return get_profile(user_id)


def get_profile(user_id: str) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM profiles WHERE user_id=?",
            (user_id,),
        ).fetchone()

    if not row:
        return {
            "user_id": user_id,
            "payday_day": None,
            "available_cash": None,
            "currency": "USD",
        }

    return dict(row)


def save_obligations(
    user_id: str,
    items: list[Obligation],
) -> list[dict]:
    saved: list[dict] = []

    with _connect() as conn:
        for item in items:
            oid = item.id or str(uuid.uuid4())

            conn.execute(
                """
                INSERT INTO obligations (
                    id,
                    user_id,
                    merchant,
                    provider,
                    original_total,
                    installment_amount,
                    remaining_balance,
                    remaining_installments,
                    next_due_date,
                    late_fee,
                    currency,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    oid,
                    user_id,
                    item.merchant,
                    item.provider,
                    item.original_total,
                    item.installment_amount,
                    item.remaining_balance,
                    item.remaining_installments,
                    item.next_due_date.isoformat(),
                    item.late_fee,
                    item.currency,
                    item.notes,
                ),
            )

            saved.append(
                {
                    **item.model_dump(),
                    "id": oid,
                    "next_due_date": item.next_due_date.isoformat(),
                }
            )

    return saved


def list_obligations(user_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM obligations
            WHERE user_id=?
            ORDER BY next_due_date
            """,
            (user_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def clear_obligations(user_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM obligations WHERE user_id=?",
            (user_id,),
        )


def clear_profile(user_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM profiles WHERE user_id=?",
            (user_id,),
        )