# MedTruth AI

Explains chest X-ray report text in plain language and checks every statement against evidence.
This explains report wording only. It is not a diagnosis tool.

## How it works

    report text
        |
    Analysis Agent      split into sentences, find findings, detect "not seen" / "uncertain" wording
        |
    Retrieval Agent     TF-IDF retrieval of evidence passages from the knowledge base (the RAG step)
        |
    Explanation Agent   LLM (optional) or template; told to use only the retrieved evidence
        |
    Verification Agent  checks each claim: word support, numbers, and contradiction with the report
        |
    findings + explanation + evidence trail

## Quick setup on Windows with WSL (Ubuntu), including Ollama

One command from the project root inside the WSL terminal:

    bash setup_wsl.sh            # installs everything and pulls the llama3.2 model
    bash setup_wsl.sh llama3.1:8b   # or choose another model (needs more RAM)

It installs: Python 3 + venv, Node.js 20, Tesseract OCR, Poppler, Ollama, the Python and npm packages, and creates
`backend/.env`. Manual steps are below if you prefer them.

### Manual steps

    # 1. system packages
    sudo apt update
    sudo apt install -y python3 python3-venv python3-pip curl zstd tesseract-ocr poppler-utils
    # Node 18+ (20 recommended):
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs

    # 2. Ollama (always installs the current release; update later by re-running the same line)
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &                 # skip if systemd is enabled in WSL; the installer starts a service then
    ollama pull llama3.2
    curl http://localhost:11434/v1/models     # should list llama3.2

    # 3. backend
    cd backend
    python3 -m venv .venv && . .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env           # then edit if needed (see below)
    python -m unittest discover -s tests -v
    uvicorn app.main:app --reload --port 8000

    # 4. frontend (second WSL terminal)
    cd frontend && npm install && npm run dev      # open http://localhost:5173 in your Windows browser

### Where the API key is

`backend/.env`, line `LLM_API_KEY=`. Ollama ignores the key, so any non-empty word works (`ollama`). Only a hosted
provider (Groq, Gemini, OpenRouter) needs a real secret key there. `.env` is git-ignored; never commit it. The three
settings are read at start-up, so restart uvicorn after editing. `GET /api/health` shows `"llm_enabled": true` when
they are picked up.

    LLM_BASE_URL=http://localhost:11434/v1
    LLM_MODEL=llama3.2
    LLM_API_KEY=ollama
    LLM_TIMEOUT=180

If Ollama is stopped or too slow, the app silently falls back to the built-in template explanation.

### Versions

Python 3.10+ (3.12 on current Ubuntu is fine), Node 18+ (20 LTS recommended), Tesseract 4+ (5.x from apt),
Ollama latest from the install script, FastAPI 0.115+, React 18.3, Vite 5.4. Update with
`pip install -U -r requirements.txt`, `npm update`, and the Ollama install line again.

## Uploading files

"Choose file" accepts `.pdf`, `.docx`, `.txt`, `.md`, `.png`, `.jpg`, `.tif`, `.bmp`, `.webp` (max 5 MB).
Text PDFs are read directly. Scanned PDFs (first 10 pages) and pictures of reports are read with OCR (Tesseract).
Old `.doc` files are not supported; save as `.docx`. OCR reads printed words only: it cannot interpret an X-ray
image itself, and an image with no readable text is rejected with a clear message. Check OCR output in the text box
before analysing, since OCR can misread words.

## Run it (without the script)

    cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
    cd frontend && npm install && npm run dev

## Before you rely on it

1. The knowledge base (`backend/app/data/knowledge_base.json`) is a placeholder written from general knowledge.
   Replace it with vetted, licensed sources and get a clinician to review it.
2. Retrieval is TF-IDF. Upgrade path: sentence embeddings + a vector DB (for example sentence-transformers with
   FAISS or Chroma). Keep `Retriever.retrieve(query, k)` as the interface.
3. Analysis is rule-based (negation and hedge cues). Test it on real, de-identified reports and extend the
   cue lists where it is wrong.
4. Evaluation plan: hand-label 20 to 30 reports (findings and status), then compare plain LLM vs RAG + LLM vs the
   full pipeline on accuracy, support score, hallucination rate and readability.

## Layout

    backend/app/text_utils.py            sentence splitting, tokenizer, stemmer
    backend/app/knowledge_base.py        loads the knowledge base and compiles term patterns
    backend/app/agents/                  analysis, retrieval, explanation, verification agents
    backend/app/pipeline.py              runs the four agents in order
    backend/app/main.py                  FastAPI: GET /api/health, GET /api/samples, POST /api/analyze, POST /api/extract (file to text, with OCR)
    backend/app/extract.py               file to text: PDF, scanned PDF, image (OCR), docx
    backend/app/llm.py                   optional OpenAI-compatible client
    backend/tests/test_pipeline.py       unit tests
    frontend/src/App.jsx, styles.css     React interface

## Multi-X-ray design

The proposed roadmap covers four separate pathways: chest, bones and joints, spine, and dental X-rays. Each pathway must use a task-appropriate model, document its supported inputs, and pass its own evaluation. The design is documented in [docs/MULTI_XRAY_DESIGN.md](docs/MULTI_XRAY_DESIGN.md).

**Current status:** this is a design and implementation plan, not a claim that all four specialty models are integrated or clinically validated. AI-generated image findings must be clearly labelled, unsupported inputs must fail safely, and outputs require appropriate clinical review.
