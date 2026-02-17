from openai import OpenAI

from config import settings
from services.gemini_client import LM_UNAVAILABLE_PREFIX


class ChatGPTClient:
    """
    Client for interacting with OpenAI Chat Completions API.
    """

    def __init__(self):
        self.api_key = settings.CHAT_GPT_API_KEY or settings.OPENAI_API_KEY
        self.model_name = "gpt-4o-mini"
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    async def generate_text(self, prompt: str) -> str:
        if not self.api_key or not self.client:
            return f"{LM_UNAVAILABLE_PREFIX}:missing_key:ChatGPT API key not configured"

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            text = (response.choices[0].message.content or "").strip()
            return text
        except Exception as e:
            print(f"Error generating text with ChatGPT: {e}")
            error_text = str(e)
            if "429" in error_text or "rate_limit" in error_text.lower() or "quota" in error_text.lower():
                return f"{LM_UNAVAILABLE_PREFIX}:rate_limited:{error_text[:220]}"
            return f"{LM_UNAVAILABLE_PREFIX}:api_error:{error_text[:220]}"


chatgpt_client = ChatGPTClient()
