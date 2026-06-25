"""
Judge Model configuration for DeepEval.
DeepEval uses OpenAI-compatible endpoints via environment variables.
"""

import os
import logging

logger = logging.getLogger(__name__)


def get_judge_endpoint(config: dict) -> str:
    """
    Configure and return the judge model identifier for DeepEval.

    Sets OPENAI_API_KEY and OPENAI_API_BASE environment variables
    so DeepEval's internal LLM calls use the configured endpoint.

    Args:
        config: dict with keys:
            - model: model identifier (e.g. "gpt-4o", "deepseek-chat")
            - api_base: OpenAI-compatible API base URL
            - api_key: API key (may be encrypted; caller must decrypt)
            - judge_model_id: (optional) UUID to look up JudgeModel from DB

    Returns:
        Model identifier string for DeepEval's `model` parameter.
    """
    # If judge_model_id is provided, resolve it from the database
    judge_model_id = config.get("judge_model_id")
    if judge_model_id and not config.get("api_key"):
        try:
            from evaluation.models import JudgeModel
            jm = JudgeModel.objects.filter(id=judge_model_id, is_active=True).first()
            if jm:
                logger.info("Resolved judge_model_id %s to '%s'", judge_model_id, jm.name)
                # Merge DB values with config (config takes precedence)
                config = {
                    "model": config.get("model") or jm.model,
                    "api_base": config.get("api_base") or jm.api_base,
                    "api_key": jm.api_key,  # Use DB key
                }
            else:
                logger.warning("JudgeModel %s not found or inactive", judge_model_id)
        except Exception as e:
            logger.warning("Failed to resolve judge_model_id %s: %s", judge_model_id, e)

    api_key = config.get("api_key", "")
    api_base = config.get("api_base", "")
    model = config.get("model", "gpt-4o")

    if api_key:
        # Decrypt if encrypted (Fernet in production, plain for dev)
        try:
            from evaluation.utils import decrypt_key
            decrypted = decrypt_key(api_key)
        except (ImportError, Exception):
            decrypted = api_key
        os.environ["OPENAI_API_KEY"] = decrypted

    if api_base:
        # OpenAI client requires /v1 suffix for non-OpenAI providers
        # (e.g., DeepSeek, Qwen, etc.)
        if not api_base.rstrip("/").endswith("/v1"):
            api_base = api_base.rstrip("/") + "/v1"
            logger.info("Appended /v1 to api_base for OpenAI client compatibility")
        os.environ["OPENAI_API_BASE"] = api_base

    logger.info("Judge model configured: %s at %s", model, api_base or "default OpenAI")
    return model


def get_judge_model_instance(config: dict):
    """
    Create and return a DeepEval-compatible GPTModel instance.

    This is preferred over get_judge_endpoint() as it explicitly configures
    the model with api_key and base_url, avoiding environment variable issues.

    Args:
        config: dict with model, api_base, api_key, judge_model_id

    Returns:
        A GPTModel instance configured for the judge endpoint.
    """
    from deepeval.models.llms.openai_model import GPTModel

    # Resolve judge_model_id if provided
    judge_model_id = config.get("judge_model_id")
    if judge_model_id and not config.get("api_key"):
        try:
            from evaluation.models import JudgeModel
            jm = JudgeModel.objects.filter(id=judge_model_id, is_active=True).first()
            if jm:
                logger.info("Resolved judge_model_id %s for model instance", judge_model_id)
                config = {
                    "model": config.get("model") or jm.model,
                    "api_base": config.get("api_base") or jm.api_base,
                    "api_key": jm.api_key,
                }
        except Exception as e:
            logger.warning("Failed to resolve judge_model_id: %s", e)

    api_key = config.get("api_key", "")
    api_base = config.get("api_base", "")
    model_name = config.get("model", "gpt-4o")

    # Decrypt API key if needed
    if api_key:
        try:
            from evaluation.utils import decrypt_key
            api_key = decrypt_key(api_key)
        except (ImportError, Exception):
            pass

    # Ensure base_url has /v1 suffix for OpenAI client compatibility
    if api_base and not api_base.rstrip("/").endswith("/v1"):
        api_base = api_base.rstrip("/") + "/v1"

    logger.info("Creating GPTModel instance: %s at %s", model_name, api_base)

    return GPTModel(
        model=model_name,
        api_key=api_key,
        base_url=api_base if api_base else None,
    )
