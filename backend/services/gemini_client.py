import google.generativeai as genai
from config import settings

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
            return "Gemini API key not configured. Please set GEMINI_API_KEY."
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Handle API errors gracefully
            print(f"Error generating text with Gemini: {e}")
            return "Sorry, I'm having trouble connecting to the Gemini API right now."

gemini_client = GeminiClient()
