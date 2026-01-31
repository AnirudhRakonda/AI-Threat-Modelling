import streamlit as st

from core.parser import parse_system_description
from core.stride_agent import generate_stride_threats
from core.dread import enrich_with_dread
from core.attack_tree import (
    build_attack_tree,
    attack_tree_to_mermaid
)
from utils.mermaid import render_mermaid


# ---------------- UI SETUP ----------------
st.set_page_config(page_title="AI Threat Modeling", layout="wide")

st.title("AI-Powered Threat Modeling System")
st.caption("Local LLM powered | STRIDE | DREAD | Attack Trees")

system_desc = st.text_area(
    "Enter System Description",
    height=260,
    placeholder=(
        "Example: A web app with React frontend, Node.js backend, "
        "JWT authentication, MongoDB database, and admin panel..."
    )
)

# ---------------- MAIN LOGIC ----------------
if st.button("Generate Threat Model"):

    if not system_desc.strip():
        st.warning("Please enter a system description.")
        st.stop()

    with st.spinner("Analyzing threats using Mistral 7B..."):

        # 1️⃣ Parse input
        parsed_desc = parse_system_description(system_desc)

        # 2️⃣ Generate STRIDE threats (JSON)
        stride_data = generate_stride_threats(parsed_desc)

        # 3️⃣ Add DREAD scoring
        stride_data = enrich_with_dread(stride_data)

        # 4️⃣ Build attack tree from STRIDE
        root, parent_nodes, edges = build_attack_tree(stride_data)

        # 5️⃣ Convert to Mermaid
        mermaid_code = attack_tree_to_mermaid(
            root, parent_nodes, edges
        )

    # ---------------- OUTPUT ----------------
    st.subheader("STRIDE Threat Model (Structured)")

    for threat in stride_data["threats"]:
        with st.expander(
            f'{threat["id"]} | {threat["stride"]} | {threat["component"]}'
        ):
            st.write("**Description:**", threat["description"])
            st.write("**Impact:**", threat["impact"])
            st.write("**Attack Path:**", threat["attack_tree_node"])
            st.write("**DREAD Score:**", threat["dread"]["Total"])
            st.json(threat["dread"])

    st.subheader("Attack Tree (Mermaid Visualization)")
    render_mermaid(mermaid_code)
