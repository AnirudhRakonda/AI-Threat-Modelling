import re

# ---------------- STRIDE COLOR MAPPING ----------------
STRIDE_COLORS = {
    "Spoofing": "#ffcccc",
    "Tampering": "#ffe0b3",
    "Repudiation": "#e6e6e6",
    "Information Disclosure": "#cce5ff",
    "Denial of Service": "#ffd6cc",
    "Elevation of Privilege": "#ffb3b3"
}


# ---------------- MERMAID SAFE ID ----------------
def safe_id(text: str) -> str:
    """
    Convert any text into a Mermaid-safe node ID.
    Mermaid node IDs must contain ONLY letters, numbers, and underscores.
    """
    return re.sub(r"[^a-zA-Z0-9_]", "_", text)


# ---------------- BUILD ATTACK TREE ----------------
def build_attack_tree(stride_data: dict):
    """
    Builds attack tree structure from STRIDE threats.
    Returns:
    - root label
    - parent_nodes: {attack_node: stride_type}
    - edges: list of (parent_node, threat_dict)
    """
    root = "Breach and Compromise System"

    parent_nodes = {}
    edges = []

    for threat in stride_data.get("threats", []):
        parent = threat["attack_tree_node"]
        parent_nodes[parent] = threat["stride"]
        edges.append((parent, threat))

    return root, parent_nodes, edges


# ---------------- MERMAID GENERATION ----------------
def attack_tree_to_mermaid(root: str, parent_nodes: dict, edges: list) -> str:
    lines = ["graph TD"]

    # Root node (fixed ID)
    lines.append(f'root["{root}"]')
    lines.append("style root fill:#ffffff,stroke:#000,stroke-width:2px")

    # Parent attack nodes
    for parent, stride in parent_nodes.items():
        pid = safe_id(parent)
        color = STRIDE_COLORS.get(stride, "#ffffff")

        lines.append(f'{pid}["{parent}"]')
        lines.append(f'root --> {pid}')
        lines.append(f'style {pid} fill:{color},stroke:#333')

    # Leaf STRIDE threat nodes
    for parent, threat in edges:
        pid = safe_id(parent)
        tid = safe_id(threat["id"])

        label = (
            f'{threat["id"]} | {threat["stride"]} | '
            f'DREAD {threat["dread"]["Total"]}'
        )

        lines.append(f'{tid}["{label}"]')
        lines.append(f'{pid} --> {tid}')

    return "\n".join(lines)
