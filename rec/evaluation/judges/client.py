"""
Unified LLM Client using LiteLLM

Provides async multi-provider support for LLM-based evaluation.
Supports OpenAI, Gemini, and Anthropic through a unified interface.

Usage:
    from evaluation.judges.client import call_llm, get_available_providers
    
    # Single call
    result = await call_llm(
        provider="openai",
        prompt="Evaluate this recommendation...",
        temperature=0.8
    )
    
    # Check available providers (based on API keys)
    providers = get_available_providers()
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

import litellm
from litellm import acompletion

# Suppress LiteLLM's verbose logging
litellm.suppress_debug_info = True

# Drop unsupported params for models with restrictions (e.g., gpt-5 only supports temp=1)
litellm.drop_params = True


# ============================================================================
# Model Configuration
# ============================================================================

SUPPORTED_MODELS: Dict[str, str] = {
    "openai": "gpt-5-mini",
    "gemini": "gemini/gemini-2.5-flash",
    "anthropic": "claude-sonnet-4-5"
}

# Environment variable names for API keys
API_KEY_ENV_VARS: Dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY"
}


# ============================================================================
# Provider Availability
# ============================================================================

def get_available_providers() -> List[str]:
    """
    Get list of providers with valid API keys configured.
    
    Returns:
        List of provider names (e.g., ["openai", "gemini"])
    """
    available = []
    for provider, env_var in API_KEY_ENV_VARS.items():
        if os.getenv(env_var):
            available.append(provider)
    return available


def is_provider_available(provider: str) -> bool:
    """Check if a specific provider has an API key configured."""
    env_var = API_KEY_ENV_VARS.get(provider)
    return bool(env_var and os.getenv(env_var))


def get_model_for_provider(provider: str) -> str:
    """
    Get the model identifier for a provider.
    
    Args:
        provider: One of "openai", "gemini", "anthropic"
    
    Returns:
        Model identifier string for LiteLLM
    
    Raises:
        ValueError: If provider is not supported
    """
    model = SUPPORTED_MODELS.get(provider)
    if not model:
        raise ValueError(f"Unsupported provider: {provider}. "
                        f"Supported: {list(SUPPORTED_MODELS.keys())}")
    return model


# ============================================================================
# JSON Parsing
# ============================================================================

def parse_json_response(content: str) -> Dict[str, Any]:
    """
    Parse JSON from LLM response, handling various formats.
    
    LLMs may return JSON in different formats:
    - Direct JSON object
    - JSON wrapped in markdown code blocks
    - JSON with surrounding text
    
    Args:
        content: Raw LLM response text
    
    Returns:
        Parsed JSON as dictionary
    
    Raises:
        ValueError: If no valid JSON found
    """
    content = content.strip()
    
    # Try direct JSON parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code block
    match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try finding any JSON object
    match = re.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not parse JSON from response: {content[:200]}...")


# ============================================================================
# LLM API Calls
# ============================================================================

async def call_llm(
    provider: str,
    prompt: str,
    temperature: float = 0.8,
    response_schema: Optional[Dict[str, str]] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Call LLM provider with prompt and return parsed JSON response.
    
    Uses LiteLLM for unified multi-provider support with async execution.
    
    Args:
        provider: One of "openai", "gemini", "anthropic"
        prompt: The evaluation prompt
        temperature: Sampling temperature (default 0.8, research-backed)
        response_schema: Expected response structure (for validation, optional)
        timeout: Request timeout in seconds
    
    Returns:
        Parsed JSON response from LLM (typically {"score": float, "reasoning": str})
    
    Raises:
        ValueError: If provider is not supported or response parsing fails
        Exception: If LLM API call fails
    """
    model = get_model_for_provider(provider)
    
    # Check if API key is available
    if not is_provider_available(provider):
        raise ValueError(f"No API key configured for {provider}. "
                        f"Set {API_KEY_ENV_VARS[provider]} environment variable.")
    
    # Build messages
    messages = [{"role": "user", "content": prompt}]
    
    # Call LLM via LiteLLM
    response = await acompletion(
        model=model,
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
        timeout=timeout
    )
    
    # Extract content
    content = response.choices[0].message.content
    
    # Parse JSON response
    result = parse_json_response(content)
    
    # Validate schema if provided
    if response_schema:
        _validate_response_schema(result, response_schema)
    
    return result


def _validate_response_schema(result: Dict[str, Any], schema: Dict[str, str]) -> None:
    """
    Validate that response contains expected fields.
    
    Args:
        result: Parsed JSON response
        schema: Expected field types (e.g., {"score": "number", "reasoning": "string"})
    
    Raises:
        ValueError: If required fields are missing or wrong type
    """
    for field, expected_type in schema.items():
        if field not in result:
            raise ValueError(f"Response missing required field: {field}")
        
        value = result[field]
        
        # Type validation
        if expected_type == "number":
            if not isinstance(value, (int, float)):
                raise ValueError(f"Field '{field}' expected number, got {type(value).__name__}")
        elif expected_type == "string":
            if not isinstance(value, str):
                raise ValueError(f"Field '{field}' expected string, got {type(value).__name__}")
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"Field '{field}' expected boolean, got {type(value).__name__}")


async def call_llm_batch(
    provider: str,
    prompts: List[str],
    temperature: float = 0.8,
    response_schema: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Call LLM provider with multiple prompts in parallel.
    
    Args:
        provider: One of "openai", "gemini", "anthropic"
        prompts: List of evaluation prompts
        temperature: Sampling temperature
        response_schema: Expected response structure
    
    Returns:
        List of parsed JSON responses (or exception objects for failures)
    """
    import asyncio
    
    tasks = [
        call_llm(provider, prompt, temperature, response_schema)
        for prompt in prompts
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "call_llm",
    "call_llm_batch",
    "get_available_providers",
    "is_provider_available",
    "get_model_for_provider",
    "parse_json_response",
    "SUPPORTED_MODELS",
    "API_KEY_ENV_VARS"
]
