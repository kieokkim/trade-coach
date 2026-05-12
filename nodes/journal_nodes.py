import io
import json
import logging

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

_llm: ChatOpenAI | None = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    return _llm


_JOURNAL_SYSTEM = """\
You are a trading journal writer. Given a list of trades (CSV), write a journal entry for each closed trade.

For each trade return a JSON object with these keys:
  date:          str   (trade date, YYYY-MM-DD)
  symbol:        str   (asset or setup name)
  result:        str   ('win' or 'loss')
  rr:            float (risk:reward ratio)
  entry_reason:  str   (ICT-based entry rationale, inferred from setup/context; empty string if cannot determine)
  exit_reason:   str   (exit rationale, inferred from result/context; empty string if cannot determine)
  reflection:    str   (one-sentence lesson learned, in Korean)

Return JSON with key "entries" containing an array of the above objects.
If a field cannot be determined from the data, set it to an empty string.
Write reflection in Korean."""


def journal_write_node(state: dict) -> dict:
    """preprocess 이후 정규화된 journal_data 기반으로 거래별 매매일지 자동 작성."""
    session_id = state.get("session_id", "default")
    logger.info("journal_write_node start | session_id=%s", session_id)

    journal_data: str = state.get("journal_data", "")
    if not journal_data.strip():
        logger.warning("journal_write_node: journal_data is empty | session_id=%s", session_id)
        return {"journal_entries": [], "needs_user_input": False}

    try:
        df = pd.read_csv(io.StringIO(journal_data))
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        logger.warning("journal_write_node: CSV parse failed: %s", e)
        return {"journal_entries": [], "needs_user_input": False}

    has_entry_reason = "entry_reason" in df.columns
    has_exit_reason = "exit_reason" in df.columns
    entry_reason_empty = has_entry_reason and df["entry_reason"].astype(str).str.strip().eq("").all()
    exit_reason_empty = has_exit_reason and df["exit_reason"].astype(str).str.strip().eq("").all()
    needs_user_input = (not has_entry_reason or entry_reason_empty) or (not has_exit_reason or exit_reason_empty)

    try:
        msg = _get_llm().invoke([
            SystemMessage(content=_JOURNAL_SYSTEM),
            HumanMessage(content=f"Trades:\n{journal_data}"),
        ])
        parsed = json.loads(msg.content)
        entries: list[dict] = parsed.get("entries", [])
    except Exception as e:
        logger.warning("journal_write_node LLM error: %s", e)
        entries = []

    if needs_user_input:
        logger.info(
            "journal_write_node: entry/exit reasons missing, needs_user_input=True | session_id=%s",
            session_id,
        )

    logger.info(
        "journal_write_node end | session_id=%s entries=%d needs_user_input=%s",
        session_id, len(entries), needs_user_input,
    )
    return {"journal_entries": entries, "needs_user_input": needs_user_input}
