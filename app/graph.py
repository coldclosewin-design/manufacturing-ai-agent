"""LangGraph 기반 제조 현장 지원 Agent.

구조: ReAct 루프를 StateGraph로 명시.
    START → agent(LLM+도구바인딩) → [도구 호출 필요?]
                                      ├─ yes → tools(ToolNode) → agent (관찰 후 재추론)
                                      └─ no  → END

핵심 설계 의도 (면접 설명 포인트):
- 단발성 LLM 호출이 아니라 '도구 호출 → 결과 관찰 → 재추론' 루프를 그래프로 통제한다.
- recursion_limit으로 무한 루프를 방지(신뢰성). 임베디드 검증 사고방식의 전이.
- 시스템 프롬프트로 '근거(출처) 인용'을 강제해 환각을 억제한다.
"""
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI

from app.config import CHAT_MODEL
from app.tools import ALL_TOOLS

SYSTEM_PROMPT = """당신은 반도체 후공정(P&T) 현장을 지원하는 AI 엔지니어링 어시스턴트입니다.

원칙:
1. 공정 절차/기준/대응 방법 질문은 반드시 search_process_docs로 SOP를 검색해 '근거에 기반'해 답한다.
2. 설비 상태/이상은 query_equipment_logs, get_fdc_alarms로 실제 데이터를 조회해 답한다.
3. 현황 요약/리포트 요청은 summarize_shift_status로 집계 후 정리한다.
4. 답변 끝에 사용한 근거(SOP 출처 또는 조회 데이터)를 명시한다.
5. 데이터로 확인되지 않은 내용은 추측하지 말고 '확인 불가'라고 답한다.
6. 원인분석 질문은 SOP의 표준 절차와 실제 로그/알람을 교차 확인해 단계적으로 추론한다.
한국어로 간결하고 실무적으로 답한다."""


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph():
    """LangGraph StateGraph를 컴파일해 반환한다."""
    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)  # 재현성 위해 temperature=0
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def agent_node(state: AgentState):
        messages = state["messages"]
        # 시스템 프롬프트를 항상 맨 앞에 주입
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        return {"messages": [llm_with_tools.invoke(messages)]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))

    graph.add_edge(START, "agent")
    # tools_condition: 마지막 메시지에 tool_call이 있으면 'tools', 없으면 END로 라우팅
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")  # 도구 결과를 관찰하고 다시 추론

    return graph.compile()


# 모듈 로드 시 1회 컴파일
APP_GRAPH = None


def get_graph():
    global APP_GRAPH
    if APP_GRAPH is None:
        APP_GRAPH = build_graph()
    return APP_GRAPH


def ask(question: str) -> dict:
    """질문을 받아 Agent를 실행하고 최종 답변 + 도구 호출 추적을 반환한다."""
    from langchain_core.messages import AIMessage, ToolMessage

    result = get_graph().invoke(
        {"messages": [("user", question)]},
        config={"recursion_limit": 12},
    )
    answer = result["messages"][-1].content
    # 어떤 도구를 어떤 인자로 호출했는지 추적(시연 시 '실제 동작' 증명용)
    trace = []
    for m in result["messages"]:
        if isinstance(m, AIMessage) and m.tool_calls:
            for tc in m.tool_calls:
                trace.append({"tool": tc["name"], "args": tc["args"]})
    return {"answer": answer, "tool_calls": trace}
