import json
from llm.llm_client import query_llm


def calculate_dread_batch(stride_data: dict) -> dict:
    threats = stride_data.get("threats", [])

    if not threats:
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

    with open("prompts/dread_batch.txt", "r") as f:
        prompt_template = f.read()

    prompt = prompt_template.replace("{threat_list}", threat_text)

    response = query_llm(prompt)

    try:
        dread_scores = json.loads(response)
    except json.JSONDecodeError:
        # Fallback deterministic scoring
        for threat in threats:
            threat["dread"] = {
                "Damage": 3,
                "Reproducibility": 3,
                "Exploitability": 3,
                "AffectedUsers": 3,
                "Discoverability": 3,
                "Total": 15
            }
        return stride_data

    # Attach scores to threats
    for threat in threats:
        tid = threat["id"]

        if tid in dread_scores:
            scores = dread_scores[tid]

            # Clamp values 1–5
            for key in scores:
                scores[key] = max(1, min(5, int(scores[key])))

            scores["Total"] = sum(scores.values())
            threat["dread"] = scores
        else:
            # fallback if missing
            threat["dread"] = {
                "Damage": 3,
                "Reproducibility": 3,
                "Exploitability": 3,
                "AffectedUsers": 3,
                "Discoverability": 3,
                "Total": 15
            }

    return stride_data