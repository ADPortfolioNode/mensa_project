import google.generativeai as genai
from config import GEMINI_API_KEY

class GeminiClient:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')

    async def generate_text(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Handle API errors gracefully
            print(f"Error generating text with Gemini: {e}")
            return "Sorry, I'm having trouble connecting to the Gemini API right now."

gemini_client = GeminiClient()
