"""Agent가 호출하는 도구(tool) 정의.

실제 현장에서는 이 함수들이 MES/FDC/장비 API를 호출하지만,
데모에서는 가상 CSV(Legacy 시스템 대체)를 조회한다.
도구 인터페이스만 동일하게 유지하면 실제 시스템 연동으로 교체 가능하다.
"""
import csv

from langchain_core.tools import tool

from app.config import DATA_DIR
from app.rag import search_docs


@tool
def search_process_docs(query: str) -> str:
    """공정 SOP/지식베이스에서 절차·기준·대응 가이드를 검색한다.
    공정 방법, 불량 대응, 관리 기준, 알람 대응 가이드 질문에 사용한다."""
    return search_docs(query)


def _read_csv(filename: str) -> list[dict]:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@tool
def query_equipment_logs(equipment_id: str = "", status: str = "") -> str:
    """설비 계측 로그(MES/장비 데이터 대체)를 조회한다.
    equipment_id(예: BOND-01) 또는 status(NORMAL/WARN/ALARM)로 필터링할 수 있다.
    설비 상태, 계측값 추이, 이상 발생 시점 확인에 사용한다."""
    rows = _read_csv("equipment_logs.csv")
    if equipment_id:
        rows = [r for r in rows if r["equipment_id"] == equipment_id]
    if status:
        rows = [r for r in rows if r["status"].upper() == status.upper()]
    if not rows:
        return "조건에 맞는 로그가 없습니다."
    return "\n".join(
        f"{r['timestamp']} | {r['equipment_id']} | {r['process_step']} | "
        f"{r['metric']}={r['value']}{r['unit']} | {r['status']}"
        for r in rows
    )


@tool
def get_fdc_alarms(severity: str = "") -> str:
    """FDC 알람 목록을 조회한다. severity(Critical/Major/Minor)로 필터링 가능.
    설비 이상 알람, 심각도, 관련 로트 확인에 사용한다."""
    rows = _read_csv("fdc_alarms.csv")
    if severity:
        rows = [r for r in rows if r["severity"].lower() == severity.lower()]
    if not rows:
        return "조건에 맞는 알람이 없습니다."
    return "\n".join(
        f"{r['alarm_id']} | {r['timestamp']} | {r['equipment_id']} | "
        f"[{r['severity']}] {r['alarm_type']} | {r['description']} | lot={r['lot_id']}"
        for r in rows
    )


@tool
def summarize_shift_status() -> str:
    """현재 교대(shift)의 설비/알람 현황 집계 통계를 반환한다.
    일일 리포트나 현황 요약 생성에 사용한다."""
    logs = _read_csv("equipment_logs.csv")
    alarms = _read_csv("fdc_alarms.csv")
    by_status: dict[str, int] = {}
    for r in logs:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    by_sev: dict[str, int] = {}
    for a in alarms:
        by_sev[a["severity"]] = by_sev.get(a["severity"], 0) + 1
    crit = [a["alarm_id"] + "(" + a["equipment_id"] + ")" for a in alarms if a["severity"] == "Critical"]
    return (
        f"로그 상태 집계: {by_status}\n"
        f"알람 심각도 집계: {by_sev}\n"
        f"Critical 알람: {', '.join(crit) if crit else '없음'}"
    )


ALL_TOOLS = [search_process_docs, query_equipment_logs, get_fdc_alarms, summarize_shift_status]
