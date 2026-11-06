"""Streamlit chat interface. Talks to the FastAPI backend."""
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="FinSight AI", page_icon="📈", layout="centered")
st.title("📈 FinSight AI")
st.caption("Financial research copilot · SQL (what happened) + 10-K RAG (why) + computed quant metrics · "
           "Research support, not investment advice.")

EXAMPLES = [
    "Why did Apple's revenue change, and did the stock follow?",
    "Compare JPM, BAC and GS: profit margin, ROE and 1-year return.",
    "What are the volatility, Sharpe ratio and max drawdown of NVDA over 3 years?",
    "Analyse a portfolio 50% MSFT, 30% KO, 20% XOM over 1 year.",
]
with st.sidebar:
    st.subheader("Try asking")
    for e in EXAMPLES:
        if st.button(e, use_container_width=True):
            st.session_state["pending"] = e

if "history" not in st.session_state:
    st.session_state["history"] = []
for m in st.session_state["history"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("tools"):
            st.caption("Tools used: " + ", ".join(m["tools"]))

q = st.chat_input("Ask a question about the 44 companies...") or st.session_state.pop("pending", None)
if q:
    st.session_state["history"].append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        with st.spinner("Analysing with local LLM..."):
            try:
                r = requests.post(f"{API_URL}/ask", json={"question": q}, timeout=600)
                r.raise_for_status()
                d = r.json()
                st.markdown(d["answer"])
                st.caption(f"Tools used: {', '.join(d['tools_used']) or 'none'} · {d['latency_ms'] / 1000:.1f}s")
                st.session_state["history"].append({"role": "assistant", "content": d["answer"], "tools": d["tools_used"]})
            except Exception as e:
                st.error(f"Backend error: {e}")
