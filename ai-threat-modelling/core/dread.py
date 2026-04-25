import json
import re
import logging
import os
from llm.llm_client import query_llm

logger = logging.getLogger(__name__)


def extract_dread_json(text: str) -> dict:
    """
    Robustly extracts DREAD scores JSON from LLM output.
    
    Uses json.JSONDecoder().raw_decode() for safety.
    Handles markdown fences and extra text.
    
    Returns:
        Parsed DREAD scores dict
    """
    if not text:
        raise ValueError("Empty DREAD response from LLM")
    
    text = text.strip()
    
    # Remove markdown code fences
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    
    # Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try raw_decode from first { position
    for i, char in enumerate(text):
        if char == '{':
            try:
                decoder = json.JSONDecoder()
                obj, idx = decoder.raw_decode(text[i:])
                logger.info(f"Extracted DREAD JSON from position {i}")
                return obj
            except json.JSONDecodeError:
                continue
    
    raise ValueError("No valid DREAD JSON found in response")


def calculate_dread_batch(stride_data: dict) -> dict:
    """
    Batch calculates DREAD scores for all threats.
    
    Args:
        stride_data: Dict with threats from STRIDE phase
    
    Returns:
        Updated stride_data with DREAD scores attached
    """
    threats = stride_data.get("threats", [])

    if not threats:
        logger.warning("No threats to score")
        return stride_data

    # Build threat list text for prompt
    threat_text = ""
    for threat in threats:
        threat_text += (
            f'ID: {threat["id"]}\n'
            f'Component: {threat.get("component","")}\n'
            f'STRIDE: {threat.get("stride","")}\n'
            f'Description: {threat.get("description","")}\n'
            f'Impact: {threat.get("impact","")}\n\n'
        )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "..", "prompts", "dread_batch.txt")
    with open(prompt_path, "r") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{threat_list}", threat_text)

    logger.info(f"Sending DREAD scoring request for {len(threats)} threats...")
    response = query_llm(prompt)

    try:
        dread_scores = extract_dread_json(response)
        logger.info(f"Successfully parsed DREAD scores")
    except ValueError as e:
        logger.warning(f"DREAD JSON parsing failed: {str(e)}. Using fallback scores.")
        logger.debug(f"Raw DREAD response (first 500 chars): {response[:500]}")
        
        # Fallback: assign neutral scores to all threats
        for threat in threats:
            threat["dread"] = {
                "Damage": 3,
                "Reproducibility": 3,
                "Exploitability": 3,
                "AffectedUsers": 3,
                "Discoverability": 3,
                "Total": 15
            }
        
        logger.warning("Applied default DREAD scores (all 3s)")
        return stride_data

    # Attach scores to threats
    for threat in threats:
        tid = threat["id"]

        if tid in dread_scores:
            scores = dread_scores[tid]

            # Clamp values 1–5 and ensure integers
            for key in ["Damage", "Reproducibility", "Exploitability", "AffectedUsers", "Discoverability"]:
                if key in scores:
                    try:
                        scores[key] = max(1, min(5, int(scores[key])))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid DREAD score for {tid}.{key}: {scores[key]}, using 3")
                        scores[key] = 3
                else:
                    logger.warning(f"Missing DREAD factor {key} for threat {tid}, using 3")
                    scores[key] = 3

            scores["Total"] = sum([scores.get(k, 3) for k in ["Damage", "Reproducibility", "Exploitability", "AffectedUsers", "Discoverability"]])
            threat["dread"] = scores
        else:
            # Fallback if threat ID not in response
            logger.warning(f"Threat {tid} not in DREAD response, using defaults")
            threat["dread"] = {
                "Damage": 3,
                "Reproducibility": 3,
                "Exploitability": 3,
                "AffectedUsers": 3,
                "Discoverability": 3,
                "Total": 15
            }

    return stride_data