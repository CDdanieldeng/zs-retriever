# Retriever Service MVP

Production-grade MVP for **Recall + Rerank only** (no generation). Supports file upload, multi-level chunking, pluggable providers, project isolation, async indexing, and index versioning.

## Structure

```
root/
  backend/          # FastAPI backend
  playground_ui/    # Streamlit testing UI (HTTP only)
  README.md
```

## Tech Stack

- **Backend:** Python 3.10, FastAPI, Uvicorn, SQLite, PyMuPDF, python-pptx, python-docx
- **Playground:** Streamlit, requests (no backend imports)

## Quick Start

### 1. Backend

```bash
cd backend
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Playground UI

```bash
cd playground_ui
pip install -r requirements.txt
streamlit run app.py
```

### 3. Usage

1. **Upload:** Open Upload page, enter project ID (e.g. `default`), upload a PDF/PPTX/DOCX, click "Upload & Index"
2. **Search:** Open Search page, enter project ID and query, adjust recall/rerank params, view results

## Configuration

Environment variables (prefix `RETRIEVER_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `RETRIEVER_SQLITE_PATH` | `data/retriever.db` | SQLite path |
| `RETRIEVER_FILES_STORAGE_PATH` | `data/files` | Uploaded files |
| `RETRIEVER_VECTOR_STORE_PATH` | `data/vectors` | Vector store |
| `RETRIEVER_CHUNKING_POLICY` | `hybrid` | `structure_fixed`, `semantic`, or `hybrid` |
| `RETRIEVER_ENABLE_OCR` | `false` | OCR for images |
| `RETRIEVER_ENABLE_VISION_CAPTION` | `false` | Vision captioning |

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/projects/{project_id}/files/upload` | Upload file |
| POST | `/v1/indexes/build` | Start index build job |
| GET | `/v1/jobs/{job_id}` | Job status |
| POST | `/v1/projects/{project_id}/search` | Recall + Rerank search |
| GET | `/v1/projects/{project_id}/parents/{parent_id}` | Get parent with children |

## Chunking Policies

- **structure_fixed:** Target 280 tokens, overlap 60, hard max 380
- **semantic:** Paragraph-level embeddings, split when similarity < 0.72
- **hybrid (default):** Structure first; semantic refinement if parent >= 600 tokens

## Pluggable Providers

All providers are interfaces; configure via env (dotted class path):

- `OcrProvider`, `VisionCaptionProvider`, `EmbeddingProvider`, `RerankProvider`, `VectorStoreAdapter`

Stub implementations allow running without external services.

## Testing

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
