# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A **CrewAI-powered research automation tool** that takes a topic as input, searches the web for recent articles, and publishes a structured note to Notion. It has two interfaces:
- **Web UI**: Flask app with SSE streaming (`app.py`, runs on port 5000)
- **CLI**: Direct Python script (`src/note_research_team/main.py`)

Deployed to Kubernetes via Helm, with Argo CD handling GitOps-style sync.

## Required Environment Variables

Create a `.env` file with:
```
GEMINI_API_KEY=...
SERPER_API_KEY=...
NOTION_API_KEY=...
NOTION_PARENT_PAGE_ID=...
NOTION_PARENT_PAGE_URL=...   # optional, for UI display
```

Agent LLMs can be overridden per-agent:
```
RESEARCHER_LLM=gemini/gemini-2.5-flash   # default
WRITER_LLM=gemini/gemini-2.5-flash       # default
```

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt -r requirements_web.txt

# Run Flask web UI (http://localhost:5000)
python app.py

# Run CLI (interactive topic prompt)
python src/note_research_team/main.py

# Test Notion API connectivity
python test_notion.py
```

## Architecture

### CrewAI Pipeline (`src/note_research_team/`)

Three sequential tasks executed by two agents:

| Task | Agent | Tool | Purpose |
|------|-------|------|---------|
| `research_task` | `researcher` | `SerperDevTool` | Web search, select 10 recent articles |
| `organize_task` | `researcher` | — | Categorize and deduplicate findings |
| `write_and_publish_task` | `note_writer` | `NotionTool` | Write Markdown article, publish to Notion |

Config lives in YAML: `src/note_research_team/config/agents.yaml` and `tasks.yaml`.

### Flask Web App (`app.py`)

- `POST /api/run` — starts a crew task in a background thread
- `GET /api/stream` — Server-Sent Events stream of stdout + status events
- Uses `OutputCapture` to redirect stdout → SSE queue during crew execution
- Extracts Notion URL from result text using string matching then regex fallback

### Notion Integration (`src/note_research_team/tools/notion_tool.py`)

`NotionTool` is a custom `crewai.tools.BaseTool` that:
- Converts Markdown to Notion block API format (headings, lists, paragraphs, bold, links)
- Prepends a `table_of_contents` block automatically
- Limited to 100 blocks per API call (1 ToC + 99 content blocks)
- Returns a success message containing `頁面連結：https://www.notion.so/...` which `app.py` parses

### Helm Chart & Kubernetes Deployment

- Helm chart in repo root (`Chart.yaml`, `values.yaml`, `templates/`)
- App secrets injected via `envFrom: secretRef: research-team-secret` (a Sealed Secret)
- TLS handled by `my-tls-sealed-secret.yaml` + Traefik ingress with HTTPS redirect middleware
- Ingress host: `research.local` (configurable in `values.yaml`)

### CI/CD

GitHub Actions (`.github/workflows/ci.yaml`) on push to `main`:
1. Build & push Docker image tagged with short commit SHA
2. Update `values.yaml` `image.tag` with the new SHA
3. Commit & push back (`[skip ci]` to avoid loop)

Argo CD watches this repo and auto-syncs the Helm chart to the cluster.

## Key Design Decisions

- **Notion block limit**: The Notion API accepts max 100 children per page creation. Content beyond 99 blocks is silently dropped — for long articles, a pagination/append approach would be needed.
- **Numbered lists**: Currently rendered as `bulleted_list_item` (Notion doesn't have a simple ordered list equivalent in the API).
- **Output capture**: `sys.stdout` is monkey-patched during crew execution to capture verbose CrewAI logs for SSE streaming. The original stdout is saved and restored after.
