import json
import logging
from datetime import date
from pathlib import Path

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from db import get_db

logger = logging.getLogger(__name__)

_CONCEPTS_PATH = Path(__file__).parent.parent / "tools" / "ict_concepts.json"

_CLASSIFY_SYSTEM = """\
트레이딩 약점 태그를 보고 아래 3가지 중 하나만 정확히 반환하세요. 다른 문자는 출력하지 마세요.

ICT개념  - ICT 기술 개념이 부족해서 발생하는 약점 (예: 특정 패턴 미인식, 진입 기준 혼동)
심리     - 알고는 있지만 감정·충동·규율 부재로 발생하는 약점 (예: 충동매매, 손절 회피)
패턴     - 유저 고유의 반복 행동 데이터로만 판단 가능한 약점 (예: 특정 시간대 연속 손실)"""

_GENERATE_SYSTEM = """\
당신은 ICT(Inner Circle Trader) 전문 트레이딩 코치입니다.
주어진 트레이딩 약점 태그에 대한 ICT 개념 설명을 JSON으로 생성하세요.
반드시 아래 키를 포함하세요:
  정의: str
  핵심_포인트: list[str] (정확히 3개)
  실수_패턴: str
  개선_방법: str
  category: 항상 "auto_generated"으로 고정"""

_classify_llm: ChatOpenAI | None = None
_generate_llm: ChatOpenAI | None = None


def _get_classify_llm() -> ChatOpenAI:
    global _classify_llm
    if _classify_llm is None:
        _classify_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _classify_llm


def _get_generate_llm() -> ChatOpenAI:
    global _generate_llm
    if _generate_llm is None:
        _generate_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    return _generate_llm


def _classify(tag: str) -> str:
    result = _get_classify_llm().invoke([
        {"role": "system", "content": _CLASSIFY_SYSTEM},
        {"role": "user", "content": f"약점 태그: {tag}"},
    ])
    return result.content.strip()


def _handle_ict(tag: str) -> str:
    gen = _get_generate_llm().invoke([
        {"role": "system", "content": _GENERATE_SYSTEM},
        {"role": "user", "content": f"약점 태그: {tag}"},
    ])
    concept_data: dict = json.loads(gen.content)
    concept_data["category"] = "auto_generated"

    concepts = json.loads(_CONCEPTS_PATH.read_text(encoding="utf-8"))
    concepts[tag] = concept_data
    _CONCEPTS_PATH.write_text(
        json.dumps(concepts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    import tools.concept_tool as _ct
    _ct._concepts = None  # 캐시 무효화 → 다음 호출 시 파일에서 재로드

    points = "\n".join(f"  • {p}" for p in concept_data["핵심_포인트"])
    return (
        f"【{tag}】(자동 생성)\n"
        f"정의: {concept_data['정의']}\n\n"
        f"핵심 포인트:\n{points}\n\n"
        f"개선 방법: {concept_data['개선_방법']}"
    )


def _handle_psychology(tag: str) -> str:
    return (
        f"이 패턴은 ICT 기술보다 트레이딩 심리 문제입니다.\n\n"
        f"'{tag}' 약점은 기술적 지식 부족이 아닌 심리적 요인에서 비롯됩니다. "
        f"트레이딩 규칙 준수, 감정 관리, 일관성 유지에 집중하세요."
    )


def _handle_pattern(tag: str, session_id: str) -> str:
    today = date.today().isoformat()
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO weaknesses (session_id, weakness, count, last_seen)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(session_id, weakness)
                DO UPDATE SET count = count + 1, last_seen = excluded.last_seen
                """,
                (session_id, tag, today),
            )
    except Exception as e:
        logger.warning("_handle_pattern DB upsert failed: %s", e)
    return f"'{tag}' 패턴을 계속 모니터링하겠습니다. 충분한 데이터가 쌓이면 분석 결과를 제공합니다."


def fallback_classify_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("fallback_classify_node start | session_id=%s", session_id)
    weaknesses = state.get("weaknesses", [])
    if not weaknesses:
        return {}

    tag = weaknesses[0]
    messages = list(state.get("messages", []))

    category = _classify(tag)

    if category == "ICT개념":
        msg = _handle_ict(tag)
    elif category == "심리":
        msg = _handle_psychology(tag)
    else:
        msg = _handle_pattern(tag, session_id)

    messages.append(AIMessage(content=msg))
    logger.info("fallback_classify_node end | session_id=%s tag=%s category=%s", session_id, tag, category)
    return {"messages": messages}
