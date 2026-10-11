"""Optional LLM client for any OpenAI-compatible chat endpoint (standard library only).

Works with a local Ollama server, or hosted providers that expose /chat/completions.
Configure with environment variables. With none set, the system runs without an LLM
and the Explanation Agent uses its built-in template.

  LLM_BASE_URL  e.g. http://localhost:11434/v1   (Ollama)
  LLM_MODEL     e.g. llama3.2
  LLM_API_KEY   any non-empty string for Ollama; a real key for hosted providers
"""
import json
import os
import urllib.request


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
        self.model = os.getenv("LLM_MODEL", "")
        self.api_key = os.getenv("LLM_API_KEY", "none")
        self.enabled = bool(self.base_url and self.model)

    def complete(self, system: str, user: str, timeout: int = 0) -> str:
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", "120"))  # CPU-only Ollama can be slow
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
