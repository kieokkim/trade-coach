import logging
from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from db import get_db
from tools.concept_tool import search_ict_concept, CONCEPT_NOT_FOUND_PREFIX

logger = logging.getLogger(__name__)

_quiz_llm: ChatOpenAI | None = None
_eval_llm:  ChatOpenAI | None = None

_QUIZ_GENERATE_SYSTEM = """\
당신은 트레이딩 코치입니다. ICT 개념 설명을 바탕으로 트레이더를 위한 퀴즈 문항 1개를 만드세요.

요구사항:
- 개념 이해를 확인할 수 있는 실전적 질문
- 객관식이 아닌 서술형 또는 단답형
- 한국어로 작성
- 질문 문장 하나만 출력하세요. 다른 내용은 포함하지 마세요."""

_QUIZ_EVALUATE_SYSTEM = """\
당신은 트레이딩 코치입니다. 트레이더의 퀴즈 답변을 평가하세요.

평가 기준:
- 핵심 개념을 이해하고 있으면 pass
- 완벽하지 않아도 방향이 맞으면 pass
- 완전히 틀리거나 모르겠다고 하면 fail

반드시 아래 형식으로만 응답하세요:
pass: [한 줄 피드백]
또는
fail: [한 줄 피드백과 힌트]"""


def _get_quiz_llm() -> ChatOpenAI:
    global _quiz_llm
    if _quiz_llm is None:
        _quiz_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
    return _quiz_llm


def _get_eval_llm() -> ChatOpenAI:
    global _eval_llm
    if _eval_llm is None:
        _eval_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _eval_llm


def quiz_generate_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("quiz_generate_node start | session_id=%s", session_id)

    weaknesses = state.get("weaknesses", [])
    if not weaknesses:
        logger.info("quiz_generate_node: no weaknesses, skipping | session_id=%s", session_id)
        return {"quiz_question": "", "current_concept": ""}

    primary = weaknesses[0]
    concept_info = search_ict_concept.invoke({"weakness_tag": primary})
    if concept_info.startswith(CONCEPT_NOT_FOUND_PREFIX):
        concept_info = f"{primary} 약점 개선을 위한 트레이딩 원칙"

    try:
        msg = _get_quiz_llm().invoke([
            SystemMessage(content=_QUIZ_GENERATE_SYSTEM),
            HumanMessage(content=f"약점 태그: {primary}\n\n개념 설명:\n{concept_info}"),
        ])
        quiz_question = msg.content.strip()
    except Exception as e:
        logger.warning("quiz_generate_node LLM error: %s | session_id=%s", e, session_id)
        quiz_question = f"{primary} 약점을 개선하기 위해 내일 어떤 규칙을 적용할 건가요?"

    logger.info(
        "quiz_generate_node end | session_id=%s concept=%s",
        session_id, primary,
    )
    return {"quiz_question": quiz_question, "current_concept": primary}


def evaluate_quiz(
    session_id: str,
    quiz_question: str,
    quiz_answer: str,
    current_concept: str,
    retry_count: int = 0,
) -> tuple[str, str]:
    """Streamlit에서 직접 호출. Returns (result: 'pass'|'fail', feedback: str)."""
    if not quiz_answer.strip():
        return "", ""

    concept_info = search_ict_concept.invoke({"weakness_tag": current_concept}) if current_concept else ""
    if concept_info.startswith(CONCEPT_NOT_FOUND_PREFIX):
        concept_info = ""

    context = f"퀴즈 문항: {quiz_question}\n트레이더 답변: {quiz_answer}"
    if concept_info:
        context += f"\n\n참고 개념:\n{concept_info}"

    try:
        msg = _get_eval_llm().invoke([
            SystemMessage(content=_QUIZ_EVALUATE_SYSTEM),
            HumanMessage(content=context),
        ])
        raw = msg.content.strip()
        quiz_result = "pass" if raw.lower().startswith("pass") else "fail"
        feedback = raw.split(":", 1)[1].strip() if ":" in raw else raw
    except Exception as e:
        logger.warning("evaluate_quiz LLM error: %s", e)
        quiz_result = "fail"
        feedback = "평가 중 오류가 발생했습니다."

    # DB 저장
    try:
        today = date.today().isoformat()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO quiz_results (session_id, concept, passed, retry_count, date) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, current_concept, quiz_result == "pass", retry_count, today),
            )
    except Exception as e:
        logger.warning("evaluate_quiz DB error: %s", e)

    return quiz_result, feedback
