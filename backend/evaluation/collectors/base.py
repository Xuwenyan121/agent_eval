"""
Base Collector - Abstract base class for all agent protocol collectors.
Defines the shared interface and template variable rendering logic.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from glom import glom
except ImportError:
    glom = None


class BaseCollector(ABC):
    """
    Abstract base for agent collectors.
    All collectors must implement collect() and test_connection().
    """

    def __init__(self, endpoint_config: dict):
        self.url = endpoint_config["endpoint_url"]
        self.headers = endpoint_config.get("headers", {})
        self.body_template = endpoint_config.get("body_template", {})
        self.timeout = endpoint_config.get("timeout", 60)
        self.retry_times = endpoint_config.get("retry_times", 3)
        self.method = endpoint_config.get("method", "POST").upper()
        self.verify_ssl = endpoint_config.get("verify_ssl", True)
        self.defaults = {
            "user_id": endpoint_config.get("default_user_id", "test_user"),
            "conv_id": endpoint_config.get("default_conv_id", str(int(time.time()))),
            "cache_user": endpoint_config.get("cache_user", ""),
        }

    def _render(self, query: str, sample_vars: dict) -> tuple:
        """Render body/header templates, replacing {{var}} placeholders.

        If query is a JSON string containing content/userId/convId fields,
        auto-extract them as individual template variables:
          {{query}}   -> content text only (not the full JSON)
          {{content}} -> same as query (alias)
          {{user_id}} -> from dataset userId or agent default
          {{conv_id}} -> from dataset convId or pipeline-generated value
        """
        content = query
        parsed_uid = ""
        parsed_cid = ""

        # Try to parse input as JSON and extract individual fields
        try:
            parsed = json.loads(query)
            if isinstance(parsed, dict):
                content = str(parsed.get("content") or parsed.get("query") or query)
                parsed_uid = str(parsed.get("userId") or parsed.get("user_id") or "")
                parsed_cid = str(parsed.get("convId") or parsed.get("conv_id") or "")
        except (json.JSONDecodeError, TypeError):
            pass  # query is plain text, use as-is

        # Build variable map: sample_vars override parsed values override defaults
        vars_ = {
            "query": content,
            "content": content,
            "user_id": parsed_uid or self.defaults.get("user_id", ""),
            "conv_id": parsed_cid or self.defaults.get("conv_id", ""),
            "cache_user": self.defaults.get("cache_user", ""),
        }
        # sample_vars take highest priority (pipeline-level overrides)
        vars_.update(sample_vars)

        body = json.loads(json.dumps(self.body_template))
        self._fill_vars(body, vars_)
        headers = json.loads(json.dumps(self.headers))
        self._fill_vars(headers, vars_)
        return headers, body

    @staticmethod
    def _fill_vars(obj, vars_: dict):
        """Recursively replace {{var}} in strings within dicts/lists."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    for var_name, val in vars_.items():
                        obj[k] = obj[k].replace("{{" + var_name + "}}", str(val))
                else:
                    BaseCollector._fill_vars(v, vars_)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                if isinstance(v, str):
                    for var_name, val in vars_.items():
                        obj[i] = obj[i].replace("{{" + var_name + "}}", str(val))
                else:
                    BaseCollector._fill_vars(v, vars_)

    @staticmethod
    def _normalize_path(field_path: str) -> str:
        """
        Convert bracket notation to dot notation for glom.
        e.g. 'choices[0].delta.content' → 'choices.0.delta.content'
        """
        import re
        return re.sub(r'\[(\d+)\]', r'.\1', field_path)

    @staticmethod
    def extract_field(data: dict, field_path: str) -> str:
        """
        Extract a nested field from JSON using dot/bracket notation.
        e.g. 'choices[0].delta.content' or 'data.result'
        """
        if glom is not None:
            try:
                normalized = BaseCollector._normalize_path(field_path)
                result = glom(data, normalized)
                return str(result) if result is not None else ""
            except Exception:
                return ""
        # Fallback: simple dot-path traversal
        try:
            obj = data
            for part in field_path.replace("[0]", ".0").split("."):
                obj = obj[int(part)] if part.isdigit() else obj[part]
            return str(obj) if obj is not None else ""
        except (KeyError, IndexError, TypeError):
            return ""

    @abstractmethod
    async def collect(self, query: str, sample_vars: Optional[dict] = None) -> dict:
        """
        Call the Agent and return the collected result.

        Returns: {
            "output": str,           # Full text response
            "chunks": list,          # Stream chunks (empty for non-streaming)
            "latency_ms": int,       # Response time in milliseconds
            "error": str | None,     # Error message if failed
        }
        """
        pass

    async def test_connection(self, test_query: str = "hello") -> dict:
        """
        Quick connectivity test for the Agent endpoint.
        Returns protocol-level diagnostics.
        """
        result = await self.collect(test_query)
        return {
            "status": "online" if not result["error"] else "offline",
            "latency_ms": result["latency_ms"],
            "sample_output": result["output"][:200] if result["output"] else "",
            "sse_chunks_received": len(result.get("chunks", [])),
            "protocol_verified": not result["error"],
            "error": result["error"],
        }
