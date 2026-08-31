from __future__ import annotations

import json
from datetime import date
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.types import Send

from aftermath.chains import (
    build_evaluator_chain,
    build_extract_chain,
    build_planner_chain,
    build_router_chain,
)
from aftermath.embedding import documents_from_texts
from aftermath.memory import get_checkpointer, get_store
from aftermath.prompts import SYSTEM_AGENT
from aftermath.repository import get_profile, list_obligations, save_obligations
from aftermath.schemas import AccountAnalysis, Obligation
from aftermath.search import retrieve
from aftermath.tools import compute_payoff, dues_in_window, stacking_risk
from aftermath.llm import get_llm
from aftermath.vector_store import index_documents


def _merge_analyses(left: list | None, right: list | None) -> list:
    if right and len(right) == 1 and isinstance(right[0], dict) and right[0].get("__reset__"):
        return []
    return list(left or []) + list(right or [])


class GraphState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    intent: Literal["ingest", "ask", "plan"]
    raw_text: str
    available_cash: float
    accounts: list[dict]
    extracted: list[dict]
    warnings: list[str]
    retrieved: list[dict]
    analyses: Annotated[list[dict], _merge_analyses]
    account: dict
    plan: dict
    evaluation: dict
    loop_count: int
    answer: str
    citations: list[dict]


def _make_tools(user_id: str):
    @tool
    def list_user_obligations() -> str:
        """List stored BNPL obligations for this user as JSON."""
        return json.dumps(list_obligations(user_id), default=str)

    @tool
    def retrieve_context(query: str) -> str:
        """Retrieve knowledge-base or uploaded document chunks with source, score, and preview."""
        chunks = retrieve(query)
        return json.dumps([c.model_dump() for c in chunks])

    @tool
    def tool_stacking_risk(window_dues: float, available_cash: float) -> str:
        """Deterministic stacking risk. Pass 7-day or 30-day dues vs cash. Do not do this math yourself."""
        return json.dumps(stacking_risk(window_dues, available_cash))

    @tool
    def tool_compute_payoff(
        remaining_balance: float,
        installment: float,
        extra_per_period: float = 0.0,
    ) -> str:
        """Deterministic payoff simulation for one account."""
        return json.dumps(compute_payoff(remaining_balance, installment, extra_per_period))

    return [
        list_user_obligations,
        retrieve_context,
        tool_stacking_risk,
        tool_compute_payoff,
    ]


def hydrate(state: GraphState) -> dict:
    user_id = state.get("user_id") or "demo"
    accounts = list_obligations(user_id)
    profile = get_profile(user_id)
    cash = state.get("available_cash")
    if cash is None:
        cash = profile.get("available_cash") or 0.0
    store = get_store()
    store.put(("users", user_id), "profile", profile)
    store.put(("users", user_id), "accounts", accounts)
    return {
        "user_id": user_id,
        "accounts": accounts,
        "available_cash": float(cash),
        "analyses": [{"__reset__": True}],
        "loop_count": state.get("loop_count") or 0,
        "warnings": [],
        "citations": [],
    }


def route(state: GraphState) -> dict:
    if state.get("intent") in {"ingest", "ask", "plan"}:
        return {}
    last = ""
    for msg in reversed(state.get("messages") or []):
        content = getattr(msg, "content", "")
        if content:
            last = content
            break
    if state.get("raw_text") and not last:
        return {"intent": "ingest"}
    routed = build_router_chain().invoke({"message": last or state.get("raw_text") or ""})
    return {"intent": routed.intent}


def after_route(state: GraphState) -> str:
    return state.get("intent") or "ask"


def ingest_extract(state: GraphState) -> dict:
    document = state.get("raw_text") or ""
    if not document:
        for msg in reversed(state.get("messages") or []):
            if getattr(msg, "content", None):
                document = msg.content
                break
    result = build_extract_chain().invoke({"document": document})
    payload = result.model_dump()
    for item in payload["obligations"]:
        if isinstance(item.get("next_due_date"), date):
            item["next_due_date"] = item["next_due_date"].isoformat()
    return {
        "extracted": payload["obligations"],
        "warnings": payload["warnings"],
        "raw_text": document,
    }


def ingest_persist(state: GraphState) -> dict:
    user_id = state["user_id"]
    models = [Obligation(**row) for row in state.get("extracted") or []]
    saved = save_obligations(user_id, models) if models else []
    if state.get("raw_text"):
        docs = documents_from_texts(
            [(f"upload-{user_id}.txt", state["raw_text"])],
            kind="user_upload",
        )
        index_documents(docs)
    n = len(saved)
    answer = f"Saved {n} obligation(s)."
    if state.get("warnings"):
        answer += " Warnings: " + "; ".join(state["warnings"])
    if n == 0:
        answer = "No BNPL obligations found in that text."
    return {
        "accounts": list_obligations(user_id),
        "extracted": saved,
        "answer": answer,
        "messages": [SystemMessage(content=answer)],
    }


