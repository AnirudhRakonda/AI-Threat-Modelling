def calculate_dread(threat: dict) -> dict:
    """
    Simple deterministic DREAD scoring.
    Replaceable later with LLM-assisted or learned model.
    """

    stride_base_score = {
        "Spoofing": 3,
        "Tampering": 4,
        "Repudiation": 2,
        "Information Disclosure": 4,
        "Denial of Service": 3,
        "Elevation of Privilege": 5
    }

    base = stride_base_score.get(threat.get("stride"), 3)

    dread = {
        "Damage": base,
        "Reproducibility": base,
        "Exploitability": base,
        "AffectedUsers": base,
        "Discoverability": base
    }

    dread["Total"] = sum(dread.values())
    return dread


def enrich_with_dread(stride_data: dict) -> dict:
    for threat in stride_data.get("threats", []):
        threat["dread"] = calculate_dread(threat)
    return stride_data
