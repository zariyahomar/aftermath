# AfterMath

**A BNPL payment tracker that turns messy payment statements into a clear payoff picture.**

AfterMath is a Production AI Engineering project that helps users understand and manage multiple Buy Now, Pay Later (BNPL) installment plans in one place.

Users can paste or upload messy payment statements, and AfterMath uses an LLM to extract structured installment plans such as merchants, providers, balances, installment amounts, and due dates. The extracted information is stored and can then be used to answer questions, retrieve relevant information from a knowledge base, and simulate a payoff calendar based on the user's available cash.

AfterMath is designed to **organize and explain existing payment commitments**. It does **not** approve credit, recommend taking out new loans, or encourage additional borrowing.

---

## The Problem

BNPL services make it easy to split purchases into installments, but having several plans across different providers can make it difficult to see the full picture.

A user might have:

* several BNPL providers
* different installment amounts
* different payment dates
* different remaining balances
* payment information spread across statements
* multiple plans that overlap in the same month

The information is often presented in statements or messages that are not immediately useful for planning.

For example, a statement might contain information such as:

```text
Klarna
Remaining balance: £240
Next payment: £40
Due: 14 September

Afterpay
Remaining: £180
Payment: £30
Due: 18 September

Affirm
Outstanding: £320
Monthly payment: £80
Next payment: 22 September
```

A user has to manually find this information, understand it, and combine it themselves.

**AfterMath solves this organization problem by turning unstructured payment information into structured data and then using that data to provide a single view of the user's existing obligations.**

---

## What AfterMath Does

AfterMath has four main capabilities:

### 1. Extract payment plans

Users can either:

* paste a statement into the application, or
* upload a supported statement file.

Gemini extracts relevant payment information into structured Pydantic models rather than relying on free-form text.

The extracted information can include:

* merchant
* BNPL provider
* remaining balance
* installment amount
* next due date
* number of installments where available

The application is designed to avoid inventing missing financial information.

---

### 2. Track existing obligations

Extracted plans are persisted in SQLite and displayed in a dashboard.

The dashboard provides an overview of:

* total remaining balance
* number of active plans
* upcoming payment
* payment amount
* provider
* due date

This gives the user a consolidated view of their existing BNPL commitments.

---

### 3. Ask questions using RAG

AfterMath includes a Retrieval-Augmented Generation (RAG) system.

Users can ask questions such as:

> What is BNPL stacking?

or questions about information contained in their uploaded material.

The application retrieves relevant documents from:

* a small built-in knowledge base
* the user's own uploaded documents

The retrieved chunks include metadata such as their source and relevance score, allowing answers to be grounded in identifiable information rather than relying entirely on the model's internal knowledge.

---

### 4. Simulate a payoff calendar

Users can enter their available cash and ask AfterMath to simulate how existing obligations could be paid.

The payoff calculation is handled by Python rather than being left entirely to the LLM.

The system considers existing payment obligations and produces a simulated payment schedule.

This is deliberately presented as a **simulation**, not financial advice.

---

# How It Works

At a high level, the application follows this flow:

```text
                    User
                      |
          +-----------+-----------+
          |                       |
     Paste statement         Upload file
          |                       |
          +-----------+-----------+
                      |
                      v
              Document processing
                      |
                      v
             Gemini extraction
                      |
                      v
             Structured Pydantic data
                      |
          +-----------+-----------+
          |                       |
          v                       v
       SQLite                 Chroma
     obligations          uploaded content
          |                       |
          |                 + knowledge base
          |                       |
          +-----------+-----------+
                      |
                      v
                 AfterMath
                      |
          +-----------+-----------+
          |                       |
          v                       v
     RAG questions          Payoff simulation
          |                       |
          v                       v
   Grounded answer          Python calculation
    + citations             + evaluation
```

---

# Architecture

AfterMath is built as a small production-style AI application rather than a single LLM prompt.

## Frontend

The frontend is a lightweight HTML/CSS/JavaScript interface.

It allows users to:

