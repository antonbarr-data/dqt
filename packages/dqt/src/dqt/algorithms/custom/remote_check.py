# packages/dqt/src/dqt/algorithms/custom/remote_check.py
# Extension point: POST a DataFrame sample to an external HTTP endpoint for scoring.
# Endpoint must accept POST with JSON body:
#   {"reference_stats": {"mean": ..., "std": ...}, "current": [...rows...], "params": {...}}
# and return JSON: {"score": float, "details": {...}}  (details is optional)
from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

import pandas as pd

from dqt.algorithms._base import BaseDetector, DetectorResult, DetectorState, Verdict
from dqt.algorithms._registry import registry

_MAX_ROWS = 1000  # cap to keep payload manageable


@registry.register
class RemoteCheckDetector(BaseDetector):
    """Calls an external HTTP endpoint to score the current DataFrame.

    The endpoint receives a POST request with JSON body::

        {
            "reference_stats": {"mean": float, "std": float, "n_rows": int, "columns": [...]},
            "current": [{"col": val, ...}, ...],   // up to 1000 rows
            "params": {...}                          // detector params passed through
        }

    And must return::

        {"score": float}   // required; float in [0, 1]
        // optional: {"score": 0.1, "details": {"reason": "..."}}

    Example using a local REST endpoint::

        detector = RemoteCheckDetector(
            endpoint="http://localhost:8080/check/null-rate",
            params={"column": "email", "threshold": 0.05},
            timeout=10.0,
        )

    Example using a GraphQL endpoint::

        detector = RemoteCheckDetector(
            endpoint="http://localhost:4000/graphql",
            graphql_query='query Check($rows: JSON!) { checkNullRate(rows: $rows) { score } }',
            graphql_variable="rows",
        )
    """

    slug = "remote_check"
    group = "custom"

    def __init__(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
        graphql_query: str | None = None,
        graphql_variable: str = "rows",
    ) -> None:
        self._endpoint = endpoint
        self._params = params or {}
        self._timeout = timeout
        self._graphql_query = graphql_query
        self._graphql_variable = graphql_variable

    def fit(self, reference: pd.DataFrame) -> DetectorState:
        numeric = reference.select_dtypes(include="number")
        ref_stats: dict[str, Any] = {
            "n_rows": len(reference),
            "columns": list(reference.columns),
        }
        if not numeric.empty:
            ref_stats["mean"] = float(numeric.mean().mean())
            ref_stats["std"] = float(numeric.std().mean())
        return {
            "ref_stats": ref_stats,
            "endpoint": self._endpoint,
            "params": self._params,
            "timeout": self._timeout,
            "graphql_query": self._graphql_query,
            "graphql_variable": self._graphql_variable,
        }

    def score(self, current: pd.DataFrame, state: DetectorState) -> DetectorResult:
        sample = current.head(_MAX_ROWS)
        rows = sample.where(pd.notnull(sample), None).to_dict(orient="records")

        if state["graphql_query"]:
            body = json.dumps({
                "query": state["graphql_query"],
                "variables": {state["graphql_variable"]: rows},
            }).encode()
        else:
            body = json.dumps({
                "reference_stats": state["ref_stats"],
                "current": rows,
                "params": state["params"],
            }).encode()

        req = Request(
            state["endpoint"],
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=state["timeout"]) as resp:
                response = json.loads(resp.read().decode())
        except Exception as exc:
            raise RuntimeError(
                f"RemoteCheckDetector: request to {state['endpoint']} failed: {exc}"
            ) from exc

        if "score" not in response:
            raise ValueError(
                f"RemoteCheckDetector: endpoint {state['endpoint']} response missing 'score' key: {response}"
            )

        score = float(min(max(response["score"], 0.0), 1.0))
        details = response.get("details", {})
        details["endpoint"] = state["endpoint"]
        return DetectorResult(
            score=score,
            verdict=self._verdict(score),
            plain_english=f"Remote endpoint {state['endpoint']} returned score={score:.4f}",
            details=details,
        )
