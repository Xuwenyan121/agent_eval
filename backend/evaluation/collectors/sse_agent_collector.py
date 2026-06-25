"""
SSE Agent Collector - Streaming Server-Sent Events protocol.
Aggregates SSE chunks into a single complete text output.

This is the PRIMARY collector for the project's target agent
(corp-map-app/v3/chat/simple with text/event-stream).
"""

import httpx
import json
import logging
import time
from typing import Optional

from evaluation.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class SSEAgentCollector(BaseCollector):
    """
    Calls the target HTTP/SSE Agent endpoint and aggregates streaming response.
    Supports:
      - Standard SSE format: `data: {...}` lines
      - Configurable content field path (e.g. choices[0].delta.content)
      - Configurable done marker (e.g. [DONE])
      - Retry with exponential backoff
    """

    def __init__(self, endpoint_config: dict):
        super().__init__(endpoint_config)
        self.sse_event_field = endpoint_config.get("sse_event_field", "choices[0].delta.content")
        self.done_marker = endpoint_config.get("sse_done_marker", "[DONE]")

    async def collect(self, query: str, sample_vars: Optional[dict] = None) -> dict:
        """
        Call the Agent SSE endpoint and aggregate streaming chunks.
        Returns: {"output": str, "chunks": list, "latency_ms": int, "error": str|None,
                  "meta": dict|None}  # metadata from event: meta
        """
        sample_vars = sample_vars or {}
        headers, body = self._render(query, sample_vars)
        chunks_log = []
        meta_data = None  # Captured from event: meta
        start = time.monotonic()
        last_err = None

        for attempt in range(self.retry_times):
            try:
                full_text = ""
                chunk_count = 0
                async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                    async with client.stream(self.method, self.url, headers=headers, json=body) as response:
                        response.raise_for_status()

                        # Verify content type is SSE
                        content_type = response.headers.get("content-type", "")
                        if "text/event-stream" not in content_type and "text/" not in content_type:
                            logger.debug("Non-SSE content-type: %s (will try to parse anyway)", content_type)

                        current_event_type = None  # Track SSE event type from "event:" lines

                        async for line in response.aiter_lines():
                            if not line:
                                continue

                            # Standard SSE: lines start with "data:"
                            if line.startswith("data:"):
                                data = line[5:].strip()
                            else:
                                # Some agents send raw JSON without "data:" prefix
                                data = line.strip()
                                if not data.startswith("{"):
                                    continue

                            # Check for stream termination
                            # Match exact marker, "event: <marker>", or "event:<marker>"
                            if data == self.done_marker:
                                break
                            if data.startswith("event:") and data.split(":", 1)[1].strip() == self.done_marker:
                                break

                            # Track event type markers (e.g. "event: delta", "event: progress")
                            if data.startswith("event:"):
                                current_event_type = data.split(":", 1)[1].strip()
                                continue

                            # Parse JSON
                            try:
                                chunk_json = json.loads(data)
                            except json.JSONDecodeError:
                                chunks_log.append({"raw": data, "chunk_index": chunk_count})
                                continue

                            # Capture meta event data (agentId, convId, title, etc.)
                            if current_event_type == "meta":
                                meta_data = chunk_json
                                logger.debug("Captured meta: %s", meta_data)
                                chunk_count += 1
                                continue

                            # Check for finish in JSON (e.g. {"finishReason":"SUCCESS"})
                            if chunk_json.get("finishReason") or "finish_reason" in chunk_json:
                                break

                            # If event types are used, only extract from "delta" events
                            # (skip "progress", etc.)
                            if current_event_type and current_event_type not in ("delta", "message", "content"):
                                chunk_count += 1
                                continue

                            # Extract content using configured field path
                            content = self.extract_field(chunk_json, self.sse_event_field)
                            if content:
                                full_text += content
                                chunks_log.append({"content": content, "chunk_index": chunk_count})
                            chunk_count += 1

                latency = int((time.monotonic() - start) * 1000)
                logger.debug(
                    "SSE collected: %d chunks, %d chars, %dms, meta=%s, url=%s",
                    len(chunks_log), len(full_text), latency,
                    "yes" if meta_data else "no", self.url,
                )
                return {
                    "output": full_text,
                    "chunks": chunks_log,
                    "latency_ms": latency,
                    "meta": meta_data,
                    "error": None,
                }

            except httpx.TimeoutException as e:
                last_err = f"Timeout after {self.timeout}s: {e}"
                logger.warning("SSE attempt %d/%d timeout: %s", attempt + 1, self.retry_times, e)
            except httpx.HTTPStatusError as e:
                last_err = f"HTTP {e.response.status_code}: {e}"
                logger.warning("SSE attempt %d/%d HTTP error: %s", attempt + 1, self.retry_times, e)
                if e.response.status_code in (401, 403, 404):
                    break  # Don't retry auth/not-found errors
            except httpx.ConnectError as e:
                last_err = f"Connection failed: {e}"
                logger.warning("SSE attempt %d/%d connect error: %s", attempt + 1, self.retry_times, e)
            except Exception as e:
                last_err = str(e)
                logger.warning("SSE attempt %d/%d failed: %s", attempt + 1, self.retry_times, e)

            # Brief backoff before retry
            if attempt < self.retry_times - 1:
                import asyncio
                await asyncio.sleep(min(2 ** attempt, 10))

        return {
            "output": "",
            "chunks": chunks_log,
            "latency_ms": int((time.monotonic() - start) * 1000),
            "meta": meta_data,
            "error": str(last_err),
        }

    async def test_connection(self, test_query: str = "hello") -> dict:
        """
        Enhanced connectivity test with SSE protocol verification.
        """
        result = await self.collect(test_query)
        has_output = bool(result["output"])
        has_chunks = len(result["chunks"]) > 0

        return {
            "status": "online" if has_output else "offline",
            "latency_ms": result["latency_ms"],
            "sample_output": result["output"][:200] if result["output"] else "",
            "sse_chunks_received": len(result["chunks"]),
            "protocol_verified": has_output and has_chunks,
            "protocol_details": {
                "has_stream_output": has_output,
                "has_sse_chunks": has_chunks,
                "sse_event_field": self.sse_event_field,
                "done_marker": self.done_marker,
                "response_length": len(result["output"]),
                "has_meta": result.get("meta") is not None,
                "meta_agent_id": result.get("meta", {}).get("agentId", "") if result.get("meta") else "",
            },
            "error": result["error"],
        }
