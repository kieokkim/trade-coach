import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_SAMPLE_PATH = Path(__file__).parent.parent / "data" / "sample_trades.json"
_BYBIT_EXEC_URL = "https://api.bybit.com/v5/execution/list"


def new_data_check_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("new_data_check_node start | session_id=%s", session_id)

    last_fetched_at = state.get("last_fetched_at", "")
    if not last_fetched_at:
        logger.info("new_data_check_node: first run, has_new_data=True | session_id=%s", session_id)
        return {"has_new_data": True}

    try:
        data = json.loads(_SAMPLE_PATH.read_text(encoding="utf-8"))
        trades = data.get("result", {}).get("list", [])
        if not trades:
            return {"has_new_data": False}

        max_exec_ms = max(int(t.get("execTime", 0)) for t in trades)
        max_exec_dt = datetime.fromtimestamp(max_exec_ms / 1000, tz=timezone.utc)
        last_dt = datetime.fromisoformat(last_fetched_at.replace("Z", "+00:00"))

        has_new = max_exec_dt > last_dt
        logger.info(
            "new_data_check_node: max_exec=%s last=%s has_new_data=%s | session_id=%s",
            max_exec_dt.isoformat(), last_fetched_at, has_new, session_id,
        )
        return {"has_new_data": has_new}
    except Exception as e:
        logger.warning("new_data_check_node: comparison failed: %s", e)
        return {"has_new_data": True}


def bybit_fetch_node(state: dict) -> dict:
    session_id = state.get("session_id", "default")
    logger.info("bybit_fetch_node start | session_id=%s", session_id)

    api_key = os.getenv("BYBIT_API_KEY", "")
    api_secret = os.getenv("BYBIT_API_SECRET", "")

    if api_key and api_secret:
        trades = _fetch_from_api(api_key, api_secret)
    else:
        logger.info("bybit_fetch_node: no API key, loading sample_trades.json | session_id=%s", session_id)
        trades = _load_sample()

    now = datetime.now(tz=timezone.utc).isoformat()
    logger.info("bybit_fetch_node end | session_id=%s trades=%d", session_id, len(trades))
    return {"raw_trades": trades, "last_fetched_at": now}


def _fetch_from_api(api_key: str, api_secret: str) -> list[dict]:
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    query_str = "category=linear&limit=50"
    sign_payload = f"{timestamp}{api_key}{recv_window}{query_str}"
    signature = hmac.new(
        api_secret.encode("utf-8"),
        sign_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-SIGN": signature,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
    }

    try:
        resp = requests.get(
            _BYBIT_EXEC_URL,
            params={"category": "linear", "limit": 50},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("bybit_fetch_node: API response retCode=%s", data.get("retCode"))
        return data.get("result", {}).get("list", [])
    except Exception as e:
        logger.warning("bybit_fetch_node: API call failed: %s, falling back to sample", e)
        return _load_sample()


def _load_sample() -> list[dict]:
    try:
        data = json.loads(_SAMPLE_PATH.read_text(encoding="utf-8"))
        return data.get("result", {}).get("list", [])
    except Exception as e:
        logger.warning("bybit_fetch_node: failed to load sample: %s", e)
        return []
