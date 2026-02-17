import google.generativeai as genai
from config import settings

LM_UNAVAILABLE_PREFIX = "__LM_UNAVAILABLE__"

class GeminiClient:
    """
    Client for interacting with Google's Gemini API.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None

    async def generate_text(self, prompt: str) -> str:
        if not self.api_key or not self.model:
            return f"{LM_UNAVAILABLE_PREFIX}:missing_key:Gemini API key not configured"
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating text with Gemini: {e}")
            error_text = str(e)
            if "429" in error_text or "RATE_LIMIT_EXCEEDED" in error_text or "ResourceExhausted" in error_text:
                return f"{LM_UNAVAILABLE_PREFIX}:rate_limited:{error_text[:220]}"
            return f"{LM_UNAVAILABLE_PREFIX}:api_error:{error_text[:220]}"

gemini_client = GeminiClient()
