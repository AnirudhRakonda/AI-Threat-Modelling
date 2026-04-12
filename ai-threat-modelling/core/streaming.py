"""
Token streaming utilities for real-time LLM response display.
Enables progressive token-by-token output to UI.
"""

import logging
from typing import Callable, Iterator
import requests

logger = logging.getLogger(__name__)


def query_llm_streaming(prompt: str, images: list = None, 
                        on_token: Callable = None, 
                        timeout: int = 180) -> str:
    """
    Query LLM with streaming responses for real-time token display.
    
    Args:
        prompt: The prompt to send
        images: Optional image bytes for vision
        on_token: Callback function called with each token (receives token string)
        timeout: Request timeout in seconds
    
    Returns:
        Complete response text
    """
    
    OLLAMA_URL = "http://localhost:11434/api/chat"
    MODEL_NAME = "llava"
    DEFAULT_NUM_CTX = 4096
    DEFAULT_TEMPERATURE = 0.2
    
    message = {
        "role": "user",
        "content": prompt
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [message],
        "stream": True,
        "options": {
            "num_ctx": DEFAULT_NUM_CTX,
            "temperature": DEFAULT_TEMPERATURE
        }
    }

    # Attach images if provided
    if images:
        import base64
        encoded_images = [
            base64.b64encode(img).decode("utf-8")
            for img in images
        ]
        payload["messages"][0]["images"] = encoded_images

    full_response = ""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=timeout,
            stream=True
        )
        response.raise_for_status()
        
        # Process streaming response
        for line in response.iter_lines():
            if line:
                try:
                    import json
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    
                    if token:
                        full_response += token
                        
                        # Call callback if provided
                        if on_token:
                            try:
                                on_token(token)
                            except Exception as e:
                                logger.warning(f"Callback error: {e}")
                    
                    # Check if stream is complete
                    if chunk.get("done"):
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        logger.info(f"Streaming complete. Total length: {len(full_response)} chars")
        return full_response

    except requests.exceptions.Timeout:
        error_msg = f"Streaming request timed out after {timeout}s"
        logger.error(error_msg)
        return f"LLM Error: {error_msg}"
    except requests.exceptions.ConnectionError:
        error_msg = "Failed to connect to Ollama for streaming"
        logger.error(error_msg)
        return f"LLM Error: {error_msg}"
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        return f"LLM Error: {str(e)}"
