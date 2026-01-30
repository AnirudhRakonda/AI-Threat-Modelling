import streamlit as st
from core.stride_agent import generate_stride_threats
from core.attack_tree import generate_attack_tree

st.set_page_config(page_title="AI Threat Modeling", layout="wide")

st.title("AI-Powered Threat Modeling System")
st.caption("Local LLM powered | STRIDE-based | Automated")

system_desc = st.text_area(
    "Enter System Description",
    height=250,
    placeholder="Example: A web app with React frontend, Node.js backend, JWT authentication, MongoDB..."
)

if st.button("Generate Threat Model"):
    with st.spinner("Analyzing threats using Mistral 7B..."):
        stride_output = generate_stride_threats(system_desc)
        attack_tree = generate_attack_tree(system_desc)

    st.subheader("STRIDE Threat Model")
    st.markdown(stride_output)

    st.subheader("Attack Tree")
    st.text(attack_tree)
