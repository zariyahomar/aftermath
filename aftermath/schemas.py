from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Provider = Literal[
    "klarna",
    "afterpay",
    "affirm",
    "paypal",
    "zip",
    "sezzle",
    "store_card",
    "other",
]


class Obligation(BaseModel):
    id: str | None = None
    merchant: str
    provider: Provider = "other"
    original_total: float | None = None
    installment_amount: float
    remaining_balance: float
    remaining_installments: int | None = None
    next_due_date: date
    late_fee: float | None = None
    currency: str = "USD"
    notes: str | None = None


class ExtractedObligations(BaseModel):
    obligations: list[Obligation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RetrievedChunk(BaseModel):
    source: str
    score: float
    preview: str
    text: str


class PlanStep(BaseModel):
    account_id: str
    merchant: str
    action: str
    amount: float
    when: str


class PayoffPlan(BaseModel):
    summary: str
    total_due_7d: float
    total_due_30d: float
    available_cash: float
    feasible: bool
    steps: list[PlanStep] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class PlanEvaluation(BaseModel):
    accepted: bool
    score: float = Field(ge=0, le=1)
    feedback: str


class AccountAnalysis(BaseModel):
    account_id: str
    merchant: str
    provider: str
    next_due_date: date
    remaining_balance: float
    installment_amount: float
    due_in_7d: bool
    due_in_30d: bool
    pressure: Literal["low", "medium", "high"]


class IngestRequest(BaseModel):
    user_id: str = "demo"
    text: str | None = None


class RunRequest(BaseModel):
    user_id: str = "demo"
    thread_id: str
    message: str
    available_cash: float | None = None
    intent: Literal["auto", "ingest", "ask", "plan"] = "auto"


class RouterOutput(BaseModel):
    intent: Literal["ingest", "ask", "plan"]
    reason: str = ""


class ProfileUpdate(BaseModel):
    payday_day: int | None = Field(default=None, ge=1, le=28)
    available_cash: float | None = None
    currency: str | None = None
