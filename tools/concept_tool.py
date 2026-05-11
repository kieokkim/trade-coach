import json
from pathlib import Path

from langchain_core.tools import tool

_CONCEPTS_PATH = Path(__file__).parent / "ict_concepts.json"
_concepts: dict | None = None

CONCEPT_NOT_FOUND_PREFIX = "해당 개념을 찾을 수 없습니다"


def _load_concepts() -> dict:
    global _concepts
    if _concepts is None:
        _concepts = json.loads(_CONCEPTS_PATH.read_text(encoding="utf-8"))
    return _concepts


def _find_key(concepts: dict, weakness_tag: str) -> str | None:
    tag_lower = weakness_tag.lower()
    for key in concepts:
        if tag_lower == key.lower():
            return key
    for key in concepts:
        if tag_lower in key.lower() or key.lower() in tag_lower:
            return key
    return None


@tool
def search_ict_concept(weakness_tag: str) -> str:
    """weakness_tag에 해당하는 ICT 개념 정의와 개선 방법을 반환합니다."""
    concepts = _load_concepts()
    key = _find_key(concepts, weakness_tag)

    if key is None:
        return f"해당 개념을 찾을 수 없습니다: '{weakness_tag}'"

    entry = concepts[key]
    points = "\n".join(f"  • {p}" for p in entry["핵심_포인트"])
    return (
        f"【{key}】\n"
        f"정의: {entry['정의']}\n\n"
        f"핵심 포인트:\n{points}\n\n"
        f"개선 방법: {entry['개선_방법']}"
    )
