import io
import logging

import pandas as pd

logger = logging.getLogger(__name__)

_REQUIRED_COLS = {"date", "result"}


def preprocess_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("preprocess_node start | session_id=%s", session_id)

    raw_trades: list[dict] = state.get("raw_trades", [])
    if raw_trades:
        result = _preprocess_bybit(raw_trades, session_id)
    else:
        result = _preprocess_journal(state.get("journal_data", ""), session_id)

    logger.info("preprocess_node end | session_id=%s", session_id)
    return result


# ---------------------------------------------------------------------------
# journal CSV 전처리
# ---------------------------------------------------------------------------

def _preprocess_journal(journal_data: str, session_id: str) -> dict:
    if not journal_data.strip():
        logger.warning("preprocess_node journal: journal_data is empty | session_id=%s", session_id)
        return {}

    try:
        df = pd.read_csv(io.StringIO(journal_data))
    except Exception as e:
        logger.warning("preprocess_node journal: CSV parse failed: %s", e)
        return {}

    # 컬럼명 소문자 변환 + 공백 제거
    df.columns = [c.strip().lower() for c in df.columns]

    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        logger.warning(
            "preprocess_node journal: missing required columns %s | session_id=%s",
            missing, session_id,
        )
        return {}

    # 값 정규화
    df["result"] = df["result"].astype(str).str.strip().str.lower()
    df["setup"] = df["setup"].astype(str).str.strip()
    df["rr"] = pd.to_numeric(df["rr"], errors="coerce").fillna(0.0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["date"])

    normalized_csv = df.to_csv(index=False)
    logger.info(
        "preprocess_node journal: normalized %d rows | session_id=%s",
        len(df), session_id,
    )
    return {"journal_data": normalized_csv}


# ---------------------------------------------------------------------------
# Bybit API 응답 전처리
# ---------------------------------------------------------------------------

def _preprocess_bybit(raw_trades: list[dict], session_id: str) -> dict:
    rows = []
    for trade in raw_trades:
        closed_pnl_str = trade.get("closedPnl", "0")
        try:
            closed_pnl = float(closed_pnl_str)
        except (ValueError, TypeError):
            closed_pnl = 0.0

        # closedPnl == 0 은 진입 체결로 간주 → 스킵
        if closed_pnl == 0.0:
            continue

        result = "win" if closed_pnl > 0 else "loss"

        exec_time_str = trade.get("execTime", "0")
        try:
            date_str = pd.to_datetime(int(exec_time_str), unit="ms").strftime("%Y-%m-%d")
        except Exception as e:
            logger.warning("preprocess_node bybit: execTime parse failed: %s", e)
            date_str = ""

        exec_value_str = trade.get("execValue", "0")
        try:
            exec_value = float(exec_value_str)
        except (ValueError, TypeError):
            exec_value = 0.0

        symbol = trade.get("symbol", "")
        setup = symbol.replace("USDT", "").replace("PERP", "").strip()

        exec_price = trade.get("execPrice", "")
        side = trade.get("side", "").lower()
        entry_price = exec_price if side == "buy" else ""
        exit_price = exec_price if side == "sell" else ""

        rows.append({
            "date": date_str,
            "result": result,
            "rr": 0.0,
            "setup": setup,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "closed_pnl": closed_pnl,
            "exec_value": exec_value,
        })

    if not rows:
        logger.warning(
            "preprocess_node bybit: no closed trades found | session_id=%s", session_id
        )
        return {}

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["date"])
    normalized_csv = df.to_csv(index=False)
    logger.info(
        "preprocess_node bybit: normalized %d closed trades | session_id=%s",
        len(df), session_id,
    )
    return {"journal_data": normalized_csv}
