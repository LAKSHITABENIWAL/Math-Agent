from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import traceback
import uuid
import os
import re
from sentence_transformers import SentenceTransformer
from arithmetic_helper import try_compute_arithmetic
from linear_equation_solver import try_solve_linear
from derivative_helper import try_derivative_lookup
from openai import OpenAI
from guardrails_helper import is_math_question, contains_prompt_injection
from web_search_helper import search_web
from feedback_db import save_feedback, get_all_feedback
from db_utils import ensure_collection, upsert_points, search_vectors, get_qdrant_client

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Math Routing Agent")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Environment setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY", None)
GROQ_API_BASE = "https://api.groq.com/openai/v1"
groq_client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_API_BASE) if GROQ_API_KEY else None

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")
COLLECTION = "math_kb"


# ---------------------------------------------------------------------
# Helper: call Groq
# ---------------------------------------------------------------------
def call_grok_fallback(question: str, context_snippets=None,
                       model_name="openai/gpt-oss-20b", max_tokens=700, temperature=0.05):
    if groq_client is None:
        raise RuntimeError("GROQ_API_KEY not configured")

    messages = [
        {"role": "system", "content":
         ("You are a precise math tutor. Reply only as numbered steps. "
          "No titles or markdown. Example:\n1. Step 1\n2. Step 2\n3. Final answer: x = 2")}
    ]
    if context_snippets:
        ctx = "Related context (don’t repeat verbatim):\n" + "\n\n".join(context_snippets)
        messages.append({"role": "user", "content": ctx})
    messages.append({"role": "user", "content": f"Solve or explain: {question}"})

    resp = groq_client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )

    text = resp.choices[0].message.content.strip()
    return text.strip("*")


# ---------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------
class IngestResponse(BaseModel):
    status: str
    error: Optional[str] = None
    ingested: Optional[int] = None

class DebugResponse(BaseModel):
    ok: bool
    collections: Optional[List[str]] = None
    error: Optional[str] = None

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    source: str
    text: str
    error: Optional[str] = None

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    helpful: bool
    corrected_answer: Optional[str] = None
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    ok: bool
    id: Optional[int] = None
    error: Optional[str] = None
    feedback: Optional[List[Dict[str, Any]]] = None

class TrainRequest(BaseModel):
    question: str
    corrected_answer: str
    comment: Optional[str] = None

# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.get("/")
async def home():
    return {"message": "Math Routing Agent Backend is running"}

@app.get("/api/debug", response_model=DebugResponse)
async def debug():
    try:
        client = get_qdrant_client()
        info = client.get_collections()
        coll_names = [c.name for c in getattr(info, "collections", [])]
        return DebugResponse(ok=True, collections=coll_names)
    except Exception as e:
        traceback.print_exc()
        return DebugResponse(ok=False, error=str(e))

@app.post("/api/setup_collection", response_model=IngestResponse)
async def setup_collection():
    try:
        ensure_collection(collection_name=COLLECTION, recreate=False)
        return IngestResponse(status="ok")
    except Exception as e:
        return IngestResponse(status="error", error=str(e))

@app.post("/api/ingest", response_model=IngestResponse)
async def ingest():
    samples = [
        {"question": "What is 2 + 2?", "answer": "2 + 2 = 4"},
        {"question": "Solve 2x + 5 = 15", "answer": "x = 5"},
        {"question": "What is the square root of 16?", "answer": "√16 = 4"},
    ]

    points = []
    for i, item in enumerate(samples):
        vector = model.encode(item["question"]).tolist()
        points.append({
            "id": i + 1,
            "vector": vector,
            "payload": {
                "question": item["question"],
                "answer": item["answer"],
                "source": "seed"
            }
        })
    try:
        upsert_points(collection_name=COLLECTION, points=points)
        return IngestResponse(status="ok", ingested=len(points))
    except Exception as e:
        return IngestResponse(status="error", error=str(e))


