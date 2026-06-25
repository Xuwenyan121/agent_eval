"""
OpenAI-Compatible Agent Collector - For /v1/chat/completions endpoints.
Supports both streaming and non-streaming modes.
"""

import httpx
import json
import logging
import time
from typing import Optional

from evaluation.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class OpenAICompatCollector(BaseCollector):
    """
    Collector for OpenAI-compatible chat completions endpoints.
    Automatically constructs the standard messages format:
      {"messages": [{"role": "user", "content": "..."}]}

    Supports both streaming (stream=true) and non-streaming responses.
    """

    def __init__(self, endpoint_config: dict):
        super().__init__(endpoint_config)
        self.model = endpoint_config.get("model", "gpt-3.5-turbo")
        self.stream = endpoint_config.get("stream", True)
        # Build standard OpenAI-compatible headers
        if "Authorization" not in self.headers and "authorization" not in self.headers:
            api_key = endpoint_config.get("api_key", "")
            if api_key:
                self.headers["Authorization"] = f"Bearer {api_key}"
        if "Content-Type" not in self.headers and "content-type" not in self.headers:
            self.headers["Content-Type"] = "application/json"

    def _build_messages(self, query: str) -> list:
        """Build standard OpenAI messages format."""
        return [{"role": "user", "content": query}]

    async def collect(self, query: str, sample_vars: Optional[dict] = None) -> dict:
        """
        Call OpenAI-compatible endpoint.
        Returns: {"output": str, "chunks": list, "latency_ms": int, "error": str|None}
        """
        sample_vars = sample_vars or {}
        headers = dict(self.headers)

        # Apply any header variable overrides
        for var_name, val in sample_vars.items():
            for k, v in list(headers.items()):
                if isinstance(v, str) and "{{" + var_name + "}}" in v:
                    headers[k] = v.replace("{{" + var_name + "}}", str(val))

        body = {
            "model": self.model,
            "messages": self._build_messages(query),
            "stream": self.stream,
        }
        # Merge any extra body params from template
        if self.body_template:
            for k, v in self.body_template.items():
                if k not in body:
                    body[k] = v

        start = time.monotonic()
        last_err = None

        for attempt in range(self.retry_times):
            try:
                if self.stream:
                    return await self._collect_streaming(headers, body, start)
                else:
                    return await self._collect_non_streaming(headers, body, start)

            except httpx.TimeoutException as e:
                last_err = f"Timeout after {self.timeout}s: {e}"
                logger.warning("OpenAI attempt %d/%d timeout: %s", attempt + 1, self.retry_times, e)
            except httpx.HTTPStatusError as e:
                last_err = f"HTTP {e.response.status_code}: {e}"
                logger.warning("OpenAI attempt %d/%d HTTP error: %s", attempt + 1, self.retry_times, e)
                if e.response.status_code in (401, 403, 404, 429):
                    break
            except Exception as e:
                last_err = str(e)
                logger.warning("OpenAI attempt %d/%d failed: %s", attempt + 1, self.retry_times, e)

            if attempt < self.retry_times - 1:
                import asyncio
                await asyncio.sleep(min(2 ** attempt, 10))

        return {
            "output": "",
            "chunks": [],
            "latency_ms": int((time.monotonic() - start) * 1000),
            "error": str(last_err),
        }

    async def _collect_streaming(self, headers: dict, body: dict, start: float) -> dict:
        """Handle SSE streaming response from OpenAI-compatible endpoint."""
        full_text = ""
        chunks_log = []
        chunk_count = 0

        async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
            async with client.stream(self.method, self.url, headers=headers, json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    # Standard OpenAI format: choices[0].delta.content
                    choices = chunk_json.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_text += content
                            chunks_log.append({"content": content, "chunk_index": chunk_count})
                    chunk_count += 1

        latency = int((time.monotonic() - start) * 1000)
        logger.debug("OpenAI stream: %d chunks, %d chars, %dms", len(chunks_log), len(full_text), latency)
        return {
            "output": full_text,
            "chunks": chunks_log,
            "latency_ms": latency,
            "error": None,
        }

    async def _collect_non_streaming(self, headers: dict, body: dict, start: float) -> dict:
        """Handle standard JSON response from OpenAI-compatible endpoint."""
        async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
            response = await client.request(self.method, self.url, headers=headers, json=body)
            response.raise_for_status()
            response_json = response.json()

        # Standard OpenAI format: choices[0].message.content
        output = ""
        choices = response_json.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            output = message.get("content", "")

        latency = int((time.monotonic() - start) * 1000)
        logger.debug("OpenAI non-stream: %d chars, %dms", len(output), latency)
        return {
            "output": output,
            "chunks": [],
            "latency_ms": latency,
            "error": None,
        }
