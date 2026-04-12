import requests
import base64
import logging
import time
from core.cache import get_cached_response, cache_response
from core.resilience import CircuitBreaker, retry_with_backoff

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llava"
DEFAULT_NUM_CTX = 4096  # Increased from 1024 for better context handling
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TIMEOUT = 180

# Circuit breaker for fault tolerance
_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=60,
    name="Ollama_CircuitBreaker"
)


@retry_with_backoff(max_retries=2, initial_delay=2.0, backoff_factor=2.0)
def _make_llm_request(url: str, payload: dict, timeout: int) -> str:
    """
    Internal function to make LLM request with retry logic.
    
    Args:
        url: Ollama endpoint URL
        payload: Request payload
        timeout: Request timeout in seconds
    
    Returns:
        LLM response text
    """
    response = requests.post(
        url,
        json=payload,
        timeout=timeout
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def query_llm(prompt: str, images: list = None, use_cache: bool = True) -> str:
    """
    Unified LLaVA client using Ollama /api/chat endpoint.
    Includes caching, retry logic, and circuit breaker.
    
    Args:
        prompt: The prompt to send to LLM
        images: Optional list of image bytes
        use_cache: Whether to check/use cache (disabled for image queries)
    
    Returns:
        LLM response text
    """

    # Check cache first (only if no images)
    if use_cache and not images:
        cached = get_cached_response(prompt)
        if cached:
            logger.info("Cache hit for prompt")
            return cached

    message = {
        "role": "user",
        "content": prompt
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [message],
        "stream": False,
        "options": {
            "num_ctx": DEFAULT_NUM_CTX,
            "temperature": DEFAULT_TEMPERATURE
        }
    }

    # Attach images if provided
    if images:
        encoded_images = [
            base64.b64encode(img).decode("utf-8")
            for img in images
        ]
        payload["messages"][0]["images"] = encoded_images

    # Execute through circuit breaker with fallback
    def _query():
        return _make_llm_request(OLLAMA_URL, payload, DEFAULT_TIMEOUT)
    
    result = _circuit_breaker.call(
        _query,
        fallback="LLM Error: Circuit breaker open - service unavailable"
    )

    # Handle error response
    if isinstance(result, str) and result.startswith("LLM Error:"):
        logger.error(result)
        return result

    # Cache successful response (only if no images)
    if use_cache and not images:
        try:
            cache_response(prompt, result)
            logger.info("Cached response for future queries")
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

    return result