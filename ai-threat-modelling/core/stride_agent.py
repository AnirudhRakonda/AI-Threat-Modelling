import json
import re
from llm.llm_client import query_llm


def extract_json_from_response(text: str) -> str:
    """
    Extracts the first valid JSON object from LLM output.
    Handles markdown fences and extra explanation text.
    """

    if not text:
        raise ValueError("Empty response from LLM")

    text = text.strip()

    # Remove markdown code fences if present
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)

    # Try direct parsing first
    try:
        json.loads(text)
        return text
    except:
        pass

    # Extract first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)

    raise ValueError("No valid JSON object found in LLM response")


def validate_stride_structure(data: dict) -> None:
    """
    Ensures LLM returned expected STRIDE structure.
    """

    if "threats" not in data:
        raise ValueError("Missing 'threats' key in STRIDE output")

    if not isinstance(data["threats"], list):
        raise ValueError("'threats' must be a list")

    required_fields = {
        "id",
        "component",
        "stride",
        "description",
        "impact",
        "attack_tree_node"
    }

    for threat in data["threats"]:
        missing = required_fields - threat.keys()
        if missing:
            raise ValueError(f"Missing fields in threat: {missing}")


def generate_stride_threats(system_description: str) -> dict:
    """
    Generates structured STRIDE threats using LLaVA.
    Returns validated JSON dict.
    """

    with open("prompts/stride.txt", "r") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{system}", system_description)

    response = query_llm(prompt)

    try:
        clean_json = extract_json_from_response(response)
        stride_data = json.loads(clean_json)
        validate_stride_structure(stride_data)
    except Exception as e:
        raise ValueError("STRIDE LLM output is not valid JSON structure") from e

    return stride_data