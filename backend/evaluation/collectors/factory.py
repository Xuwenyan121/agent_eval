"""
Collector Factory - Selects the right collector based on agent protocol type.
"""

import logging
from evaluation.collectors.base import BaseCollector
from evaluation.collectors.sse_agent_collector import SSEAgentCollector
from evaluation.collectors.json_agent_collector import JSONAgentCollector
from evaluation.collectors.openai_compat_collector import OpenAICompatCollector

logger = logging.getLogger(__name__)

# Protocol → Collector class registry
_COLLECTOR_REGISTRY = {
    "http_sse": SSEAgentCollector,
    "http_json": JSONAgentCollector,
    "openai_compat": OpenAICompatCollector,
}


def get_collector(endpoint_config: dict) -> BaseCollector:
    """
    Factory function: returns the appropriate collector based on protocol.

    Args:
        endpoint_config: dict from AgentEndpoint.endpoint_config_dict()
            Must contain "protocol" key: "http_sse" | "http_json" | "openai_compat"

    Returns:
        BaseCollector subclass instance

    Raises:
        ValueError: if protocol is unknown
    """
    protocol = endpoint_config.get("protocol", "http_sse")
    collector_cls = _COLLECTOR_REGISTRY.get(protocol)

    if collector_cls is None:
        raise ValueError(
            f"Unknown protocol: '{protocol}'. "
            f"Supported: {list(_COLLECTOR_REGISTRY.keys())}"
        )

    collector = collector_cls(endpoint_config)
    logger.info("Created %s for %s (protocol=%s)", collector_cls.__name__, endpoint_config.get("endpoint_url", "?"), protocol)
    return collector


def get_supported_protocols() -> list:
    """Return list of supported protocol types."""
    return list(_COLLECTOR_REGISTRY.keys())
