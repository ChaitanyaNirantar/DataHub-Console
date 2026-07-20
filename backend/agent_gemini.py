"""
Agentic Development, powered by Gemini instead of Claude.

Same job as agent.py: translate a researcher's natural-language
question into a single read-only SQL query against DataHub, run it,
and return structured results. Swapped in here because Google AI
Studio's Gemini Flash models are free to use for prototyping
(generous daily request quota, no credit card).

Get a free API key at: https://aistudio.google.com/apikey
Then:  export GEMINI_API_KEY=your-key-here

Docs: https://ai.google.dev/gemini-api/docs
"""

import os
import json
import logging
from typing import Dict, Any

from google import genai
from google.genai import types

from agent_db import SCHEMA_DESCRIPTION, run_safe_query, UnsafeQueryError

log = logging.getLogger("agent")

# Flash models are the ones covered by the free tier as of mid-2026.
# "gemini-flash-latest" is Google's rolling alias for the newest Flash
# model, so this stays current without code changes. Pin to an exact
# version (e.g. "gemini-2.5-flash") if you want reproducible behavior.
MODEL = "gemini-flash-latest"

SYSTEM_PROMPT = f"""You are a data assistant for DataHub, a research data platform.
You translate a researcher's natural-language question into a single
read-only SQLite SELECT query against the following schema:

{SCHEMA_DESCRIPTION}

Rules:
- Respond with JSON only: {{"sql": "<the SELECT statement>", "explanation": "<one sentence on what it does>"}}
- The SQL must be a single SELECT statement. Never write INSERT/UPDATE/DELETE/DROP/ATTACH/PRAGMA.
- Always include a LIMIT clause (default 20) unless the user asks for aggregates only.
- If the question cannot be answered with this schema, return {{"sql": null, "explanation": "<why not>"}}.
"""


class QueryAgent:
    def __init__(self, api_key: str = None):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Get a free key at "
                "https://aistudio.google.com/apikey and export it."
            )
        self.client = genai.Client(api_key=key)

    def _translate(self, question: str) -> Dict[str, Any]:
        resp = self.client.models.generate_content(
            model=MODEL,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",  # forces valid JSON back, no fence-stripping needed
                temperature=0,
            ),
        )
        text = (resp.text or "").strip()
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


if __name__ == "__main__":
    agent = QueryAgent()
    out = agent.ask("What are the top 5 most-starred Python repos with an MIT license?")
    print(json.dumps(out, indent=2))
