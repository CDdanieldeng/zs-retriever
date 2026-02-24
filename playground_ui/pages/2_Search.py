"""Search page - project_id, query, recall/rerank params, display results."""

import requests
import streamlit as st

API_BASE = "http://localhost:8000/v1"


def get_api_base() -> str:
    return st.session_state.get("api_base", API_BASE)


st.title("Search")
st.caption("Recall + Rerank search. Expand parents for full context.")

api_base = st.text_input("API Base URL", value=API_BASE, key="api_base")
project_id = st.text_input("Project ID", value="default", key="project_id")
query = st.text_input("Query", placeholder="Enter search query")
col1, col2, col3 = st.columns(3)
with col1:
    recall_top_k = st.number_input("Recall top K", min_value=1, max_value=200, value=50)
with col2:
    rerank_top_n = st.number_input("Rerank top N", min_value=1, max_value=100, value=10)
with col3:
    request_timeout = st.number_input(
        "Request timeout (s)",
        min_value=10,
        max_value=600,
        value=120,
        help="Increase if using local Qwen embedding (first load slow)",
    )

if query and st.button("Search"):
    base = get_api_base()
    with st.spinner("Searching..."):
        try:
            r = requests.post(
                f"{base}/projects/{project_id}/search",
                json={
                    "query": query,
                    "recall_top_k": recall_top_k,
                    "rerank_top_n": rerank_top_n,
                    "debug": True,
                },
                timeout=request_timeout,
            )
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            st.error(f"Search failed: {e}")
            st.stop()

    st.write(f"**Trace ID:** {data['trace_id']}")
    st.write(f"**Timings (ms):** {data['timings_ms']}")

    st.subheader("Recall Results")
    if data["recall"]:
        import pandas as pd
        recall_df = pd.DataFrame([
            {
                "chunk_id": h["chunk_id"][:8] + "...",
                "score": round(h["score"], 4),
                "snippet": h["chunk_text"][:200] + "..." if len(h["chunk_text"]) > 200 else h["chunk_text"],
                "parent_id": h["parent_id"][:8] + "...",
            }
            for h in data["recall"]
        ])
        st.dataframe(recall_df, use_container_width=True)
    else:
        st.info("No recall results.")

    st.subheader("Rerank Results")
    if data["rerank"]:
        parent_to_load = st.selectbox(
            "View full parent context",
            options=[""] + [h["parent_id"] for h in data["rerank"]],
            format_func=lambda x: (x[:12] + "..." if len(x) > 12 else x) if x else "(select)",
        )
        if parent_to_load:
            try:
                pr = requests.get(
                    f"{base}/projects/{project_id}/parents/{parent_to_load}",
                    timeout=5,
                )
                pr.raise_for_status()
                parent = pr.json()
                st.write("**Parent text:**")
                st.write(parent["parent_text"])
                st.write("**Children:**")
                for c in parent["children"]:
                    st.write(f"- [{c['chunk_type']}] {c['chunk_text'][:150]}...")
            except requests.RequestException as e:
                st.error(f"Failed to load parent: {e}")
        for i, h in enumerate(data["rerank"], 1):
            with st.expander(f"#{i} Score: {h['score']:.4f} | {h['chunk_text'][:80]}..."):
                st.write(h["chunk_text"])
    else:
        st.info("No rerank results.")