* enter their user ID
* enter available cash
* paste statements
* upload documents
* extract payment plans
* view stored obligations
* ask questions
* simulate payoff plans
* clear stored user data

The frontend communicates with the FastAPI backend through HTTP requests.

---

## FastAPI backend

FastAPI provides the application API and coordinates the different components.

Important endpoints include:

```text
GET  /
GET  /health

GET  /obligations/{user_id}
POST /profile/{user_id}

POST /run
POST /ingest
POST /ingest/file

DELETE /user/{user_id}/data

WebSocket /ws/run
```

The API separates document ingestion, general requests, stored obligations, and user-data management.

---

## LangGraph

LangGraph controls the application's workflow.

Rather than sending every request directly to an LLM, AfterMath routes different tasks through different parts of the workflow.

The graph handles:

* intent routing
* statement extraction
* persistence
* payoff planning
* evaluation
* RAG-backed questions
* agent/tool interactions

This allows deterministic application logic and model-based reasoning to work together.

---

# AI Workflow

The main AI workflow can be viewed as several stages.

### Statement extraction

```text
Statement
    ↓
Document text
    ↓
Gemini
    ↓
Pydantic structured output
    ↓
Validated obligations
    ↓
SQLite
```

The model is responsible for interpreting messy language.

The application is responsible for validating and storing the resulting structure.

This separation reduces the amount of financial calculation that is delegated to the model.

---

### Question answering

```text
User question
      ↓
Retrieve relevant chunks
      ↓
Knowledge base + user's uploads
      ↓
Relevant context
      ↓
Agent / Gemini
      ↓
Grounded answer
      ↓
Sources / citations
```

Uploaded documents are associated with the relevant user so that one user's uploaded information is not intentionally mixed into another user's retrieval context.

---

### Payoff simulation

```text
Existing obligations
        +
Available cash
        ↓
Python payoff logic
        ↓
Simulated payment calendar
        ↓
LLM explanation / evaluation
```

The important calculations are performed by application code rather than asking the LLM to perform financial arithmetic itself.

This is an example of using the model for reasoning and language while keeping deterministic operations in conventional code.

---

# RAG Architecture

AfterMath uses Chroma as its vector database.

Documents are converted into chunks and embedded before being stored.

The system distinguishes between:

```text
Knowledge documents
        |
        +----> Chroma
        |
User uploads
        |
        +----> Chroma
```

Retrieved results contain:

* source
* relevance score
* preview
* full chunk text

This information is then made available to the answering workflow.

User-uploaded documents are tagged with the associated user ID, allowing retrieval to be scoped to that user.

---

# Memory

AfterMath demonstrates two different concepts of application memory.

### Checkpointer

LangGraph checkpoints conversation state for a thread.

This allows the application to maintain conversational context.

### Persistent application data

SQLite stores application-level information such as:

* obligations
* user profiles
* checkpoints

These are different from vector-store documents.

When user data is cleared, AfterMath can remove the corresponding:

* payment obligations
* profile information
* uploaded document vectors
* conversation thread memory

This separation demonstrates the difference between conversational state and persistent application data.

---

# Tools and Agents

AfterMath uses tools as an interface between the LLM and application data.

For example, the agent can access functionality for retrieving a user's stored obligations or relevant context.

Conceptually:

```text
LLM
 |
 +---- list user obligations
 |
 +---- retrieve relevant context
 |
 +---- other application tools
```

The tools provide controlled access to application functionality instead of giving the model unrestricted access to the database or filesystem.

The project currently uses LangGraph's ReAct-style agent functionality for the question-answering workflow.

---

# Course Map

AfterMath was designed to demonstrate several Production AI Engineering concepts.

