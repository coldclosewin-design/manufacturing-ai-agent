# 제조 현장 지원 AI Agent (포트폴리오 데모)

> **한 줄 요약**: 반도체 후공정(P&T) 현장의 공정 지식 검색·설비 이상 대응·현황 리포트를
> **LangGraph 기반 Agent**가 자동 수행하는 데모. RAG + Tool Calling + FastAPI 서비스화까지 End-to-End 구현.

SK하이닉스 **AI/DT · Digital Factory** 직무 JD의 핵심 요구사항을 직접 구현으로 증명하기 위한 포트폴리오입니다.

---

## 1. 무엇을 하는가

자연어 질문을 받아 Agent가 스스로 적절한 도구를 호출하고, **근거(출처)에 기반해** 답합니다.

| 질문 예시 | Agent 동작 |
|---|---|
| "HBM 적층 정렬 오차 기준이 얼마야?" | `search_process_docs`(RAG) → SOP 검색 후 기준 + 출처 제시 |
| "BOND-01 지금 이상 있어?" | `query_equipment_logs` → 설비 로그 조회 |
| "Critical 알람만 보여줘" | `get_fdc_alarms` → 심각도 필터 조회 |
| "Contact Test 실패율 급증 원인과 대응은?" | RAG(대응 가이드) + 로그/알람 **교차 분석** → 단계적 원인분석 |
| "이번 교대 현황 리포트로 요약" | `summarize_shift_status` → 집계 후 비즈니스 언어 리포트 |

---

## 2. 아키텍처

```
                 ┌──────────────────────────────────────────────┐
   사용자 질문 ──▶│  FastAPI  (/ask)  또는  CLI (demo_cli.py)      │
                 └───────────────────────┬──────────────────────┘
                                         ▼
                         ┌───────────────────────────────┐
                         │   LangGraph StateGraph         │
                         │                                │
        START ─────────▶ │   agent (LLM + 도구 바인딩)     │◀────────┐
                         │        │                       │         │
                         │        ▼  tools_condition       │         │
                         │   [도구 호출 필요?]              │         │
                         │      ├ yes ─▶ ToolNode ─────────┼─────────┘ (결과 관찰 후 재추론)
                         │      └ no  ─▶ END (최종 답변)    │
                         └───────────────────────────────┘
                                         │
              ┌──────────────────────────┼───────────────────────────┐
              ▼                          ▼                           ▼
   search_process_docs           query_equipment_logs /        summarize_shift_status
   (RAG: 임베딩→벡터검색)          get_fdc_alarms                (집계 리포트)
   data/process_sop.md           data/*.csv  (= MES/FDC/장비 Legacy 대체)
```

**RAG 파이프라인** (`app/rag.py`): SOP 마크다운 → 헤더 단위 청킹(+overlap) → OpenAI 임베딩 → InMemory 벡터스토어 → 유사도 top-k 검색 → 출처 메타데이터와 함께 반환.

**Agent 루프** (`app/graph.py`): `START → agent → (tools ⇄ agent)* → END` 의 ReAct 패턴을 LangGraph로 명시. `recursion_limit`으로 무한루프 방지, `temperature=0`으로 재현성 확보.

---

## 3. 실행 방법

```bash
cd manufacturing_ai_agent
python -m venv .venv && .venv\Scripts\activate      # (Windows) / source .venv/bin/activate (mac/linux)
pip install -r requirements.txt

cp .env.example .env          # .env 열어 OPENAI_API_KEY 입력

# (A) CLI로 미리 정의된 5개 시나리오 시연
python demo_cli.py --scenario

# (B) CLI 대화형
python demo_cli.py

# (C) API 서버 + Swagger UI 시연
uvicorn app.main:app --reload   # http://127.0.0.1:8000/docs
```

---

## 3-1. 실제 실행 결과 (gpt-4o-mini, 검증 완료)

`python demo_cli.py --scenario` 실행 시 5개 시나리오 모두 정상 동작 확인.

