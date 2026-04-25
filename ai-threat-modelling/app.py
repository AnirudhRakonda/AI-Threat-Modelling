import streamlit as st
import json
import os
import pandas as pd
import logging
import time

from core.parser import parse_system_description
from core.stride_agent import generate_stride_threats
from core.dread import calculate_dread_batch
from core.attack_tree import build_attack_tree, attack_tree_to_mermaid
from core.evaluation import evaluate_model
from core.concurrent import run_parallel_tasks
from core.context_manager import estimate_prompt_tokens, truncate_to_context, estimate_threat_response_tokens
from core.metrics import MetricsCollector, export_metrics_json, export_metrics_csv
from utils.mermaid import render_mermaid
from llm.llm_client import query_llm

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize metrics collector in session state
if "metrics" not in st.session_state:
    st.session_state.metrics = None

# Initialize metrics
metrics_collector = MetricsCollector() if st.session_state.metrics is None else st.session_state.metrics

# ---------------- UI SETUP ----------------
st.set_page_config(page_title="AI Threat Modeling", layout="wide")

st.title("AI-Powered Threat Modeling System")
st.caption("Unified Multimodal LLaVA | STRIDE | DREAD | Attack Trees | ⚡ Phase 2: Streaming & Monitoring")


# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    
    enable_metrics = st.checkbox("Enable Metrics Collection", value=True, help="Track latency, tokens, and errors")
    enable_context_warnings = st.checkbox("Context Warnings", value=True, help="Warn when approaching context limits")
    
    if st.button("View Metrics Summary"):
        from core.metrics import get_metrics_summary
        summary = get_metrics_summary()
        st.json(summary)
    
    if st.button("Clear Cache"):
        from core.cache import clear_cache
        clear_cache()
        st.success("Cache cleared!")


# ---------------- LOAD BENCHMARK TEST CASES ----------------
test_cases = []
data_path = os.path.join(SCRIPT_DIR, "data", "test_cases.json")
if os.path.exists(data_path):
    with open(data_path, "r") as f:
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


# Helper functions for parallel execution
def vision_analysis(image_bytes: bytes) -> str:
    """Analyze architecture diagram using vision model."""
    metrics_collector.start_phase("Vision Analysis")
    
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
    result = query_llm(vision_prompt, images=[image_bytes])
    
    metrics_collector.end_phase("Vision Analysis", 
                               vision_context_length=len(result))
    return result


def stride_generation(description: str) -> dict:
    """Generate STRIDE threats from system description."""
    metrics_collector.start_phase("STRIDE Generation")
    
    result = generate_stride_threats(description)
    
    threat_count = len(result.get("threats", []))
    metrics_collector.end_phase("STRIDE Generation", 
                               threat_count=threat_count)
    
    return result


# ---------------- MAIN EXECUTION ----------------
if st.button("Generate Threat Model"):

    if not system_desc.strip() and not uploaded_image:
        st.warning("Please provide a system description or upload an architecture diagram.")
        st.stop()

    # Reset metrics for this run
    metrics_collector = MetricsCollector()
    st.session_state.metrics = metrics_collector

    with st.spinner("Generating threat model..."):
        start_time = time.time()

        # Step 1: Parse text
        metrics_collector.start_phase("Parsing")
        parsed_desc = parse_system_description(system_desc)
        metrics_collector.end_phase("Parsing", input_length=len(system_desc))

        # Step 2: Context validation & warnings
        if enable_context_warnings:
            prompt_path = os.path.join(SCRIPT_DIR, "prompts", "stride.txt")
            with open(prompt_path, "r") as f:
                prompt_template = f.read()
            
            image_context = ""
            if uploaded_image:
                image_context = ""  # Placeholder, will be populated if vision runs
            
            token_estimate = estimate_prompt_tokens(
                parsed_desc, 
                image_context,
                prompt_template
            )
            
            if token_estimate["warning"]:
                st.warning(token_estimate["warning"])
                logger.warning(token_estimate["warning"])

        # Step 3 & 4: Vision processing (if image exists) and STRIDE generation - RUN IN PARALLEL
        parallel_tasks = []
        image_context = ""
        
        if uploaded_image:
            image_bytes = uploaded_image.read()
            parallel_tasks.append((vision_analysis, (image_bytes,), "vision"))
        
        parallel_tasks.append((stride_generation, (parsed_desc,), "stride"))
        
        # Execute parallel tasks
        if parallel_tasks:
            parallel_results = run_parallel_tasks(parallel_tasks)
            
            if "vision" in parallel_results:
                image_context = parallel_results["vision"]
                if image_context:
                    st.info("✓ Architecture diagram analyzed and context extracted")
            
            if "stride" not in parallel_results or parallel_results["stride"] is None:
                st.error("Failed to generate STRIDE threats")
                metrics_collector.record_error("STRIDE_GENERATION_FAILED", "No stride data returned")
                st.stop()
            
            stride_data = parallel_results["stride"]
        else:
            stride_data = stride_generation(parsed_desc)

        # Step 4: Combine context
        combined_context = parsed_desc
        if image_context:
            combined_context += "\n\nArchitecture Details Extracted From Diagram:\n"
            combined_context += image_context

        # Show extracted architecture if available
        if image_context:
            st.subheader("Extracted Architecture Context")
            st.write(image_context)

        # Step 5: Batch DREAD scoring
        metrics_collector.start_phase("DREAD Scoring")
        stride_data = calculate_dread_batch(stride_data)
        metrics_collector.end_phase("DREAD Scoring", threats_scored=len(stride_data.get("threats", [])))

        # Step 6: Attack tree build
        metrics_collector.start_phase("Attack Tree Generation")
        root, parent_nodes, edges = build_attack_tree(stride_data)
        metrics_collector.end_phase("Attack Tree Generation", tree_nodes=len(edges))

        # Step 7: Mermaid conversion
        metrics_collector.start_phase("Mermaid Visualization")
        mermaid_code = attack_tree_to_mermaid(root, parent_nodes, edges)
        metrics_collector.end_phase("Mermaid Visualization")

        # Step 8: Evaluation metrics
        metrics_collector.start_phase("Model Evaluation")
        evaluation_results = evaluate_model(stride_data)
        metrics_collector.end_phase("Model Evaluation", stride_coverage=evaluation_results.get("STRIDE Coverage (max 6)"))
        
        # Record final metrics
        elapsed = time.time() - start_time
        metrics_collector.record_metric("total_runtime_seconds", round(elapsed, 2))
        metrics_collector.record_metric("threat_count", len(stride_data.get("threats", [])))
        
        st.success(f"✓ Threat model generated in {elapsed:.1f} seconds")

    # Save metrics
    if enable_metrics:
        metrics_data = metrics_collector.get_metrics()
        try:
            export_metrics_json(metrics_data)
            export_metrics_csv(metrics_data)
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

    # Get summary for display
    summary = metrics_collector.get_summary()
    
    # Display metrics
    with st.expander("📊 Performance Metrics"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Runtime", f"{summary['total_runtime_seconds']}s")
        with col2:
            st.metric("Phases", summary['phases_completed'])
        with col3:
            st.metric("Errors", summary['errors'])
        with col4:
            st.metric("Threats", summary['threat_count'])
        
        st.json(metrics_collector.get_metrics().get("phases", {}))

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
    
    # Export metrics
    if enable_metrics:
        metrics_json = json.dumps(metrics_collector.get_metrics(), indent=2)
        st.download_button(
            label="Download Metrics (JSON)",
            data=metrics_json,
            file_name="metrics.json",
            mime="application/json"
        )