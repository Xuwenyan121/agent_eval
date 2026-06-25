"""
JSON Agent Collector - For non-streaming HTTP JSON response endpoints.
Useful for agents that return the full response in a single JSON body.
"""

import httpx
import json
import logging
import time
from typing import Optional

from evaluation.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class JSONAgentCollector(BaseCollector):
    """
    Calls an HTTP endpoint that returns a complete JSON response (no streaming).
    Extracts the text output using a configurable response field path.
    """

    def __init__(self, endpoint_config: dict):
        super().__init__(endpoint_config)
        self.response_field = endpoint_config.get("response_field", "output")

    async def collect(self, query: str, sample_vars: Optional[dict] = None) -> dict:
        """
        Call the Agent JSON endpoint and extract the response text.
        Returns: {"output": str, "chunks": list, "latency_ms": int, "error": str|None}
        """
        sample_vars = sample_vars or {}
        headers, body = self._render(query, sample_vars)
        start = time.monotonic()
        last_err = None

        for attempt in range(self.retry_times):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                    response = await client.request(
                        self.method, self.url, headers=headers, json=body,
                    )
                    response.raise_for_status()

                    # Parse JSON response
                    try:
                        response_json = response.json()
                    except json.JSONDecodeError:
                        # Try to use raw text if not valid JSON
                        raw_text = response.text
                        latency = int((time.monotonic() - start) * 1000)
                        logger.debug("Non-JSON response, using raw text (%d chars)", len(raw_text))
                        return {
                            "output": raw_text,
                            "chunks": [],
                            "latency_ms": latency,
                            "error": None,
                        }

                    # Extract output using configured field path
                    output = self.extract_field(response_json, self.response_field)

                    # If field extraction fails, try common field names
                    if not output:
                        for fallback_field in ["output", "text", "content", "result", "message", "answer"]:
                            output = self.extract_field(response_json, fallback_field)
                            if output:
                                logger.debug("Used fallback field: %s", fallback_field)
                                break

                    # Last resort: stringify the whole response
                    if not output:
                        output = json.dumps(response_json, ensure_ascii=False)
                        logger.warning("No field matched, returning full JSON as output")

                    latency = int((time.monotonic() - start) * 1000)
                    logger.debug("JSON collected: %d chars, %dms, url=%s", len(output), latency, self.url)
                    return {
                        "output": output,
                        "chunks": [],
                        "latency_ms": latency,
                        "error": None,
                    }

            except httpx.TimeoutException as e:
                last_err = f"Timeout after {self.timeout}s: {e}"
                logger.warning("JSON attempt %d/%d timeout: %s", attempt + 1, self.retry_times, e)
            except httpx.HTTPStatusError as e:
                last_err = f"HTTP {e.response.status_code}: {e}"
                logger.warning("JSON attempt %d/%d HTTP error: %s", attempt + 1, self.retry_times, e)
                if e.response.status_code in (401, 403, 404):
                    break
            except Exception as e:
                last_err = str(e)
                logger.warning("JSON attempt %d/%d failed: %s", attempt + 1, self.retry_times, e)

            if attempt < self.retry_times - 1:
                import asyncio
                await asyncio.sleep(min(2 ** attempt, 10))

        return {
            "output": "",
            "chunks": [],
            "latency_ms": int((time.monotonic() - start) * 1000),
            "error": str(last_err),
        }
