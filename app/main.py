"""FastAPI 서비스: Agent를 REST API로 노출.

실행: uvicorn app.main:app --reload
문서: http://127.0.0.1:8000/docs  (Swagger UI에서 바로 시연 가능)
"""
from fastapi import FastAPI
from pydantic import BaseModel

from app.config import require_api_key
from app.graph import ask

app = FastAPI(
    title="제조 현장 지원 AI Agent (포트폴리오 데모)",
    description="LangGraph + RAG + Tool calling 기반 P&T 공정 지원 Agent. "
    "공정 SOP 검색(RAG), 설비 로그/FDC 알람 조회, 현황 리포트를 자동 수행.",
    version="1.0.0",
)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    tool_calls: list[dict]


@app.on_event("startup")
def _startup():
    require_api_key()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    """제조 현장 질문을 받아 Agent가 도구를 호출하며 근거 기반 답변을 생성한다."""
    return ask(req.question)
