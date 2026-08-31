# AfterMath

BNPL stacking tracker for the Production AI Engineering course. AfterMath extracts installment plans from messy statements, grounds answers in a small knowledge base plus your uploads, and simulates a payoff calendar. It does **not** approve credit or recommend new borrowing.

## Setup

```powershell
cd C:\Users\zariy\Projects\aftermath
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Put your OpenAI-compatible key in .env
uvicorn aftermath.api:app --reload
```

Open http://127.0.0.1:8000

Demo path: paste `sample_data/statement.txt` → **Extract plans** → set cash → **Simulate payoff**. Then ask “What is BNPL stacking?” to see RAG citations.

Groq/OpenRouter: set `OPENAI_BASE_URL` and `OPENAI_MODEL` in `.env`.

## Course map

| Guide topic | Where it lives |
|---|---|
| LCEL `prompt \| model \| parser` | `aftermath/chains.py` |
| Structured JSON / Pydantic | `aftermath/schemas.py` |
| Chunking + embeddings | `aftermath/embedding.py`, `data_loader.py` |
| Vector DB (Chroma) | `aftermath/vector_store.py` |
| Enhanced RAG (source, score, preview) | `aftermath/search.py` |
| Tools as “hands” | `aftermath/tools.py` (deterministic math) |
| Routing / workers / evaluator-optimizer | `aftermath/graph.py` |
| ReAct agent | `ask_agent` via `create_react_agent` |
| Checkpointer vs Store | `aftermath/memory.py` (SQLite + InMemoryStore) |
| FastAPI + WebSocket | `aftermath/api.py` |
| LangSmith | `.env.example` tracing vars |

## Safety

System prompts refuse new-debt advice. Calculators live in Python so the model cannot invent installment math.
