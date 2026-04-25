import json
import re
import logging
import os
from llm.llm_client import query_llm

logger = logging.getLogger(__name__)


def extract_json_from_response(text: str) -> dict:
    """
    Robustly extracts first valid JSON object from LLM output.
    
    Handles:
    - Markdown code fences (```json ... ```)
    - Extra explanation text before/after JSON
    - Malformed JSON attempts
    
    Returns:
        Parsed JSON dict
        
    Raises:
        ValueError: If no valid JSON can be extracted
    """

    if not text:
        raise ValueError("Empty response from LLM")

    text = text.strip()

    # Remove markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)

    # Try direct parsing first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON using raw_decode (safer than regex)
    # This finds the first valid JSON object without regex risks
    for i, char in enumerate(text):
        if char == '{':
            try:
                decoder = json.JSONDecoder()
                obj, idx = decoder.raw_decode(text[i:])
                logger.info(f"Extracted JSON from position {i}")
                return obj
            except json.JSONDecodeError:
                continue
    
    # Fallback: extract with regex as last resort
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("No valid JSON object found in LLM response")


def validate_stride_structure(data: dict) -> None:
    """
    Ensures LLM returned expected STRIDE structure.
    
    Raises:
        ValueError: If structure is invalid
    """

    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data).__name__}")

    if "threats" not in data:
        raise ValueError("Missing 'threats' key in STRIDE output")

    if not isinstance(data["threats"], list):
        raise ValueError(f"'threats' must be a list, got {type(data['threats']).__name__}")

    if not data["threats"]:
        logger.warning("STRIDE output returned empty threats list")

    required_fields = {
        "id",
        "component",
        "stride",
        "description",
        "impact",
        "attack_tree_node"
    }

    for i, threat in enumerate(data["threats"]):
        if not isinstance(threat, dict):
            raise ValueError(f"Threat {i} is not a dict: {type(threat).__name__}")
        
        missing = required_fields - threat.keys()
        if missing:
            raise ValueError(f"Threat {i} missing fields: {missing}")


def generate_stride_threats(system_description: str) -> dict:
    """
    Generates structured STRIDE threats using LLaVA.
    
    Args:
        system_description: Text description of the system
    
    Returns:
        Validated dict with threat data
        
    Raises:
        ValueError: If LLM output cannot be parsed or validated
    """

    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "..", "prompts", "stride.txt")
    with open(prompt_path, "r") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{system}", system_description)

    logger.info("Sending STRIDE generation request to LLM...")
    response = query_llm(prompt)

    try:
        stride_data = extract_json_from_response(response)
        validate_stride_structure(stride_data)
        logger.info(f"Successfully generated {len(stride_data['threats'])} threats")
    except ValueError as e:
        logger.error(f"STRIDE parsing failed: {str(e)}")
        logger.debug(f"Raw LLM response (first 500 chars): {response[:500]}")
        raise ValueError(f"STRIDE LLM output is not valid JSON structure: {str(e)}") from e

    return stride_data