def ask_agent(state: GraphState) -> dict:
    user_id = state["user_id"]
    tools = _make_tools(user_id)
    agent = create_react_agent(get_llm(temperature=0.2), tools)
    query = ""
    for msg in reversed(state.get("messages") or []):
        if getattr(msg, "content", None):
            query = msg.content
            break
    chunks = retrieve(query) if query else []
    result = agent.invoke(
        {
            "messages": [SystemMessage(content=SYSTEM_AGENT)]
            + list(state.get("messages") or [])
        }
    )
    final = result["messages"][-1].content
    return {
        "messages": result["messages"],
        "answer": final,
        "retrieved": [c.model_dump() for c in chunks],
        "citations": [c.model_dump() for c in chunks],
    }


def analyze_account(state: GraphState) -> dict:
    acc = state["account"]
    due = date.fromisoformat(str(acc["next_due_date"]))
    in7 = dues_in_window(due, days=7)
    in30 = dues_in_window(due, days=30)
    remaining = float(acc["remaining_balance"])
    installment = float(acc["installment_amount"])
    if in7 and remaining >= installment:
        pressure = "high"
    elif in30:
        pressure = "medium"
    else:
        pressure = "low"
    analysis = AccountAnalysis(
        account_id=str(acc["id"]),
        merchant=acc["merchant"],
        provider=acc["provider"],
        next_due_date=due,
        remaining_balance=remaining,
        installment_amount=installment,
        due_in_7d=in7,
        due_in_30d=in30,
        pressure=pressure,
    )
    payload = analysis.model_dump()
    payload["next_due_date"] = due.isoformat()
    return {"analyses": [payload]}


def prep_plan(state: GraphState) -> dict:
    return {"analyses": [{"__reset__": True}]}


def fanout_accounts(state: GraphState):
    accounts = state.get("accounts") or []
    if not accounts:
        return "synthesize_plan"
    return [Send("analyze_account", {"account": acc}) for acc in accounts]


def synthesize_plan(state: GraphState) -> dict:
    analyses = state.get("analyses") or []
    cash = float(state.get("available_cash") or 0)
    due7 = sum(a["installment_amount"] for a in analyses if a.get("due_in_7d"))
    risk = stacking_risk(due7, cash)
    feedback = ""
    if state.get("evaluation"):
        feedback = state["evaluation"].get("feedback") or ""
    plan = build_planner_chain().invoke(
        {
            "available_cash": cash,
            "analyses": json.dumps(analyses, default=str),
            "risk": json.dumps(risk),
            "feedback": feedback,
        }
    )
    return {"plan": plan.model_dump(), "loop_count": int(state.get("loop_count") or 0) + 1}


def evaluate_plan(state: GraphState) -> dict:
    evaluation = build_evaluator_chain().invoke(
        {
            "available_cash": state.get("available_cash") or 0,
            "analyses": json.dumps(state.get("analyses") or [], default=str),
            "plan": json.dumps(state.get("plan") or {}, default=str),
        }
    )
    return {"evaluation": evaluation.model_dump()}


def after_eval(state: GraphState) -> str:
    ev = state.get("evaluation") or {}
    if ev.get("accepted"):
        return "finalize"
    if int(state.get("loop_count") or 0) >= 3:
        return "finalize"
    return "synthesize_plan"


def finalize(state: GraphState) -> dict:
    if state.get("intent") == "plan" and state.get("plan"):
        plan = state["plan"]
        ev = state.get("evaluation") or {}
        answer = plan.get("summary", "")
        if not ev.get("accepted"):
            answer += " (evaluator still has reservations: " + ev.get("feedback", "") + ")"
        return {"answer": answer, "messages": [SystemMessage(content=answer)]}
    return {}


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("hydrate", hydrate)
    graph.add_node("route", route)
    graph.add_node("ingest_extract", ingest_extract)
    graph.add_node("ingest_persist", ingest_persist)
    graph.add_node("ask_agent", ask_agent)
    graph.add_node("prep_plan", prep_plan)
    graph.add_node("analyze_account", analyze_account)
    graph.add_node("synthesize_plan", synthesize_plan)
    graph.add_node("evaluate_plan", evaluate_plan)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "hydrate")
    graph.add_edge("hydrate", "route")
    graph.add_conditional_edges(
        "route",
        after_route,
        {
            "ingest": "ingest_extract",
            "ask": "ask_agent",
            "plan": "prep_plan",
        },
    )
    graph.add_edge("ingest_extract", "ingest_persist")
    graph.add_edge("ingest_persist", END)
    graph.add_edge("ask_agent", END)
    graph.add_conditional_edges("prep_plan", fanout_accounts, ["analyze_account", "synthesize_plan"])
    graph.add_edge("analyze_account", "synthesize_plan")
    graph.add_edge("synthesize_plan", "evaluate_plan")
    graph.add_conditional_edges(
        "evaluate_plan",
        after_eval,
        {"synthesize_plan": "synthesize_plan", "finalize": "finalize"},
    )
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=get_checkpointer(), store=get_store())


_compiled = None


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
