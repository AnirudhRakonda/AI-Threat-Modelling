import requests
import base64

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llava"


def query_llm(prompt: str, images: list = None) -> str:
    """
    Unified LLaVA client using Ollama /api/chat endpoint.
    """

    message = {
        "role": "user",
        "content": prompt
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [message],
        "stream": False,
        "options": {
            "num_ctx": 1024,
            "temperature": 0.2
        }
    }

    # Attach images if provided
    if images:
        encoded_images = [
            base64.b64encode(img).decode("utf-8")
            for img in images
        ]
        payload["messages"][0]["images"] = encoded_images

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    except Exception as e:
        return f"LLM Error: {str(e)}"