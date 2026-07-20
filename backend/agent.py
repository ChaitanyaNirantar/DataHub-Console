"""
Agentic Development: translates a researcher's natural-language
question into an executable, read-only SQL query against DataHub,
runs it, and explains the result in plain language.

Requires ANTHROPIC_API_KEY to be set in the environment.
"""

import os
import json
import logging
from typing import Dict, Any

import anthropic

from agent_db import SCHEMA_DESCRIPTION, run_safe_query, UnsafeQueryError

log = logging.getLogger("agent")

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = f"""You are a data assistant for DataHub, a research data platform.
You translate a researcher's natural-language question into a single
read-only SQLite SELECT query against the following schema:

{SCHEMA_DESCRIPTION}

Rules:
- Output ONLY valid JSON: {{"sql": "<the SELECT statement>", "explanation": "<one sentence on what it does>"}}
- The SQL must be a single SELECT statement. Never write INSERT/UPDATE/DELETE/DROP/ATTACH/PRAGMA.
- Always include a LIMIT clause (default 20) unless the user asks for aggregates only.
- If the question cannot be answered with this schema, return {{"sql": null, "explanation": "<why not>"}}.
"""


class QueryAgent:
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def _translate(self, question: str) -> Dict[str, Any]:
        resp = self.client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Model did not return valid JSON: {text!r}") from e

    def ask(self, question: str) -> Dict[str, Any]:
        plan = self._translate(question)
        if not plan.get("sql"):
            return {"question": question, "sql": None, "explanation": plan.get("explanation"), "results": []}

        try:
            results = run_safe_query(plan["sql"])
        except UnsafeQueryError as e:
            log.warning("Blocked unsafe query: %s", e)
            return {"question": question, "sql": plan["sql"], "error": str(e), "results": []}
        except Exception as e:
            return {"question": question, "sql": plan["sql"], "error": f"query failed: {e}", "results": []}

        return {
            "question": question,
            "sql": plan["sql"],
            "explanation": plan.get("explanation"),
            "results": results,
            "row_count": len(results),
        }
