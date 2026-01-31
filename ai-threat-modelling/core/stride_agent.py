import json
from llm.mistral_client import query_mistral

def generate_stride_threats(system_description: str) -> dict:
    with open("prompts/stride.txt", "r") as f:
        prompt_template = f.read()

    # SAFE replacement (only replaces {system})
    prompt = prompt_template.replace("{system}", system_description)

    response = query_mistral(prompt)

    try:
        stride_data = json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError("STRIDE LLM output is not valid JSON") from e

    return stride_data
