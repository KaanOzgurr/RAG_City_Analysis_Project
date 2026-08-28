import sys
import os
import sqlite3

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "data", "scripts"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import app as rag_app

app = FastAPI(title="Sehrimi Tani API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    query: str
    category: str = None


class FeedbackRequest(BaseModel):
    message_id: int
    value: str


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend calisiyor"}


@app.post("/ask")
def ask(req: AskRequest):
    result = rag_app.invoke({
        "query": req.query,
        "category": req.category,
        "chunks": [],
        "answer": "",
        "sources": []
    })

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "category": result["category"]
    }


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    conn = sqlite3.connect("data/sehrimi_tani.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feedback (message_id, value) VALUES (?, ?)",
        (req.message_id, req.value)
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}