| Guide topic                             | Where it lives                                       |
| --------------------------------------- | ---------------------------------------------------- |
| LCEL `prompt \| model \| parser`        | `aftermath/chains.py`                                |
| Structured JSON / Pydantic              | `aftermath/schemas.py`                               |
| Chunking + embeddings                   | `aftermath/embedding.py`, `aftermath/data_loader.py` |
| Vector database                         | `aftermath/vector_store.py`                          |
| Enhanced RAG                            | `aftermath/search.py`                                |
| Tools as "hands"                        | `aftermath/tools.py`                                 |
| Routing / workers / evaluator-optimizer | `aftermath/graph.py`                                 |
| ReAct agent                             | `ask_agent` via `create_react_agent`                 |
| Checkpointer vs Store                   | `aftermath/memory.py`                                |
| FastAPI + WebSocket                     | `aftermath/api.py`                                   |
| LLM configuration                       | `aftermath/config.py`, `aftermath/llm.py`            |
| LangSmith                               | `.env.example` tracing variables                     |

---

# Technology Stack

* **Python**
* **FastAPI**
* **LangChain**
* **LangGraph**
* **Google Gemini**
* **Gemini embeddings**
* **Chroma**
* **SQLite**
* **Pydantic**
* **HTML / CSS / JavaScript**
* **LangSmith** for optional tracing

---

# LLM Configuration

AfterMath uses Google's Gemini models for its AI workflows.

Example configuration:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

Gemini is used for:

* statement extraction
* intent handling
* question answering
* planning
* evaluation
* agent responses

Embeddings are used to represent documents for semantic retrieval.

---

# Setup

### 1. Clone the repository

```powershell
git clone https://github.com/zariyahomar/aftermath.git
cd aftermath
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
pip install PyMuPDF
pip install -U langchain-google-genai
```

### 4. Configure environment variables

Copy the example environment file:

```powershell
copy .env.example .env
```

Add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

If LangSmith tracing is enabled, the relevant tracing variables can also be configured in `.env`.

### 5. Start the application

```powershell
uvicorn aftermath.api:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

# Demo

The simplest way to demonstrate AfterMath is:

### Step 1 — Extract plans

Paste:

```text
sample_data/statement.txt
```

into the statement box and select:

**Extract plans**

AfterMath extracts the payment obligations and displays them in the dashboard.

### Step 2 — Set available cash

Enter an amount of available cash.

### Step 3 — Simulate a payoff

Select:

**Simulate payoff**

AfterMath generates a simulated payoff calendar using the stored obligations and available cash.

### Step 4 — Test RAG

Ask:

> What is BNPL stacking?

The system retrieves relevant information and returns an answer with source information.

---

# Example Use Case

Suppose a user has three active installment plans:

```text
Klarna       £240 remaining    £40/month
Afterpay     £180 remaining    £30/month
Affirm       £320 remaining    £80/month
```

Instead of manually reading three different payment sources, AfterMath consolidates the information:

```text
Total remaining: £740
Active plans: 3
```

The user can then inspect their upcoming obligations, ask questions about BNPL concepts, or run a payoff simulation using a specified amount of available cash.

The goal is not to tell the user what financial decision to make.

The goal is to make the existing information **easier to understand and work with**.

---

# Safety and Design Principles

Financial applications require particular care around hallucination and arithmetic.

AfterMath therefore follows several design principles.

### No new-debt recommendations

The system is explicitly designed not to recommend:

* taking out new BNPL plans
* increasing borrowing
* opening additional credit
* using new debt to pay existing debt

### Deterministic calculations

Where possible, financial calculations are performed in Python rather than generated by the LLM.

This reduces the risk of the model inventing arithmetic.

### Structured extraction

The extraction workflow uses structured Pydantic output instead of relying solely on free-form model responses.

### Grounded answers

RAG answers are based on retrieved documents and expose source information where available.

### No invented facts

The extraction workflow is instructed not to manufacture financial information that is absent from the source statement.

### Simulation, not financial advice

Payoff schedules are simulations based on the information provided by the user.

They are not presented as personalized financial advice or recommendations.

---

# Data and Privacy

AfterMath stores application data locally when running the project.

The application can store:

* user profiles
* payment obligations
* conversation checkpoints
* uploaded document chunks in Chroma

The application includes a mechanism for clearing a user's stored data.

Clearing user data removes the relevant stored payment information, profile information, uploaded document vectors, and conversation memory associated with that user/thread.

API keys should be stored in `.env` and **must not be committed to Git**.

The `.env` file should remain excluded through `.gitignore`.

---

# Project Structure

A simplified view of the repository:

```text
aftermath/
│
├── aftermath/
│   ├── api.py
│   ├── chains.py
│   ├── config.py
│   ├── data_loader.py
│   ├── embedding.py
│   ├── graph.py
│   ├── llm.py
│   ├── memory.py
│   ├── repository.py
│   ├── schemas.py
│   ├── search.py
│   ├── tools.py
│   └── vector_store.py
│
├── data/
│
├── knowledge/
│
├── sample_data/
│   └── statement.txt
│
├── static/
│   └── index.html
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

