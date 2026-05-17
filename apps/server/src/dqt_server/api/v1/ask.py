"""Ask API -- natural language question resolution."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from dqt.insights.ask import resolve, AskResult, DisambiguationResult, _classify_intent, _extract_window

router = APIRouter(prefix="/api/v1/ask", tags=["ask"])


class AskRequest(BaseModel):
    question: str
    user_context: dict = {}


class ClarifyRequest(BaseModel):
    question: str
    chosen_fqn: str


def _catalog_from_registry() -> list[dict]:
    from dqt_server.api.v1.insights import _get_registry
    return [
        {"fqn": m.fqn, "display_name": m.display_name}
        for m in _get_registry().list()
    ]


def _resolve_to_response(question: str, catalog: list[dict]) -> dict:
    result = resolve(question, metric_catalog=catalog)
    if isinstance(result, AskResult):
        if result.metric_fqn == "*":
            return {
                "type": "answer",
                "intent": "list",
                "metric_fqn": None,
                "window_days": result.window_days,
                "explanation": None,
            }
        return {
            "type": "answer",
            "intent": result.intent,
            "metric_fqn": result.metric_fqn,
            "display_name": result.display_name,
            "window_days": result.window_days,
            "confidence": result.confidence,
            "explanation": None,  # TODO: wire explain_movement when store is injected
        }
    return {
        "type": "disambiguation",
        "message": result.message,
        "options": [
            {"metric_fqn": o.metric_fqn, "display_name": o.display_name, "confidence": o.confidence}
            for o in result.options
        ],
    }


@router.post("")
async def ask(body: AskRequest) -> dict:
    catalog = _catalog_from_registry()
    return _resolve_to_response(body.question, catalog)


@router.post("/clarify")
async def clarify(body: ClarifyRequest) -> dict:
    catalog = _catalog_from_registry()
    chosen = next((m for m in catalog if m["fqn"] == body.chosen_fqn), None)
    if chosen is None:
        return _resolve_to_response(body.question, catalog)
    return {
        "type": "answer",
        "intent": _classify_intent(body.question),
        "metric_fqn": chosen["fqn"],
        "display_name": chosen["display_name"],
        "window_days": _extract_window(body.question),
        "confidence": 100.0,
        "explanation": None,
    }
