"""CLI 데모 러너: API 서버 없이 터미널에서 Agent를 바로 시연.

실행: python demo_cli.py
대화형으로 질문하거나, 인자로 미리 정의된 시나리오를 실행한다.
    python demo_cli.py --scenario
"""
import sys

from app.config import require_api_key
from app.graph import ask

SCENARIOS = [
    "HBM TSV 적층 본딩에서 정렬 오차 허용 기준이 얼마야?",
    "BOND-01 설비에 지금 이상 있어? 로그 보여줘.",
    "Critical 알람만 알려줘.",
    "FT-02에서 Contact Test 실패율이 급증했는데 원인이 뭐고 어떻게 대응해야 해?",
    "이번 교대 현황을 리포트로 요약해줘.",
]


def run(question: str):
    print(f"\n[질문] {question}")
    result = ask(question)
    if result["tool_calls"]:
        print("[Agent 도구 호출]")
        for tc in result["tool_calls"]:
            print(f"  - {tc['tool']}({tc['args']})")
    print(f"[답변]\n{result['answer']}")
    print("=" * 70)


def main():
    require_api_key()
    if "--scenario" in sys.argv:
        for q in SCENARIOS:
            run(q)
        return
    print("제조 현장 지원 AI Agent 데모. 질문을 입력하세요. (종료: quit)")
    while True:
        try:
            q = input("\n질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"quit", "exit", "q"}:
            break
        if q:
            run(q)


if __name__ == "__main__":
    main()
