import streamlit as st
import json
import os
import pandas as pd

from core.parser import parse_system_description
from core.stride_agent import generate_stride_threats
from core.dread import calculate_dread_batch
from core.attack_tree import build_attack_tree, attack_tree_to_mermaid
from core.evaluation import evaluate_model
from utils.mermaid import render_mermaid
from llm.llm_client import query_llm


# ---------------- UI SETUP ----------------
st.set_page_config(page_title="AI Threat Modeling", layout="wide")

st.title("AI-Powered Threat Modeling System")
st.caption("Unified Multimodal LLaVA | STRIDE | DREAD | Attack Trees | Evaluation")


# ---------------- LOAD BENCHMARK TEST CASES ----------------
test_cases = []
if os.path.exists("data/test_cases.json"):
    with open("data/test_cases.json", "r") as f:
        test_cases = json.load(f)

selected_case = None
if test_cases:
    case_names = [case["name"] for case in test_cases]
    selected_name = st.selectbox(
        "Select Benchmark Test System (optional):",
        ["Custom Input"] + case_names
    )

    if selected_name != "Custom Input":
        selected_case = next(
            case for case in test_cases if case["name"] == selected_name
        )


# ---------------- TEXT INPUT ----------------
system_desc = st.text_area(
    "Enter System Description",
    height=220,
    value=selected_case["description"] if selected_case else "",
    placeholder="Describe your system architecture..."
)


# ---------------- IMAGE INPUT ----------------
uploaded_image = st.file_uploader(
    "Upload Architecture Diagram (optional)",
    type=["png", "jpg", "jpeg"]
)


# ---------------- MAIN EXECUTION ----------------
if st.button("Generate Threat Model"):

    if not system_desc.strip() and not uploaded_image:
        st.warning("Please provide a system description or upload an architecture diagram.")
        st.stop()

    with st.spinner("Processing input..."):

        # Step 1: Parse text
        parsed_desc = parse_system_description(system_desc)

        # Step 2: Vision processing if image exists
        image_context = ""
        if uploaded_image:
            with st.spinner("Analyzing architecture diagram with LLaVA..."):
                image_bytes = uploaded_image.read()

                vision_prompt = """
You are a cybersecurity architect.

Analyze this software architecture diagram.
Extract:
- Main components
- Technologies
- Data flows
- External interfaces
- Trust boundaries

Be structured and concise.
"""
                image_context = query_llm(
                    vision_prompt,
                    images=[image_bytes]
                )

                st.subheader("Extracted Architecture Context")
                st.write(image_context)

        # Step 3: Combine context
        combined_context = parsed_desc

        if image_context:
            combined_context += "\n\nArchitecture Details Extracted From Diagram:\n"
            combined_context += image_context

        # Step 4: STRIDE generation
        stride_data = generate_stride_threats(combined_context)

        # Step 5: Batch DREAD scoring
        stride_data = calculate_dread_batch(stride_data)

        # Step 6: Attack tree build
        root, parent_nodes, edges = build_attack_tree(stride_data)

        # Step 7: Mermaid conversion
        mermaid_code = attack_tree_to_mermaid(
            root, parent_nodes, edges
        )

        # Step 8: Evaluation metrics
        evaluation_results = evaluate_model(stride_data)

    # ---------------- STRIDE OUTPUT ----------------
    st.subheader("STRIDE Threat Model")

    for threat in stride_data["threats"]:
        with st.expander(
            f'{threat["id"]} | {threat["stride"]} | {threat["component"]}'
        ):
            st.write("**Description:**", threat["description"])
            st.write("**Impact:**", threat["impact"])
            st.write("**Attack Path:**", threat["attack_tree_node"])
            st.write("**DREAD Score:**", threat["dread"]["Total"])
            st.json(threat["dread"])

    # ---------------- ATTACK TREE ----------------
    st.subheader("Attack Tree Visualization")
    render_mermaid(mermaid_code)

    # ---------------- EVALUATION ----------------
    st.subheader("Evaluation Metrics")

    eval_df = pd.DataFrame(
        evaluation_results.items(),
        columns=["Metric", "Value"]
    )

    st.table(eval_df)

    # ---------------- EXPORT SECTION ----------------
    st.subheader("Export Report")

    # JSON Export
    st.download_button(
        label="Download JSON Report",
        data=json.dumps(stride_data, indent=2),
        file_name="threat_model.json",
        mime="application/json"
    )

    # Markdown Export
    def generate_markdown_report(stride_data):
        report = "# Threat Model Report\n\n"

        for t in stride_data["threats"]:
            report += f"## {t['id']} - {t['stride']}\n"
            report += f"- Component: {t['component']}\n"
            report += f"- Description: {t['description']}\n"
            report += f"- Impact: {t['impact']}\n"
            report += f"- Attack Path: {t['attack_tree_node']}\n"
            report += f"- DREAD Score: {t['dread']['Total']}\n\n"

        return report

    md_report = generate_markdown_report(stride_data)

    st.download_button(
        label="Download Markdown Report",
        data=md_report,
        file_name="threat_model.md",
        mime="text/markdown"
    )