# Why This Is a Production AI Engineering Project

AfterMath is intentionally more than a chatbot.

The project combines:

* **LLM-based extraction** for unstructured documents
* **structured outputs** for reliable application data
* **RAG** for grounded question answering
* **vector search** for semantic retrieval
* **tool calling** for controlled access to application data
* **LangGraph** for multi-step workflows
* **persistent state** for conversations and application data
* **deterministic Python logic** for financial calculations
* **evaluation** of generated payoff plans
* **FastAPI** for serving the application
* **WebSockets** for streaming workflow execution
* **user-scoped retrieval** for uploaded documents
* **data deletion** across multiple persistence layers

The central design principle is:

> **Use the LLM where language understanding and reasoning are useful, and use conventional software where determinism and reliability matter.**

This separation is particularly important for a financial-information application.

---

# Limitations

AfterMath is a course project and should not be treated as a production financial service.

Current limitations include:

* statement formats can vary significantly
* extraction quality depends on the source document
* unsupported document formats may not be processed correctly
* missing information cannot always be recovered
* RAG retrieval can return incomplete or irrelevant context
* payoff simulations depend on the accuracy of the extracted obligations
* the application does not connect directly to users' financial accounts
* the application does not make payments
* the application does not provide regulated financial advice

Users should verify extracted payment information against their original statements.

---

# Future Improvements

Potential extensions include:

* additional document formats
* improved statement parsing
* stronger extraction validation
* recurring payment detection
* automatic detection of duplicate obligations
* richer payment-calendar visualizations
* improved evaluation and testing
* automated test datasets for extraction accuracy
* authentication and multi-user deployment
* production database infrastructure
* more granular document permissions
* improved observability and LangSmith tracing
* automated regression tests for RAG retrieval
* support for additional currencies and date formats

---
# AI Usage

AI tools were used as part of the development process for AfterMath.

AI assistance was used for:

* **README development** — helping structure, expand, and refine the project documentation.
* **Sample data** — generating and refining example BNPL statements used for testing the extraction workflow.
* **Prompt development** — helping draft, test, and refine prompts for extraction, question answering, planning, evaluation, and safety behaviour.
* **Debugging assistance** — helping interpret errors, identify potential causes, and suggest implementation fixes during development.
* **Code development support** — providing suggestions and explanations for parts of the LangChain, LangGraph, FastAPI, RAG, and frontend implementation.

The final application, architecture, integration of components, testing, and implementation decisions were developed and reviewed as part of the project.

AI-generated suggestions were treated as development assistance and were tested or adapted before being incorporated into the project.

# Project Objective

The objective of AfterMath is to demonstrate how modern AI engineering techniques can be combined with conventional software engineering to build a useful, grounded application around a real-world problem.

Rather than treating an LLM as the entire application, AfterMath uses the model as one component within a larger system:

```text
             Unstructured information
                       ↓
                  LLM extraction
                       ↓
              Structured application data
                       ↓
          +------------+------------+
          |                         |
          ↓                         ↓
     Persistent data          Vector retrieval
          |                         |
          +------------+------------+
                       ↓
                LangGraph workflow
                       ↓
          +------------+------------+
          |                         |
          ↓                         ↓
      RAG answers             Payoff simulation
          |                         |
          ↓                         ↓
      Citations              Deterministic logic
```

**AfterMath's goal is to make complicated existing payment information easier to understand without turning the system into a source of new financial recommendations.**