# ---------------------------------------------------------------------
# Main ASK endpoint with feedback-learning boost
# ---------------------------------------------------------------------
@app.post("/api/ask", response_model=AnswerResponse)
async def ask(question_req: QuestionRequest):
    question = question_req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Empty question")

    # Guardrails
    if contains_prompt_injection(question):
        raise HTTPException(status_code=400, detail="Unsafe input blocked")
    if not is_math_question(question):
        return AnswerResponse(source="guardrail", text="I only handle math questions.")

    q_lower = question.lower()

    # Arithmetic fast path
    try:
        ar = try_compute_arithmetic(question)
        if ar is not None:
            return AnswerResponse(source="computed", text=ar)
    except Exception:
        pass

    # Linear solver
    non_linear = re.compile(r'(\bx\s*\^|\b\d+\s*\^|[²³]|\bx\d)', re.I)
    if not non_linear.search(q_lower):
        try:
            sol = try_solve_linear(question)
            if sol is not None:
                return AnswerResponse(source="solver", text=sol)
        except Exception:
            pass

    # Derivative lookup
    try:
        d = try_derivative_lookup(question)
        if d:
            return AnswerResponse(source="lookup", text=d)
    except Exception:
        pass

    # KB Search
    try:
        qv = model.encode(question).tolist()
        hits = search_vectors(collection_name=COLLECTION, query_vector=qv, top=10)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"KB error: {str(e)}")

    # Process hits: skip deprecated, boost human feedback
    processed = []
    for h in hits or []:
        payload = h.get("payload", {}) or {}
        if payload.get("deprecated"):
            continue
        score = float(h.get("score") or 0)
        if payload.get("source") == "human_feedback":
            score += 0.25  # boost
        processed.append((score, h))
    processed.sort(key=lambda x: x[0], reverse=True)

    if processed:
        top_score, top_hit = processed[0]
        if top_score > 0.85:
            return AnswerResponse(source="kb", text=top_hit["payload"].get("answer", ""))

    # Web search fallback
    context_snippets = []
    try:
        res = search_web(question, depth="basic", limit=3)
        if res.get("ok"):
            for r in res["results"][:3]:
                context_snippets.append(f"Source: {r['title']} ({r['url']})\n{r['snippet']}")
    except Exception:
        pass

    # Add KB context (esp human feedback)
    for score, h in processed:
        pl = h["payload"]
        context_snippets.append(f"{pl.get('source')}: Q: {pl.get('question')} — A: {pl.get('answer')}")

    # LLM fallback
    if groq_client:
        try:
            text = call_grok_fallback(question, context_snippets)
            return AnswerResponse(source="grok", text=text)
        except Exception as e:
            traceback.print_exc()
            return AnswerResponse(source="fallback", text=f"LLM error: {str(e)}")

    return AnswerResponse(source="fallback", text="No confident match or LLM.")


# ---------------------------------------------------------------------
# Feedback Endpoints
# ---------------------------------------------------------------------
@app.post("/api/feedback", response_model=FeedbackResponse)
async def feedback(feedback_req: FeedbackRequest):
    if not feedback_req.question or feedback_req.helpful is None:
        raise HTTPException(status_code=400, detail="Missing question/helpful")

    fb_id = save_feedback(
        question=feedback_req.question,
        answer=feedback_req.answer,
        helpful=feedback_req.helpful,
        corrected_answer=feedback_req.corrected_answer,
        comment=feedback_req.comment
    )
    return FeedbackResponse(ok=True, id=fb_id)


@app.get("/api/feedback/all", response_model=FeedbackResponse)
async def get_feedback_list():
    try:
        data = get_all_feedback()
        return FeedbackResponse(ok=True, feedback=data)
    except Exception as e:
        return FeedbackResponse(ok=False, error=str(e))


# ---------------------------------------------------------------------
# Human feedback -> KB update (learning)
# ---------------------------------------------------------------------
@app.post("/api/feedback/train", response_model=FeedbackResponse)
async def feedback_train(train_req: TrainRequest):
    try:
        if not train_req.question or not train_req.corrected_answer:
            raise HTTPException(status_code=400, detail="Missing fields")

        fb_id = save_feedback(
            question=train_req.question,
            answer="",
            helpful=False,
            corrected_answer=train_req.corrected_answer,
            comment=train_req.comment
        )

        vec = model.encode(train_req.question).tolist()
        new_point = {
            "id": str(uuid.uuid4()),
            "vector": vec,
            "payload": {
                "question": train_req.question,
                "answer": train_req.corrected_answer,
                "source": "human_feedback",
                "feedback_id": fb_id,
                "comment": train_req.comment,
                "deprecated": False
            }
        }

        upsert_points(collection_name=COLLECTION, points=[new_point])

        # Mark older similar ones deprecated
        try:
            sim = search_vectors(collection_name=COLLECTION, query_vector=vec, top=6)
            for s in sim or []:
                sid = s.get("id")
                if sid == new_point["id"]:
                    continue
                if s.get("score", 0) > 0.7:
                    qdrant_client = get_qdrant_client()
                    qdrant_client.update(collection_name=COLLECTION, point_id=sid,
                                         payload={"deprecated": True})
        except Exception as e:
            print("[feedback_train] deprecation failed:", e)

        return FeedbackResponse(ok=True, id=fb_id)

    except Exception as e:
        traceback.print_exc()
        return FeedbackResponse(ok=False, error=str(e))


# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("Starting backend with human feedback learning...")
    import uvicorn
    try:
        ensure_collection(collection_name=COLLECTION, recreate=False)
    except Exception:
        print("⚠️ Warning: collection check failed at startup.")
    uvicorn.run(app, host="0.0.0.0", port=5000)
