import google.generativeai as genai
import requests
from config import settings

class GeminiClient:
    """
    Client for interacting with Google's Gemini API.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.grok_api_key = settings.GROK_API_KEY
        self.grok_api_base = settings.GROK_API_BASE.rstrip("/")
        self.grok_model = settings.GROK_MODEL
        self.last_error = None
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        else:
            self.model = None

    def is_available(self) -> bool:
        return bool((self.api_key and self.model) or self.grok_api_key)

    def _generate_with_grok(self, prompt: str) -> str:
        if not self.grok_api_key:
            raise RuntimeError("Grok API key not configured")

        response = requests.post(
            f"{self.grok_api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.grok_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.grok_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json() or {}
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("No choices returned from Grok API")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content:
            raise RuntimeError("Empty response content from Grok API")
        return content

    async def generate_text(self, prompt: str) -> str:
        if not self.is_available():
            return "No LLM provider configured. Set GEMINI_API_KEY or GROK_API_KEY."

        if self.api_key and self.model:
            try:
                response = self.model.generate_content(prompt)
                self.last_error = None
                return response.text
            except Exception as e:
                print(f"Error generating text with Gemini: {e}")
                self.last_error = str(e)

        if self.grok_api_key:
            try:
                response_text = self._generate_with_grok(prompt)
                self.last_error = None
                return response_text
            except Exception as e:
                print(f"Error generating text with Grok: {e}")
                self.last_error = str(e)

        return "Sorry, I'm having trouble connecting to the Gemini API right now (Grok fallback unavailable)."

gemini_client = GeminiClient()
