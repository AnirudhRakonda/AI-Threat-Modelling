def coverage_score(stride_data: dict) -> int:
    """
    Measures how many STRIDE categories are covered.
    Max score = 6
    """
    categories = set(
        threat["stride"] for threat in stride_data.get("threats", [])
    )
    return len(categories)


def threat_count(stride_data: dict) -> int:
    return len(stride_data.get("threats", []))


def average_dread(stride_data: dict) -> float:
    threats = stride_data.get("threats", [])
    if not threats:
        return 0

    total = sum(threat["dread"]["Total"] for threat in threats)
    return round(total / len(threats), 2)


def evaluate_model(stride_data: dict) -> dict:
    """
    Returns evaluation summary.
    """
    return {
        "Threat Count": threat_count(stride_data),
        "STRIDE Coverage (max 6)": coverage_score(stride_data),
        "Average DREAD Score": average_dread(stride_data)
    }