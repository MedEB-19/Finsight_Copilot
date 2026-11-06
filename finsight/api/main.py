"""FastAPI backend with audit logging (SQL Server audit_log table)."""
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from finsight.agent.graph import ask
from finsight.db.engine import get_engine

log = logging.getLogger("finsight.api")
app = FastAPI(title="FinSight AI", version="1.0")


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class Answer(BaseModel):
    answer: str
    tools_used: list[str]
    latency_ms: int


def _audit(question: str, res: dict) -> None:
    try:
        with get_engine().begin() as c:
            c.execute(text("INSERT INTO audit_log(question, tools_used, answer, latency_ms, status) "
                           "VALUES (:q, :t, :a, :l, :s)"),
                      {"q": question, "t": ",".join(res.get("tools_used", [])), "a": res.get("answer"),
                       "l": res.get("latency_ms"), "s": res.get("status", "ok")})
    except Exception as e:  # never fail the user request because logging failed
        log.error("audit failed: %s", e)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=Answer)
def ask_endpoint(body: Question):
    try:
        res = ask(body.question)
    except Exception as e:
        _audit(body.question, {"answer": str(e), "status": "error"})
        raise HTTPException(500, f"Agent error: {e}. Is Ollama running with the model pulled?")
    _audit(body.question, res)
    return Answer(answer=res["answer"], tools_used=res["tools_used"], latency_ms=res["latency_ms"])


@app.get("/audit")
def audit(limit: int = 50):
    with get_engine().connect() as c:
        rows = c.execute(text("SELECT TOP (:n) audit_id, created_at, question, tools_used, latency_ms, status "
                              "FROM audit_log ORDER BY audit_id DESC"), {"n": min(limit, 200)}).mappings().all()
    return [dict(r) for r in rows]
