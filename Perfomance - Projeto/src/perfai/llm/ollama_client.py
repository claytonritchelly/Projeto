from typing import Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class OllamaClient:
	"""Cliente mínimo para Ollama local (http://localhost:11434)."""

	def __init__(self, model: str = "llama3.1:8b-instruct", base_url: str = "http://localhost:11434") -> None:
		self.model = model
		self.base_url = base_url.rstrip("/")

	@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(3))
	def complete(self, prompt: str, temperature: float = 0.1, max_tokens: int = 512) -> str:
		payload: Dict[str, object] = {
			"model": self.model,
			"prompt": prompt,
			"stream": False,
			"options": {
				"temperature": temperature,
				"num_predict": max_tokens,
			},
		}
		with httpx.Client(timeout=30) as client:
			resp = client.post(f"{self.base_url}/api/generate", json=payload)
			resp.raise_for_status()
			data = resp.json()
			return data.get("response", "").strip()
