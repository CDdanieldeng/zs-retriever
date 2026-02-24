"""Upload page - project_id, file upload, trigger index build, job status."""

import time

import requests
import streamlit as st

API_BASE = "http://localhost:8000/v1"


def get_api_base() -> str:
    return st.session_state.get("api_base", API_BASE)


st.title("Upload & Index")
st.caption("Upload a file and trigger index build. Poll for job completion.")

api_base = st.text_input("API Base URL", value=API_BASE, key="api_base")
project_id = st.text_input("Project ID", value="default", key="project_id")
uploaded_file = st.file_uploader(
    "Choose file (PDF, PPTX, DOCX)",
    type=["pdf", "pptx", "docx"],
)

if uploaded_file and st.button("Upload & Index"):
    base = get_api_base()
    with st.spinner("Uploading..."):
        try:
            r = requests.post(
                f"{base}/projects/{project_id}/files/upload",
                files={"file": (uploaded_file.name, uploaded_file.getvalue())},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            file_id = data["file_id"]
            st.success(f"Uploaded: {data['filename']} (file_id: {file_id})")
        except requests.RequestException as e:
            st.error(f"Upload failed: {e}")
            st.stop()

    with st.spinner("Starting index build..."):
        try:
            r = requests.post(
                f"{base}/indexes/build",
                json={"project_id": project_id, "file_ids": [file_id]},
                timeout=10,
            )
            r.raise_for_status()
            job_id = r.json()["job_id"]
            st.info(f"Job started: {job_id}")
        except requests.RequestException as e:
            st.error(f"Index build start failed: {e}")
            st.stop()

    st.subheader("Job Status")
    status_placeholder = st.empty()
    progress_bar = st.progress(0, text="Waiting for index build...")
    poll_count = 0
    max_progress = 0.9  # Cap at 90% until actually done

    while True:
        try:
            r = requests.get(f"{base}/jobs/{job_id}", timeout=5)
            r.raise_for_status()
            job = r.json()
            status = job["status"]
            poll_count += 1
            # Progress increases with each poll, capped at 90%
            progress = min(max_progress, poll_count * 0.08)
            progress_bar.progress(progress, text=f"Status: {status} (polling...)")

            status_placeholder.write(f"**Status:** {status}")
            if job.get("metrics"):
                status_placeholder.json(job["metrics"])
            if status == "completed":
                progress_bar.progress(1.0, text="Index build completed!")
                st.success("Index build completed!")
                break
            if status == "failed":
                progress_bar.progress(1.0, text="Index build failed.")
                st.error(f"Failed: {job.get('error_message', 'Unknown error')}")
                break
        except requests.RequestException as e:
            progress_bar.progress(1.0, text="Poll failed.")
            status_placeholder.error(f"Poll failed: {e}")
            break
        time.sleep(2)
