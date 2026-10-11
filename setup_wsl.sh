#!/usr/bin/env bash
# One-shot setup for MedTruth AI + Ollama inside WSL (Ubuntu). Run from the project root:  bash setup_wsl.sh
set -e
MODEL="${1:-llama3.2}"

echo "== 1/6 System packages (Python, OCR, PDF rendering) =="
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl zstd tesseract-ocr poppler-utils

echo "== 2/6 Node.js 20 (frontend) =="
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 18 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt install -y nodejs
fi

echo "== 3/6 Ollama =="
command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
if ! curl -s http://localhost:11434 >/dev/null; then
  (sudo systemctl start ollama 2>/dev/null) || (nohup ollama serve >/tmp/ollama.log 2>&1 &)
  sleep 5
fi
ollama pull "$MODEL"

echo "== 4/6 Backend (Python virtual environment) =="
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
sed -i "s|^LLM_MODEL=.*|LLM_MODEL=$MODEL|" .env
cd ..

echo "== 5/6 Frontend =="
(cd frontend && npm install)

echo "== 6/6 Done =="
echo "Start backend:   cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
echo "Start frontend:  cd frontend && npm run dev     (open http://localhost:5173 in your Windows browser)"
echo "API key location: backend/.env  (LLM_API_KEY)"
