"""
Context management and token estimation utilities.
Prevents context truncation and provides warnings.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Rough token estimation: 1 token ≈ 4 characters (for English)
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """
    Rough estimate of token count for text.
    
    Uses simple heuristic: 1 token ≈ 4 characters
    For accurate counts, use a tokenizer library (optional future improvement).
    
    Args:
        text: Input text
    
    Returns:
        Estimated token count
    """
    return len(text) // CHARS_PER_TOKEN


def estimate_prompt_tokens(system_description: str, 
                           vision_context: str = "",
                           prompt_template: str = "") -> dict:
    """
    Estimate total tokens for a complete prompt.
    
    Args:
        system_description: The system description text
        vision_context: Optional extracted vision context
        prompt_template: The prompt template (e.g., STRIDE prompt)
    
    Returns:
        Dict with token estimates:
        {
            "system_tokens": int,
            "vision_tokens": int,
            "template_tokens": int,
            "total_tokens": int,
            "available_context": int,
            "warning": str or None
        }
    """
    
    MAX_CONTEXT = 4096
    RESERVE_FOR_OUTPUT = 1024  # Reserve tokens for response
    
    system_tokens = estimate_tokens(system_description)
    vision_tokens = estimate_tokens(vision_context)
    template_tokens = estimate_tokens(prompt_template)
    
    total_tokens = system_tokens + vision_tokens + template_tokens
    available_for_output = MAX_CONTEXT - total_tokens
    
    warning = None
    if total_tokens > MAX_CONTEXT * 0.8:  # 80% threshold
        warning = f"⚠️ Context usage high: {total_tokens}/{MAX_CONTEXT} tokens (80%+ utilization). System description may be truncated."
        logger.warning(warning)
    elif available_for_output < RESERVE_FOR_OUTPUT:
        warning = f"⚠️ Limited output space: Only {available_for_output} tokens available for LLM response. May truncate threats."
        logger.warning(warning)
    
    return {
        "system_tokens": system_tokens,
        "vision_tokens": vision_tokens,
        "template_tokens": template_tokens,
        "total_tokens": total_tokens,
        "available_context": available_for_output,
        "max_context": MAX_CONTEXT,
        "warning": warning
    }


def truncate_to_context(text: str, max_tokens: int = 3000) -> tuple:
    """
    Truncate text to fit within context window.
    
    Args:
        text: Input text
        max_tokens: Maximum tokens to keep
    
    Returns:
        Tuple of (truncated_text, was_truncated)
    """
    
    max_chars = max_tokens * CHARS_PER_TOKEN
    
    if len(text) <= max_chars:
        return text, False
    
    # Truncate and add ellipsis
    truncated = text[:max_chars] + "\n... [truncated]"
    logger.warning(f"Text truncated from {len(text)} to {len(truncated)} chars")
    
    return truncated, True


def estimate_threat_response_tokens(threat_count: int) -> int:
    """
    Estimate tokens needed for STRIDE threat response.
    Base: ~150 tokens per threat + 50 for JSON structure.
    
    Args:
        threat_count: Expected number of threats
    
    Returns:
        Estimated tokens
    """
    BASE_TOKENS = 50
    TOKENS_PER_THREAT = 150
    
    return BASE_TOKENS + (threat_count * TOKENS_PER_THREAT)


def estimate_dread_response_tokens(threat_count: int) -> int:
    """
    Estimate tokens needed for DREAD scoring response.
    Base: ~30 tokens per threat + 20 for JSON structure.
    
    Args:
        threat_count: Number of threats to score
    
    Returns:
        Estimated tokens
    """
    BASE_TOKENS = 20
    TOKENS_PER_THREAT = 30
    
    return BASE_TOKENS + (threat_count * TOKENS_PER_THREAT)