**하이라이트 — 멀티스텝 원인분석 (LangGraph ReAct가 도구 3개를 연쇄 호출)**
```
[질문] FT-02에서 Contact Test 실패율이 급증했는데 원인이 뭐고 어떻게 대응해야 해?
[Agent 도구 호출]
  - query_equipment_logs({'equipment_id': 'FT-02', 'status': 'ALARM'})
  - get_fdc_alarms({'severity': 'Major'})
  - search_process_docs({'query': 'Contact Test 실패 대응'})
[답변] (요약)
  1) 핸들러 소켓 접촉 불량  2) 보드 오염  3) 적층 본딩 정렬 문제 역추적
  → 대응: 소켓·보드 점검, PKG-HBM-01 정렬 역추적, FDC 알람 모니터링
  (근거: process_sop.md + 장비 로그/알람 데이터)
```
> 단일 호출이 아니라 **여러 도구를 스스로 호출·관찰하며 교차 추론**한다는 점이 핵심.

**RAG 출처 인용 예시**
```
[질문] HBM TSV 적층 본딩에서 정렬 오차 허용 기준이 얼마야?
[답변] ±3 µm 이내. 초과 시 TSV 접합 불량 발생.
       (출처: process_sop.md / 1. HBM TSV 적층 본딩 공정 (PKG-HBM-01))
```

## 4. JD 요구사항 → 구현 매핑 (면접 설명용)

| JD 요구사항 (AI/DT · Digital Factory) | 본 데모의 구현 |
|---|---|
| LLM 기반 Agent 아키텍처 설계 + 백엔드 | LangGraph StateGraph + FastAPI |
| **LangGraph 기반 업무 자동화 시스템 구축** | `app/graph.py` ReAct 그래프 |
| RAG 시스템 개발 | `app/rag.py` 청킹·임베딩·벡터검색·출처인용 |
| Legacy(MES/FDC/장비) 연동 인터페이스 | `app/tools.py` — CSV를 Legacy 대체, 도구 인터페이스 유지 |
| 현장 활용 서비스(UI/서비스화) | FastAPI `/ask` + Swagger UI |
| Multi-step 의사결정 지원 | RAG + 로그/알람 교차 원인분석 시나리오 |
| 환각 억제 / 신뢰성 | 출처 인용 강제, temperature=0, recursion_limit |
| 기술→비즈니스 언어 보고 | `summarize_shift_status` 리포트 생성 |

---

## 5. 설계 의사결정 (면접 예상질문 대비)

- **왜 LangChain이 아니라 LangGraph?** 공정 의사결정은 조건 분기·도구 반복 호출·실패 재시도가 필요해 선형 체인보다 상태 그래프가 적합. 통제·검증이 쉬움.
- **왜 출처 인용을 강제?** 제조 현장은 오답 비용이 큼. RAG grounding + 인용으로 환각을 억제하고 작업자가 근거를 확인 가능.
- **왜 하이브리드/리랭킹을 언급?** 에러코드·설비ID 같은 정확 매칭이 중요 → 운영 단계 개선 방향으로 제시 가능. (현재 데모는 의미검색, 확장 포인트로 설명)
- **검증 사고 전이**: 임베디드 정적분석·회귀검증 경험을 살려 출력 스키마 검증·정답셋 회귀테스트로 Agent 품질을 관리한다는 운영 관점 제시.

## 6. 향후 확장 (말로 설명할 로드맵)
- 벡터스토어를 pgvector/Milvus로 교체(운영 확장)
- 하이브리드 검색(BM25+벡터) + Re-ranking
- Multi-Agent(이상탐지 / 원인분석 / 조치추천 + supervisor)
- Human-in-the-loop 승인 노드, 응답 평가(LLM-as-judge) 및 비용 모니터링

> ⚠️ 데이터는 전부 가상이며 실제 SK하이닉스 자료가 아닙니다.
