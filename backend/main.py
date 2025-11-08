# backend/main.py
"""
FastAPI migration of your Flask app.
Run with: uvicorn main:app --reload --port 5000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
from dotenv import load_dotenv
import os
import traceback
import uuid
import json
import asyncio
from datetime import datetime

# Blocking/sync helpers (we'll call these with asyncio.to_thread)
from sentence_transformers import SentenceTransformer
from arithmetic_helper import try_compute_arithmetic
from linear_equation_solver import try_solve_linear
from derivative_helper import try_derivative_lookup

# guardrails and web search
from guardrails_helper import is_math_question, contains_prompt_injection
from web_search_helper import search_web

# Qdrant utils (keep your existing db_utils.py)
from db_utils import ensure_collection, upsert_points, search_vectors, get_qdrant_client

# Groq/OpenAI client (if using)
from openai import OpenAI

# local feedback DB helper (we add this file)
from feedback_db import save_feedback, get_all_feedback

# load env
load_dotenv()

# FastAPI app init
app = FastAPI(title="Math Routing Agent (FastAPI)")

# allow CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq/OpenAI config (optional)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", None)
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
if GROQ_API_KEY:
    groq_client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_API_BASE)
else:
    groq_client = None

# Load embedding model once (sentence-transformers)
# This is blocking — we'll call encode via asyncio.to_thread
model = SentenceTransformer("all-MiniLM-L6-v2")
COLLECTION = os.getenv("QDRANT_COLLECTION", "math_kb")


# ---------- Pydantic models ----------
class AskIn(BaseModel):
    question: str


class FeedbackIn(BaseModel):
    question: str
    answer: Any
    helpful: bool
    corrected_answer: Optional[str] = ""
    comment: Optional[str] = ""


class TrainIn(BaseModel):
    question: str
    corrected_answer: str
    comment: Optional[str] = ""


# ---------- Utility: call Groq in thread ----------
def call_grok_fallback_sync(question: str,
                            context_snippets: Optional[List[str]] = None,
                            model_name: str = "openai/gpt-oss-20b",
                            max_tokens: int = 700,
                            temperature: float = 0.05,
                            debug_log_raw: bool = False) -> str:
    """
    Synchronous function that calls groq_client (OpenAI compatible).
    We will call this with asyncio.to_thread(...) from async endpoints.
    """
    if groq_client is None:
        raise RuntimeError("GROQ_API_KEY not configured")

    messages = [
        {"role": "system", "content":
         ("You are a precise math tutor. Answer exactly as numbered steps only. "
          "Do NOT include titles/headings/extra commentary. Example:\n"
          "1. Step one\n2. Step two\n3. Final answer: x = 2\nReturn only the steps and final answer.") }
    ]
    if context_snippets:
        ctx_text = "Related snippets for context (do not repeat verbatim):\n" + "\n\n".join(context_snippets)
        messages.append({"role": "user", "content": ctx_text})

    messages.append({"role": "user", "content": f"Solve or explain: {question}"})

    resp = groq_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        n=1,
    )

    # defensive extraction
    try:
        text = resp.choices[0].message.content
    except Exception:
        text = str(resp)

    text = text.strip()
    if text.startswith("**") and text.endswith("**"):
        text = text.strip("*").strip()
    return text


# ---------- Basic endpoints ----------
@app.get("/")
async def root():
    return {"message": "Math Routing Agent (FastAPI) running"}


@app.get("/api/debug")
async def debug():
    """
    Check Qdrant connection and list collections.
    """
    try:
        client = get_qdrant_client()
        info = client.get_collections()
        coll_names = [c.name for c in getattr(info, "collections", [])]
        return {"ok": True, "collections": coll_names}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/setup_collection")
async def setup_collection():
    try:
        # ensure_collection is synchronous — run in thread
        await asyncio.to_thread(ensure_collection, COLLECTION, False)
        return {"status": "ok"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest")
async def ingest():
    """
    Ingest sample data (sync operations run in thread).
    """
    samples = [
        {"question": "What is 2 + 2?", "answer": "2 + 2 = 4"},
        {"question": "Solve 2x + 5 = 15", "answer": "x = 5"},
        {"question": "What is the square root of 16?", "answer": "√16 = 4"},
    ]
    points = []
    try:
        # prepare vectors in thread (model.encode is blocking)
        for i, item in enumerate(samples):
            vec = await asyncio.to_thread(model.encode, item["question"])
            points.append({
                "id": i + 1,
                "vector": vec.tolist() if hasattr(vec, "tolist") else list(vec),
                "payload": {"question": item["question"], "answer": item["answer"]}
            })
        # upsert (blocking) in thread
        await asyncio.to_thread(upsert_points, COLLECTION, points)
        return {"status": "ok", "ingested": len(points)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Core ask endpoint ----------
@app.post("/api/ask")
async def ask(payload: AskIn):
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Empty question")

    # Guardrails early
    try:
        if contains_prompt_injection(question):
            return {"source": "guardrail", "text": "Sorry, request looks unsafe or tries to modify system behavior."}
        if not is_math_question(question):
            return {"source": "guardrail", "text": "I can only help with math questions. Please ask a math question."}
    except Exception:
        # if guardrails helper errors, continue but log
        traceback.print_exc()

    question_lower = question.lower()

    # 1) Fast path: arithmetic
    try:
        arithmetic_answer = await asyncio.to_thread(try_compute_arithmetic, question)
    except Exception:
        arithmetic_answer = None
    if arithmetic_answer is not None:
        return {"source": "computed", "text": arithmetic_answer}

    # 2) Linear solver decision
    try:
        non_linear_pattern = __import__("re").compile(r'(\bx\s*\^|\b\d+\s*\^|[²³]|\bx\d)', flags=__import__("re").IGNORECASE)
        if non_linear_pattern.search(question_lower):
            linear_answer = None
        else:
            linear_answer = await asyncio.to_thread(try_solve_linear, question)
    except Exception:
        linear_answer = None

    if linear_answer is not None:
        return {"source": "solver", "text": linear_answer}

    # 3) derivative lookup
    try:
        deriv_answer = await asyncio.to_thread(try_derivative_lookup, question)
    except Exception:
        deriv_answer = None
    if deriv_answer is not None:
        return {"source": "lookup", "text": deriv_answer}

    # 4) KB lookup via embeddings -> qdrant
    try:
        qvec = await asyncio.to_thread(model.encode, question)
        qvec_list = qvec.tolist() if hasattr(qvec, "tolist") else list(qvec)
        results = await asyncio.to_thread(search_vectors, COLLECTION, qvec_list, 5)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Vector/KB error: {e}")

    # If confident KB hit, return
    try:
        if results and results[0].get("score") and results[0]["score"] > 0.85:
            best = results[0]
            return {"source": "kb", "text": best["payload"].get("answer", "")}
    except Exception:
        pass

    # 5) Web search via Tavily (MCP) - only if KB is low-confidence
    context_snippets = []
    try:
        tavily_resp = await asyncio.to_thread(search_web, question, "basic", 3)
        if tavily_resp.get("ok"):
            web_hits = tavily_resp.get("results", [])[:3]
            for h in web_hits:
                title = (h.get("title") or "").strip()
                url = (h.get("url") or "").strip()
                snippet = (h.get("snippet") or "").strip()
                snippet_short = snippet[:300].rsplit(" ", 1)[0] + "..." if len(snippet) > 300 else snippet
                context_snippets.append(f"Source: {title} ({url})\nSnippet: {snippet_short}")
    except Exception:
        # ignore web search failure, proceed to LLM fallback
        traceback.print_exc()

    # include light KB hits (short) to help LLM
    for hit in (results or [])[:3]:
        try:
            q = (hit.get("payload", {}).get("question", "") or "")[:200]
            a = (hit.get("payload", {}).get("answer", "") or "")[:400]
            score = hit.get("score")
            context_snippets.append(f"KB match (score={score}): Q: {q} — A: {a}")
        except Exception:
            continue

    if context_snippets:
        print("[app.ask] Context snippets:", [s[:200].replace("\n", " / ") for s in context_snippets])
    else:
        print("[app.ask] No context snippets — calling LLM without web/KB context")

    # 6) Groq LLM fallback (sync call run in thread)
    if groq_client:
        chosen_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        try:
            grok_text = await asyncio.to_thread(call_grok_fallback_sync,
                                               question,
                                               context_snippets,
                                               chosen_model,
                                               700,
                                               0.05,
                                               True)
            print("[app.ask] Groq returned:", grok_text[:300].replace("\n", " / "))
            return {"source": "grok", "text": grok_text}
        except Exception as e:
            traceback.print_exc()
            return {"source": "fallback", "text": f"LLM error: {e}"}

    # 7) final safe fallback
    return {"source": "fallback", "text": "I couldn't find this in my KB and no LLM is configured."}


# ---------- Feedback endpoints ----------
@app.post("/api/feedback")
async def feedback(payload: FeedbackIn):
    """
    Save simple thumbs up/down feedback (non-blocking).
    """
    if not payload.question or payload.helpful is None:
        raise HTTPException(status_code=400, detail="Missing fields")

    try:
        # save_feedback is synchronous — run in thread
        fb_id = await asyncio.to_thread(save_feedback,
                                        question=payload.question,
                                        answer=json.dumps(payload.answer, ensure_ascii=False),
                                        helpful=payload.helpful,
                                        corrected_answer=payload.corrected_answer or "",
                                        comment=payload.comment or "")
        return {"ok": True, "id": fb_id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/feedback/all")
async def feedback_all():
    try:
        data = await asyncio.to_thread(get_all_feedback)
        return {"ok": True, "feedback": data}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/feedback/train")
async def feedback_train(payload: TrainIn):
    """
    Human-in-the-loop: accepts corrected answer, saves to SQLite, and upserts corrected Q/A into Qdrant.
    """
    if not payload.question or not payload.corrected_answer:
        raise HTTPException(status_code=400, detail="Missing fields")

    # 1) Save feedback (non-blocking)
    try:
        fb_id = await asyncio.to_thread(save_feedback,
                                        question=payload.question,
                                        answer="",
                                        helpful=False,
                                        corrected_answer=payload.corrected_answer,
                                        comment=payload.comment or "")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"SQLite save failed: {e}")

    # 2) Create embedding
    try:
        vec = await asyncio.to_thread(model.encode, payload.question)
        vec_list = vec.tolist() if hasattr(vec, "tolist") else list(vec)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    # 3) Upsert into Qdrant with UUID string id
    new_point = {
        "id": str(uuid.uuid4()),
        "vector": vec_list,
        "payload": {
            "question": payload.question,
            "answer": payload.corrected_answer,
            "source": "human_feedback",
            "feedback_id": fb_id,
            "comment": payload.comment or ""
        }
    }
    try:
        await asyncio.to_thread(upsert_points, COLLECTION, [new_point])
        return {"ok": True, "trained": True, "feedback_id": fb_id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Qdrant upsert failed: {e}")


# run by uvicorn; do not call app.run() here
